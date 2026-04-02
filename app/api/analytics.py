"""
Analytics API — session-wise and user-level analytics.

GET /analytics/{user_id}/sessions           — list all sessions with metadata
GET /analytics/{user_id}/sessions/{session_id} — single session analytics
GET /analytics/{user_id}/summary            — overall user analytics
"""

import json
import structlog
from fastapi import APIRouter, Query
from app.services.session_service import SessionService, Turn, SessionSummary
from app.services.assessment_service import AssessmentService, AssessmentHistory
from app.services.journal_service import JournalService, JournalEntry
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct

log = structlog.get_logger()
router = APIRouter(prefix="/analytics", tags=["analytics"])

session_svc = SessionService()
assessment_svc = AssessmentService()
journal_svc = JournalService()


@router.get("/{user_id}/sessions")
async def list_sessions(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Returns all sessions for a user with metadata:
    turn count, mood trajectory, risk arc, referral flags.
    """
    async with AsyncSession(session_svc.engine) as session:
        # Get distinct session_ids ordered by most recent
        result = await session.execute(
            select(
                Turn.session_id,
                func.count(Turn.id).label("turn_count"),
                func.min(Turn.created_at).label("started_at"),
                func.max(Turn.created_at).label("last_turn_at"),
            )
            .where(Turn.user_id == user_id)
            .group_by(Turn.session_id)
            .order_by(func.max(Turn.created_at).desc())
            .limit(limit)
        )
        rows = result.all()

    sessions = []
    for row in rows:
        sid = row.session_id
        # Get risk arc for this session
        async with AsyncSession(session_svc.engine) as session:
            turns_result = await session.execute(
                select(Turn.risk_level, Turn.referral_needed, Turn.emotions)
                .where(Turn.user_id == user_id, Turn.session_id == sid)
                .order_by(Turn.created_at.asc())
            )
            turns = turns_result.all()

        risk_arc = [t.risk_level for t in turns]
        referral_needed = any(t.referral_needed for t in turns)
        all_emotions = []
        for t in turns:
            try:
                all_emotions.extend(json.loads(t.emotions or "[]"))
            except Exception:
                pass
        # Top 3 emotions
        emotion_counts = {}
        for e in all_emotions:
            emotion_counts[e] = emotion_counts.get(e, 0) + 1
        top_emotions = sorted(emotion_counts, key=emotion_counts.get, reverse=True)[:3]

        sessions.append({
            "session_id": sid,
            "turn_count": row.turn_count,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "last_turn_at": row.last_turn_at.isoformat() if row.last_turn_at else None,
            "risk_arc": risk_arc,
            "peak_risk": max(risk_arc, key=lambda r: {"low": 0, "medium": 1, "high": 2}.get(r, 0)) if risk_arc else "low",
            "referral_needed": referral_needed,
            "top_emotions": top_emotions,
        })

    return {"user_id": user_id, "sessions": sessions, "count": len(sessions)}


@router.get("/{user_id}/sessions/{session_id}")
async def get_session_analytics(user_id: str, session_id: str):
    """
    Full analytics for a single session:
    - turn-by-turn risk + emotion arc
    - PHQ-9/GAD-7 snapshots from this session
    - session summary (if generated)
    """
    async with AsyncSession(session_svc.engine) as db:
        # All turns
        turns_result = await db.execute(
            select(Turn)
            .where(Turn.user_id == user_id, Turn.session_id == session_id)
            .order_by(Turn.created_at.asc())
        )
        turns = turns_result.scalars().all()

        # Session summary
        summary_result = await db.execute(
            select(SessionSummary)
            .where(SessionSummary.user_id == user_id, SessionSummary.session_id == session_id)
            .order_by(SessionSummary.created_at.desc())
            .limit(1)
        )
        summary = summary_result.scalar_one_or_none()

        # Assessment snapshots from this session
        assess_result = await db.execute(
            select(AssessmentHistory)
            .where(
                AssessmentHistory.user_id == user_id,
                AssessmentHistory.session_id == session_id,
            )
            .order_by(AssessmentHistory.created_at.asc())
        )
        assess_snaps = assess_result.scalars().all()

    turn_data = []
    for t in turns:
        turn_data.append({
            "message_preview": t.message[:100],
            "response_preview": t.response[:150],
            "emotions": json.loads(t.emotions or "[]"),
            "risk_level": t.risk_level,
            "referral_needed": t.referral_needed,
            "clinical_flags": json.loads(t.clinical_flags or "[]"),
            "created_at": t.created_at.isoformat(),
        })

    assessment_arc = [
        {
            "phq9_score": s.phq9_score,
            "phq9_severity": s.phq9_severity,
            "gad7_score": s.gad7_score,
            "gad7_severity": s.gad7_severity,
            "created_at": s.created_at.isoformat(),
        }
        for s in assess_snaps
    ]

    return {
        "session_id": session_id,
        "user_id": user_id,
        "turn_count": len(turns),
        "turns": turn_data,
        "summary": summary.summary if summary else None,
        "assessment_arc": assessment_arc,
    }


@router.get("/{user_id}/summary")
async def get_user_summary(user_id: str):
    """Overall cross-session user analytics."""
    async with AsyncSession(session_svc.engine) as db:
        # Total turns
        total_turns = await db.execute(
            select(func.count(Turn.id)).where(Turn.user_id == user_id)
        )
        # Total sessions
        total_sessions = await db.execute(
            select(func.count(distinct(Turn.session_id))).where(Turn.user_id == user_id)
        )
        # High-risk turns
        high_risk = await db.execute(
            select(func.count(Turn.id)).where(
                Turn.user_id == user_id,
                Turn.risk_level == "high",
            )
        )
        # Referral turns
        referrals = await db.execute(
            select(func.count(Turn.id)).where(
                Turn.user_id == user_id,
                Turn.referral_needed == True,  # noqa: E712
            )
        )
        # Journal count
        journal_count = await db.execute(
            select(func.count(JournalEntry.id)).where(JournalEntry.user_id == user_id)
        )

    assessment = await assessment_svc.get_scores(user_id)

    return {
        "user_id": user_id,
        "total_turns": total_turns.scalar() or 0,
        "total_sessions": total_sessions.scalar() or 0,
        "high_risk_turns": high_risk.scalar() or 0,
        "referral_turns": referrals.scalar() or 0,
        "journal_entries": journal_count.scalar() or 0,
        "current_phq9": assessment.get("phq9_score", 0.0),
        "phq9_severity": assessment.get("phq9_severity", "minimal"),
        "current_gad7": assessment.get("gad7_score", 0.0),
        "gad7_severity": assessment.get("gad7_severity", "minimal"),
    }
