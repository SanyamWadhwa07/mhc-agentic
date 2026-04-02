"""
Assessment API — PHQ-9 / GAD-7 score endpoints.

GET /assessment/{user_id}            — current scores + severity
GET /assessment/{user_id}/trajectory — longitudinal score history (for mood arc)
"""

import structlog
from fastapi import APIRouter, Query
from app.services.assessment_service import AssessmentService

log = structlog.get_logger()
router = APIRouter(prefix="/assessment", tags=["assessment"])

assessment_svc = AssessmentService()


@router.get("/{user_id}")
async def get_assessment(user_id: str):
    """
    Returns current PHQ-9 and GAD-7 scores for the user.
    Scores are rolling weighted averages across all chat turns and journal entries.
    """
    scores = await assessment_svc.get_scores(user_id)
    return {"user_id": user_id, **scores}


@router.get("/{user_id}/trajectory")
async def get_trajectory(
    user_id: str,
    limit: int = Query(default=30, ge=5, le=200),
):
    """
    Returns chronological score snapshots for mood arc / trend visualization.
    Each point is a turn or journal entry where signals were detected.
    """
    trajectory = await assessment_svc.get_trajectory(user_id, limit=limit)
    return {"user_id": user_id, "trajectory": trajectory, "count": len(trajectory)}
