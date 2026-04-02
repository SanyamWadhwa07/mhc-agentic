import time
import uuid
import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from app.graph.builder import mhc_graph
from app.graph.state import MHCState
from app.config import settings
from app.services.session_service import SessionService
from app.services.cache_service import CacheService
from app.api.journal import router as journal_router
from app.api.feedback import router as feedback_router
from app.api.assessment import router as assessment_router
from app.api.analytics import router as analytics_router

log = structlog.get_logger()
app = FastAPI(title="MHC Agentic V4", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register feature routers
app.include_router(journal_router)
app.include_router(feedback_router)
app.include_router(assessment_router)
app.include_router(analytics_router)

session_svc = SessionService()
cache_svc = CacheService()


@app.on_event("startup")
async def startup():
    try:
        await session_svc.init_db()
        # Import all ORM models so their tables are created via shared Base metadata
        from app.services.profile_service import UserProfile  # noqa: F401
        from app.services.assessment_service import AssessmentScore, AssessmentHistory  # noqa: F401
        from app.services.journal_service import JournalEntry  # noqa: F401
        from app.services.feedback_service import FeedbackLog  # noqa: F401
        async with session_svc.engine.begin() as conn:
            from app.services.session_service import Base
            await conn.run_sync(Base.metadata.create_all)
        log.info("database_initialized")
    except Exception as e:
        log.warning("database_init_failed", error=str(e))


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    user_id: Optional[str] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    emotions: list
    risk_level: str
    clinical_flags: list
    referral_needed: bool
    session_id: str
    metrics: dict


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    user_id = request.user_id or f"anon_{uuid.uuid4().hex[:8]}"
    session_id = request.session_id or str(uuid.uuid4())

    try:
        # Try Redis cache first; fall back to DB on miss or Redis unavailability
        try:
            cached = await cache_svc.get_session(session_id) if request.session_id else {}
        except Exception:
            cached = {}

        if cached:
            history = cached.get("history", [])
            summary = cached.get("summary", "")
        else:
            history = await session_svc.get_recent_history(user_id, session_id=session_id, n=5)
            summary = await session_svc.get_latest_summary(user_id, session_id=session_id)

        last_risk = history[-1]["risk_level"] if history else "low"

        # Load journal context (recent non-private entries for prompt injection)
        journal_context = ""
        try:
            from app.services.journal_service import JournalService
            journal_svc = JournalService()
            journal_context = await journal_svc.get_recent_context(user_id, n=settings.journal_context_turns)
        except Exception:
            pass

        initial_state: MHCState = {
            "user_id": user_id,
            "session_id": session_id,
            "message": request.message,
            "is_crisis": False,
            "crisis_response": None,
            "is_rate_limited": False,
            "sanitized_message": request.message,
            "emotional_intensity": 0.0,
            "path": "simple",
            "complexity_score": 0.0,
            "react_steps": 0,
            "tool_results": [],
            "rag_confidence": 1.0,
            "model_used": settings.groq_quality_model,
            "selected_model": settings.groq_quality_model,
            "fallback_triggered": False,
            "session_history": history,
            "session_summary": summary,
            "last_risk_level": last_risk,
            "user_profile": "",
            "journal_context": journal_context,
            "assessment_context": "",
            "response_mode": "neutral",
            "response": "",
            "emotions": [],
            "risk_level": "low",
            "clinical_flags": [],
            "referral_needed": False,
            "metrics": {},
            "start_time": time.time(),
        }

        result = await mhc_graph.ainvoke(initial_state)

        # Handle early exits (rate limit / crisis)
        if result.get("is_rate_limited"):
            return ChatResponse(
                response=result["response"],
                emotions=[],
                risk_level="low",
                clinical_flags=[],
                referral_needed=False,
                session_id=session_id,
                metrics={}
            )

        if result.get("is_crisis"):
            return ChatResponse(
                response=result["crisis_response"],
                emotions=["crisis"],
                risk_level="high",
                clinical_flags=["crisis_detected"],
                referral_needed=True,
                session_id=session_id,
                metrics={}
            )

        # Write updated session to Redis cache (best-effort, non-blocking)
        try:
            new_turn = {
                "message": request.message,
                "response": result["response"],
                "risk_level": result.get("risk_level", "low"),
            }
            await cache_svc.set_session(session_id, {
                "history": (history + [new_turn])[-5:],
                "summary": summary or "",
            })
        except Exception:
            pass  # cache failure is non-fatal

        return ChatResponse(
            response=result["response"],
            emotions=result.get("emotions", []),
            risk_level=result.get("risk_level", "low"),
            clinical_flags=result.get("clinical_flags", []),
            referral_needed=result.get("referral_needed", False),
            session_id=session_id,
            metrics=result.get("metrics", {})
        )

    except Exception as e:
        log.error("chat_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "4.0.0"}
