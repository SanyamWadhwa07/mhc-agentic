import json
from datetime import datetime
from typing import Optional, List, Dict
import structlog
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, Boolean, DateTime, Integer, select, func
from app.config import settings

log = structlog.get_logger()

# Module-level engine singleton — avoids creating a new engine per request.
# SQLite (aiosqlite) uses StaticPool by default and does not support pool_size/max_overflow.
_engine = create_async_engine(settings.database_url, echo=settings.debug_mode)


class Base(DeclarativeBase):
    pass


class Turn(Base):
    __tablename__ = "turns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    message: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    emotions: Mapped[str] = mapped_column(Text, default="[]")
    risk_level: Mapped[str] = mapped_column(String, default="low")
    clinical_flags: Mapped[str] = mapped_column(Text, default="[]")
    referral_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    metrics: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SessionSummary(Base):
    __tablename__ = "session_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    session_id: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SessionService:
    def __init__(self):
        self.engine = _engine  # reuse module-level singleton

    async def init_db(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def save_turn(self, user_id, session_id, message, response, emotions, risk_level, clinical_flags, referral_needed, metrics):
        async with AsyncSession(self.engine) as session:
            turn = Turn(
                user_id=user_id,
                session_id=session_id,
                message=message,
                response=response,
                emotions=json.dumps(emotions),
                risk_level=risk_level,
                clinical_flags=json.dumps(clinical_flags),
                referral_needed=referral_needed,
                metrics=json.dumps(metrics),
            )
            session.add(turn)
            await session.commit()

    async def get_recent_history(self, user_id: str, session_id: Optional[str], n: int = 5) -> List[Dict]:
        async with AsyncSession(self.engine) as session:
            stmt = select(Turn).where(Turn.user_id == user_id)
            if session_id:
                stmt = stmt.where(Turn.session_id == session_id)
            stmt = (
                stmt
                .order_by(Turn.created_at.desc())
                .limit(n)
            )
            result = await session.execute(stmt)
            turns = result.scalars().all()
            return [
                {"message": t.message, "response": t.response, "risk_level": t.risk_level}
                for t in reversed(turns)
            ]

    async def get_exchange_count(self, user_id: str, session_id: str) -> int:
        async with AsyncSession(self.engine) as session:
            stmt = select(func.count(Turn.id)).where(
                Turn.user_id == user_id,
                Turn.session_id == session_id
            )
            result = await session.execute(stmt)
            return result.scalar() or 0

    async def get_latest_summary(self, user_id: str, session_id: Optional[str] = None) -> Optional[str]:
        async with AsyncSession(self.engine) as session:
            stmt = select(SessionSummary).where(SessionSummary.user_id == user_id)
            if session_id:
                stmt = stmt.where(SessionSummary.session_id == session_id)
            stmt = (
                stmt
                .order_by(SessionSummary.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            summary = result.scalar_one_or_none()
            return summary.summary if summary else None

    async def save_summary(self, user_id: str, session_id: str, summary: str):
        async with AsyncSession(self.engine) as session:
            s = SessionSummary(user_id=user_id, session_id=session_id, summary=summary)
            session.add(s)
            await session.commit()
