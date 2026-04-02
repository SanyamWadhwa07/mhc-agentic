"""
Journal Service — Replika-inspired journaling with AI reflection.

Users write free-form journal entries. Each entry:
1. Gets an empathetic AI reflection from Mahi
2. Contributes passive PHQ-9/GAD-7 signals (same as chat turns)
3. Is stored with mood tags extracted from the text

Session-wise: recent journal entries are injected as context into the
companion prompt so Mahi remembers what the user has written.
"""

import json
from datetime import datetime
from typing import Optional, Dict, List
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Float, Integer, DateTime, Boolean, select
from app.services.session_service import Base, _engine

log = structlog.get_logger()


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    content: Mapped[str] = mapped_column(Text)
    mood_tags: Mapped[str] = mapped_column(Text, default="[]")          # JSON list of mood strings
    ai_reflection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emotional_intensity: Mapped[float] = mapped_column(Float, default=0.0)
    assessment_signals: Mapped[str] = mapped_column(Text, default="{}")  # PHQ-9/GAD-7 raw signals
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)     # user can mark private
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class JournalService:
    def __init__(self):
        self.engine = _engine

    async def create_entry(
        self,
        user_id: str,
        content: str,
        mood_tags: List[str] = None,
        ai_reflection: Optional[str] = None,
        emotional_intensity: float = 0.0,
        assessment_signals: Optional[Dict] = None,
        is_private: bool = False,
    ) -> Dict:
        async with AsyncSession(self.engine) as session:
            entry = JournalEntry(
                user_id=user_id,
                content=content,
                mood_tags=json.dumps(mood_tags or []),
                ai_reflection=ai_reflection,
                emotional_intensity=emotional_intensity,
                assessment_signals=json.dumps(assessment_signals or {}),
                is_private=is_private,
            )
            session.add(entry)
            await session.commit()
            await session.refresh(entry)
            return self._serialize(entry)

    async def get_entries(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict]:
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(JournalEntry)
                .where(JournalEntry.user_id == user_id)
                .order_by(JournalEntry.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            entries = result.scalars().all()
            return [self._serialize(e) for e in entries]

    async def get_recent_context(self, user_id: str, n: int = 3) -> str:
        """Returns last N non-private entries formatted for companion prompt injection."""
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(JournalEntry)
                .where(
                    JournalEntry.user_id == user_id,
                    JournalEntry.is_private == False,  # noqa: E712
                )
                .order_by(JournalEntry.created_at.desc())
                .limit(n)
            )
            entries = result.scalars().all()
            if not entries:
                return ""
            lines = ["[Recent journal entries — use for deeper context, don't mention directly unless relevant]"]
            for e in reversed(entries):
                date_str = e.created_at.strftime("%b %d")
                mood_str = ", ".join(json.loads(e.mood_tags)) if e.mood_tags else ""
                snippet = e.content[:200] + ("..." if len(e.content) > 200 else "")
                line = f"[{date_str}]"
                if mood_str:
                    line += f" [{mood_str}]"
                line += f" {snippet}"
                lines.append(line)
            return "\n".join(lines)

    async def update_reflection(self, entry_id: int, user_id: str, reflection: str):
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(JournalEntry).where(
                    JournalEntry.id == entry_id,
                    JournalEntry.user_id == user_id,
                )
            )
            entry = result.scalar_one_or_none()
            if entry:
                entry.ai_reflection = reflection
                await session.commit()

    def _serialize(self, entry: JournalEntry) -> Dict:
        return {
            "id": entry.id,
            "user_id": entry.user_id,
            "content": entry.content,
            "mood_tags": json.loads(entry.mood_tags or "[]"),
            "ai_reflection": entry.ai_reflection,
            "emotional_intensity": entry.emotional_intensity,
            "assessment_signals": json.loads(entry.assessment_signals or "{}"),
            "is_private": entry.is_private,
            "created_at": entry.created_at.isoformat(),
        }
