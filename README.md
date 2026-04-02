# MHC Agentic V4 — Mental Health Companion

> Cheap models handle structure. Expensive models handle humans. Deterministic systems handle safety.

A Hinglish-aware, agentic mental health companion for India — built on LangGraph with cost-efficient model routing, passive clinical assessment, journaling, and reinforcement learning from user feedback.

---

## What it does

Mahi is a warm, Gen Z-toned companion that validates emotions, offers evidence-based coping, and escalates to professionals when clinical signals exceed its scope. It is **not** a diagnostic tool and **not** a replacement for therapy.

---

## Architecture

```
User Input
  │
[Rate Limiter]          — Redis token bucket, ZERO LLM
[Safety Gate]           — Keyword + semantic embedding crisis check, PII scrub
[Emotional Scorer]      — Deterministic intensity score, ZERO LLM
[Profile Extractor]     — Persistent user profile (name, stressors, people, situations)
[Path Classifier]       — Complexity score → simple or complex (greetings always simple)
  │
  ├─ SIMPLE PATH
  │     Single 70B call → response
  │
  └─ COMPLEX PATH
        [ReAct Agent]   — llama-4-scout-17b, max 4 steps
        [RAG Tools]     — ChromaDB semantic search, domain-filtered
        [RAG Confidence Check]
        [Model Router]  — 120B on high risk / high emotion / low RAG confidence
        Final 70B or 120B call → response
  │
[Response Validator]    — Empathy check only on emotional turns; 40-char floor
[Output Normalizer]     — Strips clinical language, enforces tone
[Observability]         — Latency, model, RAG confidence, react steps logged
[Memory Write]          — Async SQLite/PostgreSQL + Redis, fire-and-forget
[Assessment Tracker]    — Background PHQ-9/GAD-7 signal extraction, ZERO latency impact
```

**LLM call budget:** Crisis = 0 · Simple = 1 · Complex = 2–3 · Weighted avg ~1.5 calls

---

## Features

### Core Pipeline
- **Hinglish-aware safety gate** — 4-layer crisis detection (hard/soft/contextual/indian_context) with negation window. Crisis response is always hardcoded, never LLM-generated. Includes iCall, Vandrevala, AASRA helplines.
- **Cost-efficient model routing** — 70B default, 120B only for high-risk + high-emotion + low RAG confidence.
- **ReAct agent** with 5 zero-LLM tools (TherapyTool, AssessmentTool, ResourceTool, MemoryReadTool, RiskEvaluator).
- **Persistent user profile** — name, stressors, people, situations extracted per turn and injected as context.
- **Auto-summarizing memory** — conversation summarized every N turns (configurable), prevents prompt bloat.
- **Greeting bypass** — pure greetings (`hi`, `hello`, `namaste`, etc.) always take the simple path and receive no emotional context injection.
- **Risk decay** — a prior `medium/high` risk flag resets after N consecutive low-risk turns, preventing indefinite complex routing.

### Conversation Quality Fixes
- **Companion prompt is intentionally short** — capable 70B models don't need 200-line instruction manuals. Only persona, output schema, and risk thresholds are specified. Everything else is trusted to the model.
- **Temperature 0.5** — lower than default 0.75 to reduce creative drift and produce more consistent JSON.
- **Empathy check gated on emotional intensity** — the response validator only forces empathy markers on high-intensity turns. Greetings and neutral messages are never forced to regenerate.
- **TextBlob fallback is 0.0** — no signal means no emotional intensity score. Neutral text no longer gets a phantom 0.3 intensity floor.

### PHQ-9 / GAD-7 Background Assessment
Passively tracks depression and anxiety signals across every conversation turn and journal entry — no questionnaires. Uses exponential moving average (alpha decays with turn count).

- Rolling scores updated per turn, stored per user
- Session snapshots for longitudinal mood arc visualization
- Severity context injected into companion prompt when above `minimal`
- Sources: `chat` turns + `journal` entries

### Journaling (Replika-inspired)
Users write free-form journal entries. Each entry:
1. Gets an empathetic AI reflection from Mahi
2. Contributes PHQ-9/GAD-7 assessment signals
3. Stores mood tags (user-provided + LLM-inferred)
4. Injects recent non-private entries as context into the companion prompt

### Reinforcement Learning (RLHF-lite)
Thumbs up/down per response shapes Mahi's behavior per user over time.

Signal flow:
```
User rates response → FeedbackLog stored → Preference aggregation (background task) →
UserProfile.preferences updated → companion_prompt reads prefs → personalized mode next turn
```

Learned preferences: `preferred_mode`, `avg_rating`, `high_emotion_preferred`, `prefers_shorter_responses`, `mode_scores`

DPO export: all feedback logs exportable as `(chosen, rejected)` pairs for fine-tuning.

### Session Analytics
- Per-session risk arc, emotion arc, peak risk, referral flags, top emotions
- PHQ-9/GAD-7 score trajectory across sessions
- User-level summary (total turns, sessions, high-risk turns, journal entries)

---

## Key design decisions

| Decision | Reason |
|---|---|
| Short companion prompt | Over-specification confuses capable models — 8 rules beat 80 |
| Deterministic emotional scorer | Circular dependency if intensity is read from LLM output |
| llama-4-scout-17b for ReAct only | Cheap/fast for reasoning; 70B/120B write to humans |
| Safety gate before everything | Safety is not a feature — no flags, no exceptions |
| Rate limiter fails open if Redis is down | Never block a user because of infrastructure |
| SQLite default, PostgreSQL-ready | Zero setup locally, one env var to scale |
| Hinglish semantic safety anchors | Keyword regex misses indirect crisis phrases |
| Greeting → always simple path | Greetings should never touch the ReAct agent |
| Risk decay after N low-risk turns | One medium-risk message shouldn't ratchet forever |
| Temperature 0.5 | Consistent structured JSON output; less creative drift |
| Empathy check gated on intensity | Don't regenerate natural short responses on low-intensity turns |
| Assessment tracker fire-and-forget | Never delays response pipeline |
| RL bias gated at ≥5 feedback turns | Avoid noisy preferences from 1-2 data points |
| API fallback template is low-risk | Network errors are not crises — no helplines on infra failures |

---

## Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph |
| LLM | Groq (llama-4-scout-17b ReAct, llama-3.3-70b simple, openai/gpt-oss-120b complex/high-risk) |
| RAG | ChromaDB + all-MiniLM-L6-v2 |
| DB | SQLite (default) → PostgreSQL (production) |
| Cache / Rate limit | Redis |
| API | FastAPI |
| UI | Next.js 14 + Tailwind CSS + Framer Motion |

---

## Quickstart

```bash
python -m venv venv
source venv/Scripts/activate   # Windows: venv\Scripts\activate

pip install -e .

cp .env.example .env
# Add your GROQ_API_KEY

# Start backend
uvicorn app.main:app --reload

# Start frontend (separate terminal)
cd frontend && npm install && npm run dev
```

Frontend: http://localhost:3000 · Backend: http://localhost:8000

```bash
# Ingest knowledge base (first time only)
python -m app.rag.ingest
```

---

## Environment variables

```env
GROQ_API_KEY=                                              # required
GROQ_FAST_MODEL=meta-llama/llama-4-scout-17b-16e-instruct  # ReAct + assessment extraction
GROQ_QUALITY_MODEL=llama-3.3-70b-versatile                 # simple path + journal reflection
QUALITY_RESPONSE_MODEL=openai/gpt-oss-120b                 # complex / high-risk path

DATABASE_URL=sqlite+aiosqlite:///./mhc.db                  # swap to postgres+asyncpg for prod
REDIS_URL=redis://localhost:6379

# Routing
EMOTIONAL_INTENSITY_THRESHOLD=0.5
RISK_DECAY_TURNS=3
LLM_TEMPERATURE=0.5

# Assessment
ASSESSMENT_ENABLED=true
JOURNAL_CONTEXT_TURNS=3
```

> **Common mistake:** Do not set `GROQ_FAST_MODEL=llama-3.1-8b-instant`. The 8B model is not capable enough for mental health conversation — it over-classifies risk and produces scripted responses. Use llama-4-scout-17b.

---

## API

```
POST /chat
  { "message": str, "user_id": str?, "session_id": str? }
  → { "response", "emotions", "risk_level", "clinical_flags", "referral_needed", "session_id", "metrics" }

POST /journal
  { "user_id": str, "content": str, "mood_tags": list?, "is_private": bool? }
  → { "id", "ai_reflection", "mood_tags", "emotional_intensity", "created_at" }

GET  /journal/{user_id}?limit=20&offset=0
GET  /journal/{user_id}/context

POST /feedback
  { "user_id": str, "session_id": str, "message_preview": str, "response_preview": str,
    "rating": +1|-1, "path": str, "mode": str, "emotional_intensity": float, "model_used": str }
GET  /feedback/{user_id}
GET  /feedback/export/dpo?user_id=...&limit=500

GET  /assessment/{user_id}
GET  /assessment/{user_id}/trajectory?limit=30

GET  /analytics/{user_id}/sessions
GET  /analytics/{user_id}/sessions/{session_id}
GET  /analytics/{user_id}/summary

GET  /health
```

---

## Safety

The safety gate is the most important code in this repo. It runs before every other node — no exceptions, no feature flags.

- **Layer 1:** Deterministic keyword matching (Hindi + Hinglish + English, word-boundary safe, negation window)
- **Layer 2:** Semantic embedding similarity against 60+ crisis anchor phrases (threshold configurable, default 0.82)
- **Crisis response:** Always hardcoded. Never LLM-generated. Includes iCall (9152987821), Vandrevala (1860-2662-345), AASRA (9820466627).

**Have a mental health professional who knows Indian linguistic context review the safety gate before real users touch this system.**

---

## Project structure

```
app/
├── graph/
│   ├── nodes/        rate_limiter, safety_gate, emotional_scorer, path_classifier,
│   │                 direct_responder, react_agent, rag_confidence, model_router,
│   │                 response_validator, output_normalizer, observability,
│   │                 memory_update, profile_extractor, assessment_tracker
│   ├── builder.py    LangGraph StateGraph (15-node pipeline)
│   └── state.py      MHCState TypedDict
├── api/              journal, feedback, assessment, analytics routers
├── tools/            ReAct tools (ALL zero LLM)
├── safety/           Crisis detector, semantic safety, PII scrubber, sanitizer
├── rag/              Embedder, ChromaDB, retriever, confidence scorer, ingest
├── knowledge/        JSON knowledge bases (therapy, assessment, crisis, resource)
├── prompts/          companion_prompt, assessment_prompt, journal_prompt, summary
├── services/         llm_service, session_service, cache_service, profile_service,
│                     assessment_service, journal_service, feedback_service
├── config.py
└── main.py

frontend/             Next.js 14 + Tailwind + Framer Motion

run_crisis_test.py    20-turn end-to-end conversation simulation
```

---

*Not a replacement for professional mental health care.*
