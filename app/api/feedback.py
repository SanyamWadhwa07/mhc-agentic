"""
Feedback API — RLHF-lite reinforcement learning signal collection.

POST /feedback              — submit thumbs up/down for a response
GET  /feedback/{user_id}    — user's feedback stats
GET  /feedback/export/dpo   — export DPO training pairs (admin)
"""

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional
from app.services.feedback_service import FeedbackService

log = structlog.get_logger()
router = APIRouter(prefix="/feedback", tags=["feedback"])

feedback_svc = FeedbackService()


class FeedbackRequest(BaseModel):
    user_id: str
    session_id: str
    message_preview: str = Field(max_length=500)
    response_preview: str = Field(max_length=500)
    rating: int = Field(description="+1 for thumbs up, -1 for thumbs down")
    path: str = "simple"
    mode: str = "neutral"
    emotional_intensity: float = 0.0
    model_used: str = ""
    risk_level: str = "low"
    comment: Optional[str] = Field(default=None, max_length=500)


@router.post("")
async def submit_feedback(request: FeedbackRequest):
    if request.rating not in (1, -1):
        raise HTTPException(status_code=422, detail="rating must be +1 or -1")
    try:
        result = await feedback_svc.record_feedback(
            user_id=request.user_id,
            session_id=request.session_id,
            message_preview=request.message_preview,
            response_preview=request.response_preview,
            rating=request.rating,
            path=request.path,
            mode=request.mode,
            emotional_intensity=request.emotional_intensity,
            model_used=request.model_used,
            risk_level=request.risk_level,
            comment=request.comment,
        )
        return result
    except Exception as e:
        log.error("feedback_submit_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to record feedback")


@router.get("/{user_id}")
async def get_feedback_stats(user_id: str):
    return await feedback_svc.get_user_feedback_stats(user_id)


@router.get("/export/dpo")
async def export_dpo(
    user_id: Optional[str] = Query(default=None),
    limit: int = Query(default=500, ge=1, le=5000),
):
    """Export (chosen, rejected) pairs for DPO fine-tuning."""
    pairs = await feedback_svc.export_dpo_pairs(user_id=user_id, limit=limit)
    return {"count": len(pairs), "pairs": pairs}
