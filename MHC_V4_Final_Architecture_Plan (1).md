# MHC Agentic V4 — Final Architecture Plan

> **One-line summary:** Cheap models handle structure. Expensive models handle humans. Deterministic systems handle safety.

---

## 0. Design Goals

| Goal | How V4 achieves it |
|---|---|
| Cost efficiency | Model router — pay for 120B only when it matters |
| Emotional quality | 120B fires on high risk / high emotional intensity / low RAG confidence |
| Safety correctness | Deterministic gate + semantic embedding layer |
| Latency control | Simple path stays at 1 × 70B call (~800ms) |
| Abuse protection | Redis token bucket rate limiter before everything |

---

## 1. Core Philosophy (unchanged from V3)

- LLMs do exactly two things — 8B reasons about what to retrieve, 70B/120B talks to the human. Nothing else touches an LLM.
- ReAct only fires when it earns its cost — ~55% of conversations are simple.
- Hinglish is infrastructure, not an afterthought — crisis keywords, RAG retrieval, and response generation all treat Hinglish as primary.
- Safety is two layers — deterministic gate first, semantic check second. Both must pass.
- Emotions come from a deterministic scorer — zero extra cost, zero LLM dependency.

---

## 2. Full V4 Pipeline

```
User Input (Hinglish / Hindi / English / mixed + emojis)
│
[RATE LIMITER] ── NEW, Redis token bucket, ZERO LLM
│   if requests_per_user > RATE_LIMIT_PER_MINUTE:
│       return "Please slow down. Take a breath."
│   PIPELINE ENDS HERE
│
[SAFETY GATE] ── deterministic, <5ms, ZERO LLM
│   - Hindi + Hinglish + English crisis keywords
│   - Embedding similarity check (catches indirect phrases)
│   - Prompt injection sanitizer
│   - Aadhaar / PII scrubber
│
├── CRISIS → hardcoded response, ZERO LLM
│       iCall: 9152987821
│       Vandrevala: 1860-2662-345
│       AASRA: 9820466627
│       + one warm Hinglish acknowledgement line
│       PIPELINE ENDS HERE
│
[EMOTIONAL SCORER] ── NEW, deterministic, ZERO LLM
│   emotional_intensity = weighted_score(
│       sentiment_score,
│       keyword_intensity,
│       punctuation_density,
│       repetition_patterns
│   )
│   ← feeds path classifier AND model router before any LLM call
│
[PATH CLASSIFIER] ── deterministic numeric score, <1ms, ZERO LLM
│
├── SIMPLE PATH (~55%)
│       Single 70B call
│       Input: message + last 5 turns + session summary
│       Output: { response, emotions[], risk_level, clinical_flags[], referral_needed }
│       ~800ms | 1 LLM call
│
└── COMPLEX PATH (~40%)
        [ReAct AGENT LOOP] ── max 4 steps, hard cap in CODE
        │   8B model: Thought → Action → Observation → repeat
        │   retry_once() on invalid tool call, else fallback_to_70b()
        │   validate_tool_schema(action) on every step
        │   force_exit() if step > 4
        │
        Tools (ALL ZERO LLM):
        │   TherapyTool      semantic RAG, ChromaDB, therapy domain
        │   AssessmentTool   semantic RAG, ChromaDB, assessment domain
        │   ResourceTool     semantic RAG, ChromaDB, resource domain
        │   MemoryReadTool   SQLite/Postgres query, returns session context
        │   RiskEvaluator    deterministic scoring from conversation signals
        │
        [RAG CONFIDENCE CHECK] ── NEW, ZERO LLM
        │   rag_confidence = avg_similarity(top_k)
        │   if rag_confidence < RAG_CONFIDENCE_THRESHOLD:
        │       trigger broader retrieval OR skip RAG influence
        │   ← feeds model router
        │
        [MODEL ROUTER] ── confidence-based, UPGRADED
        │   if risk_level >= "medium":          → 120B
        │   if emotional_intensity > 0.8:        → 120B
        │   if rag_confidence < 0.6:             → 120B  ← weak context
        │   if react_steps >= 3:                 → 120B  ← reasoning struggled
        │   else:                                → 70B
        │
        Final response call (70B or 120B — NEVER 8B)
        │   120B fails → fallback to 70B
        │   70B fails  → fallback to cached response / template
        Output: { response, emotions[], risk_level, clinical_flags[], referral_needed }
        ~1200ms | 2–3 LLM calls

[RESPONSE VALIDATOR] ── NEW, ZERO LLM
│   if response.length < min_threshold:
│       regenerate()
│   if missing_empathy_marker:
│       regenerate()

[OUTPUT NORMALIZER] ── deterministic, ZERO LLM
│   enforce_hinglish_style()
│   validate_json_schema()
│   strip_overclinical_language()
│   no system internals in output

[OBSERVABILITY LAYER] ── async, ZERO LLM
│   { latency_per_node, llm_calls, tokens_used, model_used,
│     safety_triggered, fallback_triggered,
│     rag_confidence, emotional_intensity, react_steps_used }

[ASYNC MEMORY WRITE] ── non-blocking, ZERO LLM on critical path
    Persist: risk_level, emotions[], clinical_flags[], referral_needed
    Every 10th exchange: out-of-band 8B summarization call
    Cross-session: prior summary injected into next session context
    Every Nth exchange: re-anchor summary to prevent state drift
```

---

## 3. The 10 Changes vs V3

### CHANGE 1 — Rate Limiter (NEW)

**Before:** No abuse protection despite `RATE_LIMIT_PER_MINUTE` being defined in env.

**After:** Redis token bucket middleware runs before everything else.

```python
if requests_per_user > RATE_LIMIT_PER_MINUTE:
    return "Please slow down. Take a breath."
```

Prevents bots, cost explosion, and denial-of-service.

---

### CHANGE 2 — Deterministic Emotional Scorer (NEW)

**Before:** `emotional_intensity` was implicitly read from LLM output — circular dependency, unreliable before generation.

**After:** Computed deterministically before any LLM call:

```python
def compute_emotional_intensity(message):
    return weighted_score(
        sentiment_score,
        keyword_intensity,
        punctuation_density,
        repetition_patterns
    )
```

This value feeds both the path classifier and the model router.

---

### CHANGE 3 — Model Router (upgraded to confidence-based)

**Before:** `if risk_level → 120B` and `if is_complex → 120B` — over-uses expensive model.

**After:**

```python
def select_model(context):
    if context.risk_level >= "medium":
        return GPT_OSS_120B

    if context.emotional_intensity > 0.8:
        return GPT_OSS_120B

    if context.rag_confidence < 0.6:    # weak context → need better model
        return GPT_OSS_120B

    if context.react_steps >= 3:        # reasoning struggled
        return GPT_OSS_120B

    return LLAMA_70B
```

Reduces cost without hurting quality.

---

### CHANGE 4 — RAG Confidence Scoring (NEW)

**Before:** Top-K retrieved, assumed good. Bad retrieval silently corrupted therapy advice.

**After:**

```python
rag_confidence = avg_similarity(top_k)

if rag_confidence < RAG_CONFIDENCE_THRESHOLD:
    # trigger broader retrieval OR skip RAG influence entirely
```

Confidence score also feeds the model router — low RAG confidence → route to 120B.

---

### CHANGE 5 — Numeric Path Classifier

**Before:** Binary `simple / complex`.

**After:**

```python
complexity_score = (
    clinical_signal    * 2 +
    prior_risk         * 2 +
    emotional_intensity    +   # ← now from deterministic scorer
    topic_count            +
    message_length_factor
)

path = "complex" if complexity_score >= 3 else "simple"
```

---

### CHANGE 6 — Semantic Safety Layer

**Before:** Keyword matching only.

**After:**

```
[Keyword Gate] → [Embedding similarity check]
```

Catches indirect phrases no keyword list covers:
- `"bas sab khatam ho jaye"`
- `"so jaana permanently"`
- `"bina mujhare sab theek rahenge"`

---

### CHANGE 7 — Hardened ReAct Loop

**Before:** No retry, no schema validation, model trusted to stop.

**After:**

```python
if invalid_tool_call:
    retry_once()
    # else:
    fallback_to_70b()

if step > 4:
    force_exit()

validate_tool_schema(action)  # on every step
```

---

### CHANGE 8 — Fallback Model Hierarchy

**Before:** Groq failure → generic message.

**After:**

```
120B fails → fallback to 70B
70B fails  → fallback to cached response / template
```

---

### CHANGE 9 — Response Validator (NEW)

**Before:** Response sent as-is regardless of quality.

**After:**

```python
if response.length < min_threshold:
    regenerate()

if missing_empathy_marker:
    regenerate()
```

---

### CHANGE 10 — Replace SQLite + State Drift Protection

**Before:** `sqlite+aiosqlite` — file locks, no concurrency. Long chats caused tone/memory drift.

**After:**

```
PostgreSQL  →  primary storage
Redis       →  session cache
```

Plus periodic re-anchor summary on long sessions to prevent state drift.

---

## 4. Model Config

```env
REASONING_MODEL        = llama-3.1-8b-instant       # ReAct steps only
FAST_RESPONSE_MODEL    = llama-3.3-70b-versatile     # Simple path + low-complexity
QUALITY_RESPONSE_MODEL = gpt-oss-120b                # High risk / high emotion / low RAG confidence
```

---

## 5. LLM Call Budget

| Path | Model | Calls | Latency |
|---|---|---|---|
| Crisis | none | 0 | 5ms |
| Simple | 70B | 1 | ~800ms |
| Complex (light) | 8B + 70B | 2 | ~1200ms |
| Complex (heavy) | 8B + 120B | 2–3 | ~1400ms |
| **Weighted average** | | **~1.5** | **~900ms** |

V1: 4.2 calls. V2: 3.8 calls. V3: 1.4 calls. V4: ~1.5 calls (slightly higher, significantly better emotional quality and routing precision).

---

## 6. Hinglish Safety Gate — Keyword Categories

All stored in `crisis_keywords.json` — updated without code changes.

### Category 1: Hard Crisis (immediate response, ZERO LLM)
```
marna chahta hoon / marna chahti hoon
khatam kar loon apne aap ko
zindagi khatam karna chahta hoon
suicide karna chahta hoon
jeena nahi chahta / jeena nahi chahti
mar jaana chahta hoon
khud ko hurt karna chahta hoon
```

### Category 2: Soft Crisis (→ COMPLEX, RiskEvaluator flags HIGH)
```
kuch feel nahi hota
zindagi se thak gaya / thak gayi
sone dedo mujhe
sab khatam ho jata toh acha hota
koi nahi hai mera
meri kisi ko zaroorat nahi
sabke liye burden hoon
bina mujhare sab theek rahenge
```

### Category 3: Contextual Signals (→ COMPLEX)
```
bahut akela lag raha hai
sab bekaar hai
koi samajhta nahi
bahut dard ho raha hai
kuch bhi acha nahi lagta
rona aa raha hai bina wajah
```

### Category 4: Indian Context Risk Markers (increases COMPLEX probability)
```
board exams / JEE / NEET fail ho gaya
ghar waale / shaadi ka pressure
log kya kahenge
paisa nahi / job nahi mili
pagal nahi hoon   ← stigma marker
```

**Implementation rules:**
- Word boundary regex — `"marna"` inside `"kamarna"` must not trigger
- Normalize before matching: lowercase, strip extra spaces
- Log all triggers (anonymized) for ongoing review
- Review with mental health professional before production

---

## 7. Semantic RAG Stack

| Component | Choice | Why |
|---|---|---|
| Embedding model | all-MiniLM-L6-v2 | Free, local, 80MB, ~10ms, handles code-switched text |
| Vector store | ChromaDB (local) | No external dependency, persistent, free |
| Chunk size | 150 tokens | Smaller chunks = better precision |
| Domain tags | therapy / assessment / resource / crisis | Tools filter by domain before similarity search |
| Query language | 8B generates English query from Hinglish | Embedding model performs better on English |
| Top-K | 3 chunks per tool call | Enough context, no context window pressure |
| Confidence scoring | avg_similarity(top_k) | NEW — gates bad retrieval before it reaches the model |

**Why TF-IDF fails:**
- `"neend nahi aati"` → zero lexical overlap with `"sleep disturbance"` docs
- `"yaar bahut akela lag raha hai"` → zero match with `"loneliness and social isolation"`

---

## 8. Path Classifier Logic

```python
def classify_path(message, session_memory) -> "simple" | "complex":

    if session_memory.last_risk_level in ["medium", "high"]:
        return "complex"

    if has_clinical_keywords(message):  # PHQ-9/GAD-7 signals + Hindi equivalents
        return "complex"

    if topic_count(message) >= 2:
        return "complex"

    if session_memory.exchange_count >= 3:
        return "complex"

    # V4: numeric score instead of binary
    complexity_score = (
        clinical_signal * 2 +
        prior_risk * 2 +
        emotional_intensity +       # ← now from deterministic scorer
        topic_count(message) +
        message_length_factor
    )

    if complexity_score >= 3:
        return "complex"

    return "simple" if is_clearly_simple(message) else "complex"
```

---

## 9. ReAct Loop — Hard Rules

- Max 4 steps enforced in code — model cannot override this
- 8B handles Thought + Action only — never generates user-facing text
- 70B or 120B always writes the final response — no exceptions
- If max steps hit: fallback to final model with all collected context
- Invalid tool call: retry once, then fallback
- Schema validated on every action before execution

---

## 10. Memory Design

| Layer | Storage | What's stored |
|---|---|---|
| Turn-level | PostgreSQL (async) | message, response, emotions[], risk_level, clinical_flags[] |
| Session-level | Redis (cache) | rolling last 5 turns injected into every LLM call |
| Cross-session | PostgreSQL (async) | 8B summary every 10 exchanges, out of band |
| Next session | Context injection | Prior summary prepended on session return |

**Summary prompt must preserve:**
- Last known `risk_level`
- Any referral flags
- Active clinical themes
- Key personal context (family situation, stressors mentioned)

**State drift protection:** Re-anchor summary triggered every N exchanges on long sessions to prevent tone/memory drift.

---

## 11. Directory Structure

```
mhc-v4/
├── app/
│   ├── main.py
│   ├── config.py                    Pydantic Settings, all env vars
│   │
│   ├── graph/
│   │   ├── state.py                 MHCState TypedDict
│   │   ├── builder.py               LangGraph composition
│   │   └── nodes/
│   │       ├── rate_limiter.py      NEW — Redis token bucket
│   │       ├── safety_gate.py       Crisis + PII + injection + embedding check
│   │       ├── emotional_scorer.py  NEW — deterministic intensity scoring
│   │       ├── path_classifier.py   Numeric score routing
│   │       ├── direct_responder.py  Simple path — 1x 70B
│   │       ├── react_agent.py       ReAct loop — hardened
│   │       ├── rag_confidence.py    NEW — avg_similarity check + fallback
│   │       ├── model_router.py      UPGRADED — confidence-based routing
│   │       ├── response_validator.py NEW — length + empathy check
│   │       ├── output_normalizer.py Hinglish style + schema
│   │       ├── observability.py     Metrics payload
│   │       └── memory_update.py     Async persist + summary trigger
│   │
│   ├── tools/                       ReAct tool registry (ALL zero LLM)
│   │   ├── therapy_tool.py
│   │   ├── assessment_tool.py
│   │   ├── resource_tool.py
│   │   ├── memory_read_tool.py
│   │   └── risk_evaluator.py
│   │
│   ├── safety/
│   │   ├── crisis_detector.py
│   │   ├── crisis_keywords.json     ← edit without touching code
│   │   ├── semantic_safety.py       Embedding similarity check
│   │   ├── input_sanitizer.py
│   │   ├── pii_scrubber.py          Aadhaar + Indian PII
│   │   └── output_scrubber.py
│   │
│   ├── rag/
│   │   ├── embedder.py              all-MiniLM-L6 wrapper
│   │   ├── vector_store.py          ChromaDB interface
│   │   ├── retriever.py             Domain-filtered + reranked search
│   │   ├── confidence.py            NEW — avg_similarity scorer
│   │   └── ingest.py
│   │
│   ├── knowledge/
│   │   ├── therapy_knowledge.json   + Hinglish anchors
│   │   ├── assessment_knowledge.json
│   │   ├── crisis_knowledge.json    India-specific resources
│   │   └── resource_knowledge.json  Indian hotlines + services
│   │
│   ├── prompts/
│   │   ├── companion_prompt.py      Master system prompt
│   │   ├── react_prompt.py          8B reasoning prompt
│   │   └── summary_prompt.py        Memory summarization
│   │
│   └── services/
│       ├── llm_service.py           Async Groq + tenacity + circuit breaker
│       ├── session_service.py       SQLAlchemy async + PostgreSQL
│       └── cache_service.py         Redis session cache + rate limiter
│
├── tests/
│   ├── test_safety/
│   │   ├── test_hindi_crisis.py
│   │   ├── test_semantic_safety.py
│   │   └── test_pii_scrubber.py
│   ├── test_rag/
│   │   ├── test_hinglish_retrieval.py
│   │   └── test_rag_confidence.py   NEW
│   ├── test_graph/
│   │   ├── test_rate_limiter.py     NEW
│   │   ├── test_emotional_scorer.py NEW
│   │   ├── test_path_classifier.py
│   │   ├── test_model_router.py
│   │   ├── test_react_agent.py
│   │   └── test_end_to_end.py
│   └── test_api/
│       └── test_chat_endpoint.py
│
├── streamlit_app.py
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## 12. Environment Variables

```env
# LLM
GROQ_API_KEY=
GROQ_FAST_MODEL=llama-3.1-8b-instant
GROQ_QUALITY_MODEL=llama-3.3-70b-versatile
QUALITY_RESPONSE_MODEL=gpt-oss-120b

# RAG
CHROMA_PERSIST_DIR=./chroma_db
EMBEDDING_MODEL=all-MiniLM-L6-v2
RAG_CONFIDENCE_THRESHOLD=0.6         # below this → broader retrieval or skip RAG

# Pipeline
REACT_MAX_STEPS=4
MEMORY_SUMMARY_INTERVAL=10
RATE_LIMIT_PER_MINUTE=10
EMOTIONAL_INTENSITY_THRESHOLD=0.8    # now from deterministic scorer, not LLM

# Safety
CRISIS_KEYWORDS_PATH=./app/safety/crisis_keywords.json
SEMANTIC_SAFETY_THRESHOLD=0.82

# Response quality
RESPONSE_MIN_LENGTH=80               # characters — below this triggers regeneration

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/mhc
REDIS_URL=redis://localhost:6379

# Debug
DEBUG_MODE=false
LOG_LEVEL=INFO
```

---

## 13. Dependencies

```toml
# Core
langgraph
langchain-groq
fastapi
uvicorn[standard]
httpx

# Resilience
tenacity
circuitbreaker

# RAG
sentence-transformers
chromadb

# Storage
sqlalchemy[asyncio]
asyncpg
redis[asyncio]

# Config
pydantic-settings
structlog

# UI
streamlit
```

---

## 14. Build Order

### Phase 1 — Safety (before any other code)
- Redis rate limiter middleware
- Hinglish crisis keyword list with all 4 categories
- `crisis_keywords.json` external file
- Embedding-based semantic safety check
- Aadhaar PII scrubber
- Test every keyword category + indirect phrases with real Hinglish inputs
- **Review with a mental health professional before proceeding**

### Phase 2 — RAG Migration
- Embed all knowledge chunks with all-MiniLM-L6
- Add domain tags
- Add Hinglish semantic anchors
- Add query expansion (Hinglish → English)
- Add domain reranker + fallback retrieval
- Add `avg_similarity` confidence scoring
- Validate on 20 Hinglish test queries

### Phase 3 — Simple Path
- Deterministic emotional scorer
- Numeric path classifier
- Direct responder (1x 70B, structured output)
- Companion system prompt (warm, Hinglish-aware, non-clinical)
- Response validator (length + empathy check)
- Output normalizer
- Async memory write (PostgreSQL + Redis)
- **Working system end-to-end at this point**

### Phase 4 — ReAct Loop
- Tool registry (all zero LLM)
- ReAct loop with hard 4-step cap
- Retry + schema validation
- 8B reasoning prompt
- RAG confidence check inside tools
- Fallback on max steps or invalid call
- Test on 30 clinical-signal inputs

### Phase 5 — Model Router
- Implement confidence-based `select_model(context)` logic
- Wire in: `emotional_intensity`, `rag_confidence`, `react_steps`
- Integrate 120B endpoint with fallback hierarchy (120B → 70B → template)
- Test routing decisions across risk/emotion/complexity/confidence combinations

### Phase 6 — Cross-Session Memory + Observability
- Summary trigger (every 10th exchange, out of band)
- State drift re-anchor on long sessions
- Prior summary injection on session return
- Full observability payload on every request (include `rag_confidence`, `emotional_intensity`, `react_steps_used`)
- Shadow evaluation log: `user_input`, `model_used`, `response` → offline 70B vs 120B comparison
- Test: user returns after gap, context is present

---

## 15. Known Risks & Mitigations

| Risk | Mitigation |
|---|---|
| 8B produces invalid JSON in ReAct steps | Strict parser + defined fallback schema. Parse fail → skip to final model with available context |
| RAG weak on novel Hinglish phrasings | Hinglish semantic anchors + confidence scoring. Low confidence → broader retrieval. Monitor and expand. |
| Path classifier sends crisis-adjacent message to Simple | Default to Complex on ambiguity. Conservative threshold. |
| 70B/120B responds in formal English when user wrote Hinglish | Explicit language-matching instruction in `companion_prompt.py` |
| Groq API downtime | Exponential backoff via tenacity. Fallback hierarchy: 120B → 70B → cached template → supportive holding message + hotlines |
| Cross-session summary loses clinical flags | Summary prompt explicitly preserves: risk_level, referral flags, active clinical themes |
| Model router sends high-risk message to 70B | Threshold set conservatively. Any `risk_level >= medium` always routes to 120B |
| Redis cache miss on session | Fallback to PostgreSQL read. Never block response path. |
| Rate limiter Redis goes down | Fail open with logging. Never block users on limiter failure. |
| Long sessions cause tone/memory drift | Periodic re-anchor summary prevents drift |
| Response quality degrades under model fallback | Response validator catches short/cold responses and triggers regeneration |

---

## 16. Non-Negotiable Rules

- **70B or 120B always writes the final response. 8B never produces user-facing text.**
- **ReAct max steps is enforced in code. Do not trust the model to stop.**
- **Path classifier defaults to COMPLEX. Wrong simple = dangerous. Wrong complex = just slower.**
- **Safety gate runs before everything. No feature flags. No A/B tests. No exceptions.**
- **Rate limiter runs before the safety gate. No exceptions.**
- **Memory write is always async. Never block the response path.**
- **Tools never use LLMs. If a tool needs a model, it is a ReAct step, not a tool.**
- **Crisis response is always hardcoded. Never LLM-generated. Never dynamic.**
- **Emotional intensity is always deterministic. Never read from LLM output.**
- **RAG confidence is always checked. Never assume Top-K is good.**
- **The safety gate is the most important code in this repository. Build it first. Test it obsessively.**

---

## 17. What This System Is

A warm, Hinglish-aware companion that validates emotions, offers evidence-based coping, and refers to professionals when clinical signals exceed its scope.

It is **not** a diagnostic tool. It is **not** a replacement for therapy. PHQ-9 and GAD-7 signals inform context — they are not clinical screening instruments here.

---

*Review the safety gate with a mental health professional who knows Indian linguistic context before any real user touches this system.*
