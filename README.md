# MHC Agentic V4 — Mental Health Companion

> Cheap models handle structure. Expensive models handle humans. Deterministic systems handle safety.

A Hinglish-aware, agentic mental health companion for India — built on LangGraph with a cost-efficient model routing pipeline.

---

## What it does

A warm, Gen Z-toned chatbot that validates emotions, offers evidence-based coping, and refers to professionals when clinical signals exceed its scope. It is **not** a diagnostic tool and **not** a replacement for therapy.

---

## Architecture at a glance

```
User Input
  │
[Rate Limiter]        — Redis token bucket, ZERO LLM
[Safety Gate]         — Keyword + semantic embedding crisis check, PII scrub
[Emotional Scorer]    — Deterministic intensity score, ZERO LLM
[Path Classifier]     — Numeric complexity score → simple or complex
  │
  ├─ SIMPLE PATH (~55%)
  │     Single 70B call → response
  │
  └─ COMPLEX PATH (~45%)
        [ReAct Agent]  — 8B model, max 4 steps, hardened loop
        [RAG Tools]    — ChromaDB semantic search, domain-filtered
        [RAG Confidence Check] — avg_similarity gates bad retrieval
        [Model Router] — Routes to 120B on high risk / emotion / low RAG confidence
        Final 70B or 120B call → response
  │
[Response Validator]  — Length + empathy check, regenerates if needed
[Output Normalizer]   — Strips clinical language, enforces tone
[Observability]       — Latency, model used, RAG confidence, react steps
[Memory Write]        — Async PostgreSQL/SQLite + Redis, never blocks response
```

**LLM call budget:** Crisis = 0 calls · Simple = 1 call · Complex = 2–3 calls · Weighted avg ~1.5 calls

---

## Key design decisions

| Decision | Reason |
|---|---|
| Deterministic emotional scorer | Circular dependency if read from LLM output |
| 8B only for ReAct reasoning, never final response | Cost — 8B is cheap, 70B/120B write to humans |
| Safety gate before everything, no feature flags | Safety is not a feature |
| Rate limiter fails open if Redis is down | Never block a user because of infrastructure |
| SQLite default, PostgreSQL-ready | Zero setup locally, swap one env var to scale |
| Hinglish semantic safety anchors | Keyword regex misses indirect crisis phrases |
| Companion prompt rewritten v2 | Shorter, no opener word repetition, strict 3-sentence + 1-question rule |

---

## Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph |
| LLM | Groq (llama-4-scout-17b ReAct, llama-3.3-70b simple path, openai/gpt-oss-120b complex/high-risk) |
| RAG | ChromaDB + all-MiniLM-L6-v2 |
| DB | SQLite (default) → PostgreSQL (production) |
| Cache / Rate limit | Redis |
| API | FastAPI |
| UI | Streamlit |

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

# Start UI (separate terminal)
streamlit run streamlit_app.py
```

Ingest knowledge base:
```bash
python -m app.rag.ingest
```

---

## Environment variables

See [.env.example](.env.example) for all variables. Key ones:

```env
GROQ_API_KEY=                                              # required
GROQ_FAST_MODEL=meta-llama/llama-4-scout-17b-16e-instruct  # ReAct reasoning
GROQ_QUALITY_MODEL=llama-3.3-70b-versatile                 # simple path + fallback
QUALITY_RESPONSE_MODEL=openai/gpt-oss-120b                 # complex / high-risk path
DATABASE_URL=sqlite+aiosqlite:///./mhc.db                  # swap to postgres+asyncpg for prod
```

---

## API

```
POST /chat
  { "message": str, "user_id": str?, "session_id": str? }
  → { "response", "emotions", "risk_level", "clinical_flags", "referral_needed", "session_id", "metrics" }

GET /health
  → { "status": "ok", "version": "4.0.0" }
```

---

## Safety

The safety gate is the most important code in this repo. It runs before every other node — no exceptions, no feature flags.

- **Layer 1:** Deterministic keyword matching (Hindi + Hinglish + English, word-boundary safe)
- **Layer 2:** Semantic embedding similarity against crisis anchor phrases
- **Crisis response:** Always hardcoded. Never LLM-generated. Includes iCall (9152987821), Vandrevala (1860-2662-345), AASRA (9820466627).

**Review the safety gate with a mental health professional who knows Indian linguistic context before any real users touch this system.**

---

## Project structure

```
app/
├── graph/          LangGraph nodes + builder
│   └── nodes/      rate_limiter, safety_gate, emotional_scorer, path_classifier,
│                   direct_responder, react_agent, rag_confidence, model_router,
│                   response_validator, output_normalizer, observability,
│                   memory_update, profile_extractor
├── tools/          ReAct tools (ALL zero LLM)
├── safety/         Crisis detector, semantic safety, PII scrubber, sanitizer
├── rag/            Embedder, ChromaDB, retriever, confidence scorer, ingest
├── knowledge/      JSON knowledge bases (therapy, assessment, crisis, resource)
├── prompts/        System prompts (companion, react, summary)
├── services/       LLM service (Groq + fallback), session DB, Redis cache
├── config.py       Pydantic Settings
└── main.py         FastAPI app

tests/
├── test_safety/
├── test_rag/
├── test_graph/
└── test_api/

run_crisis_test.py   — 20-turn end-to-end conversation simulation (crisis arc)
```

---

*Not a replacement for professional mental health care.*
