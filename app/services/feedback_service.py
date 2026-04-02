"""
Feedback Service — RLHF-lite reinforcement learning loop.

Collects per-response thumbs up/down ratings and uses them to update
UserProfile.preferences, shaping Mahi's behavior for each user over time.

RL signal flow:
  User rates response → FeedbackLog stored → Preference aggregation →
  UserProfile.preferences updated → path_classifier + companion_prompt
  read preferences → personalized routing/tone next turn.

Scalability: The aggregation runs in a background task (fire-and-forget).
Fine-tuning export: all FeedbackLogs can be exported as DPO pairs.
"""

import json
from datetime import datetime
from typing import Optional, Dict, List
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Float, Integer, DateTime, select, func
from app.services.session_service import Base, _engine

log = structlog.get_logger()


class FeedbackLog(Base):
    """Raw feedback record for every rated response."""
    __tablename__ = "feedback_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    # Snapshot of the turn for DPO / fine-tuning export
    message_preview: Mapped[str] = mapped_column(Text)
    response_preview: Mapped[str] = mapped_column(Text)
    # Rating: +1 = thumbs up, -1 = thumbs down
    rating: Mapped[int] = mapped_column(Integer)
    # Pipeline context at time of response
    path: Mapped[str] = mapped_column(String, default="simple")
    mode: Mapped[str] = mapped_column(String, default="neutral")      # emotional/action/neutral
    emotional_intensity: Mapped[float] = mapped_column(Float, default=0.0)
    model_used: Mapped[str] = mapped_column(String, default="")
    risk_level: Mapped[str] = mapped_column(String, default="low")
    # Optional free-text reason
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FeedbackService:
    def __init__(self):
        self.engine = _engine

    async def record_feedback(
        self,
        user_id: str,
        session_id: str,
        message_preview: str,
        response_preview: str,
        rating: int,
        path: str = "simple",
        mode: str = "neutral",
        emotional_intensity: float = 0.0,
        model_used: str = "",
        risk_level: str = "low",
        comment: Optional[str] = None,
    ) -> Dict:
        assert rating in (1, -1), "rating must be +1 or -1"
        async with AsyncSession(self.engine) as session:
            log_entry = FeedbackLog(
                user_id=user_id,
                session_id=session_id,
                message_preview=message_preview[:500],
                response_preview=response_preview[:500],
                rating=rating,
                path=path,
                mode=mode,
                emotional_intensity=emotional_intensity,
                model_used=model_used,
                risk_level=risk_level,
                comment=comment,
            )
            session.add(log_entry)
            await session.commit()
            await session.refresh(log_entry)

        # Fire-and-forget preference update
        import asyncio
        task = asyncio.create_task(
            self._update_user_preferences(user_id),
            name=f"rl_update_{user_id}",
        )
        task.add_done_callback(self._log_task_error)

        return {"id": log_entry.id, "status": "recorded"}

    async def _update_user_preferences(self, user_id: str):
        """
        Aggregate feedback signals → update UserProfile.preferences.

        Computed preferences:
        - preferred_mode: mode with highest avg rating
        - avg_rating: overall average (normalized 0-1)
        - total_feedback: total rated turns
        - prefers_shorter_responses: if short responses (< 100 chars) get higher avg
        - high_emotion_preferred: if emotional mode outperforms neutral by >0.2
        """
        try:
            async with AsyncSession(self.engine) as session:
                result = await session.execute(
                    select(FeedbackLog).where(FeedbackLog.user_id == user_id)
                )
                logs = result.scalars().all()

            if not logs:
                return

            total = len(logs)
            avg_rating = sum(l.rating for l in logs) / total
            # Normalize to 0-1
            avg_rating_norm = (avg_rating + 1) / 2

            # Per-mode averages
            mode_sums: Dict[str, List[int]] = {}
            for l in logs:
                mode_sums.setdefault(l.mode, []).append(l.rating)
            mode_avgs = {m: sum(v) / len(v) for m, v in mode_sums.items()}
            preferred_mode = max(mode_avgs, key=mode_avgs.get) if mode_avgs else "neutral"

            # Response length preference: split on median
            positive = [l for l in logs if l.rating == 1]
            negative = [l for l in logs if l.rating == -1]
            avg_pos_len = sum(len(l.response_preview) for l in positive) / len(positive) if positive else 250
            avg_neg_len = sum(len(l.response_preview) for l in negative) / len(negative) if negative else 250
            prefers_shorter = avg_pos_len < avg_neg_len

            # High emotion preference
            emotional_avg = mode_avgs.get("emotional", 0)
            neutral_avg = mode_avgs.get("neutral", 0)
            high_emotion_preferred = (emotional_avg - neutral_avg) > 0.2

            updates = {
                "preferences": {
                    "preferred_mode": preferred_mode,
                    "avg_rating": round(avg_rating_norm, 3),
                    "total_feedback": total,
                    "prefers_shorter_responses": prefers_shorter,
                    "high_emotion_preferred": high_emotion_preferred,
                    "mode_scores": {m: round((v + 1) / 2, 3) for m, v in mode_avgs.items()},
                }
            }

            from app.services.profile_service import ProfileService
            from app.services.session_service import SessionService
            svc = SessionService()
            profile_svc = ProfileService(svc.engine)
            await profile_svc.update_profile(user_id, updates)
            log.info("rl_preferences_updated", user_id=user_id, preferred_mode=preferred_mode, avg_rating=avg_rating_norm)

        except Exception as e:
            log.error("rl_update_failed", user_id=user_id, error=str(e))

    def _log_task_error(self, task):
        if not task.cancelled() and task.exception():
            log.error("rl_background_task_failed", error=str(task.exception()))

    async def get_user_feedback_stats(self, user_id: str) -> Dict:
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(FeedbackLog).where(FeedbackLog.user_id == user_id)
                .order_by(FeedbackLog.created_at.desc())
                .limit(100)
            )
            logs = result.scalars().all()
            if not logs:
                return {"total": 0}

            total = len(logs)
            pos = sum(1 for l in logs if l.rating == 1)
            return {
                "total": total,
                "positive": pos,
                "negative": total - pos,
                "approval_rate": round(pos / total, 3),
                "recent": [
                    {
                        "id": l.id,
                        "rating": l.rating,
                        "mode": l.mode,
                        "created_at": l.created_at.isoformat(),
                    }
                    for l in logs[:10]
                ],
            }

    async def export_dpo_pairs(self, user_id: Optional[str] = None, limit: int = 500) -> List[Dict]:
        """
        Export (chosen, rejected) pairs for DPO fine-tuning.
        Pairs positive (+1) rated responses as 'chosen', negative (-1) as 'rejected'.
        """
        async with AsyncSession(self.engine) as session:
            stmt = select(FeedbackLog)
            if user_id:
                stmt = stmt.where(FeedbackLog.user_id == user_id)
            stmt = stmt.order_by(FeedbackLog.created_at.desc()).limit(limit)
            result = await session.execute(stmt)
            logs = result.scalars().all()

        # Group by (user_id, message_preview) to find pairs
        from collections import defaultdict
        groups: Dict[str, List] = defaultdict(list)
        for l in logs:
            key = f"{l.user_id}::{l.message_preview[:100]}"
            groups[key].append(l)

        pairs = []
        for key, entries in groups.items():
            chosen = [e for e in entries if e.rating == 1]
            rejected = [e for e in entries if e.rating == -1]
            if chosen and rejected:
                pairs.append({
                    "prompt": chosen[0].message_preview,
                    "chosen": chosen[0].response_preview,
                    "rejected": rejected[0].response_preview,
                    "user_id": chosen[0].user_id,
                })

        return pairs
