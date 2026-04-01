import time
import uuid
import structlog
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from app.graph.builder import mhc_graph
from app.graph.state import MHCState
from app.config import settings
from app.services.session_service import SessionService

log = structlog.get_logger()
app = FastAPI(title="MHC Agentic V4", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

session_svc = SessionService()


@app.on_event("startup")
async def startup():
    try:
        await session_svc.init_db()
        log.info("database_initialized")
    except Exception as e:
        log.warning("database_init_failed", error=str(e))


class ChatRequest(BaseModel):
    message: str
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
        # Load prior context — history across ALL sessions for this user (last 5 turns)
        history = await session_svc.get_recent_history(user_id, session_id=None, n=5)
        summary = await session_svc.get_latest_summary(user_id)
        last_risk = history[-1]["risk_level"] if history else "low"

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
