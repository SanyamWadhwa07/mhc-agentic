"""
PHQ-9 / GAD-7 Background Assessment Service

Passively tracks depression (PHQ-9) and anxiety (GAD-7) signals from natural
conversation — no questionnaire forms. Scores update as a rolling weighted
average across turns, giving a longitudinal view of mental health trajectory.

PHQ-9 severity: 0-4 minimal, 5-9 mild, 10-14 moderate, 15-19 mod-severe, 20+ severe
GAD-7 severity: 0-4 minimal, 5-9 mild, 10-14 moderate, 15+ severe
"""

import json
from datetime import datetime
from typing import Optional, Dict, List
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, Float, Integer, DateTime, select
from app.services.session_service import Base, _engine

log = structlog.get_logger()

# PHQ-9 item keys and their clinical descriptions
PHQ9_ITEMS = [
    "anhedonia",          # little interest/pleasure
    "depressed_mood",     # feeling down/depressed/hopeless
    "sleep",              # trouble sleeping/oversleeping
    "fatigue",            # feeling tired, low energy
    "appetite",           # poor appetite or overeating
    "worthlessness",      # feeling bad about yourself, failure
    "concentration",      # trouble concentrating
    "psychomotor",        # moving/speaking slow or restless
    "suicidality",        # thoughts of self-harm or death
]

# GAD-7 item keys
GAD7_ITEMS = [
    "nervous",            # feeling nervous/anxious/on edge
    "uncontrollable_worry",  # can't stop worrying
    "excessive_worry",    # worrying too much about things
    "relaxation",         # trouble relaxing
    "restless",           # too restless to sit still
    "irritable",          # easily annoyed/irritable
    "afraid",             # feeling afraid, something awful will happen
]

SEVERITY_LABELS = {
    "phq9": [(5, "minimal"), (9, "mild"), (14, "moderate"), (19, "moderately_severe"), (27, "severe")],
    "gad7": [(4, "minimal"), (9, "mild"), (14, "moderate"), (21, "severe")],
}


def _severity(score: float, scale: str) -> str:
    thresholds = SEVERITY_LABELS[scale]
    for threshold, label in thresholds:
        if score <= threshold:
            return label
    return thresholds[-1][1]


class AssessmentScore(Base):
    """Cumulative assessment scores per user — updated rolling average per turn."""
    __tablename__ = "assessment_scores"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    phq9_score: Mapped[float] = mapped_column(Float, default=0.0)
    gad7_score: Mapped[float] = mapped_column(Float, default=0.0)
    phq9_items: Mapped[str] = mapped_column(Text, default="{}")   # JSON {item: rolling_score}
    gad7_items: Mapped[str] = mapped_column(Text, default="{}")   # JSON {item: rolling_score}
    turn_count: Mapped[int] = mapped_column(Integer, default=0)   # total turns assessed
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AssessmentHistory(Base):
    """Per-session snapshot of assessment scores for trajectory visualization."""
    __tablename__ = "assessment_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, index=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    phq9_score: Mapped[float] = mapped_column(Float, default=0.0)
    gad7_score: Mapped[float] = mapped_column(Float, default=0.0)
    phq9_severity: Mapped[str] = mapped_column(String, default="minimal")
    gad7_severity: Mapped[str] = mapped_column(String, default="minimal")
    signals_raw: Mapped[str] = mapped_column(Text, default="{}")   # JSON from LLM extraction
    source: Mapped[str] = mapped_column(String, default="chat")    # "chat" | "journal"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AssessmentService:
    def __init__(self):
        self.engine = _engine

    async def update_from_signals(
        self,
        user_id: str,
        session_id: str,
        signals: Dict,
        source: str = "chat",
    ) -> Dict:
        """
        Apply extracted PHQ-9 / GAD-7 item signals to the rolling score.

        signals: {
            "phq9": {"anhedonia": 1, "depressed_mood": 2, ...},
            "gad7": {"nervous": 1, ...}
        }
        Each item score is 0-3 (None = not observed this turn).

        Uses exponential moving average: new = alpha * latest + (1-alpha) * prev
        Alpha decreases as turn_count grows → early turns have more influence
        per-turn, but long-term stability is preserved.
        """
        if not signals:
            return {}

        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(AssessmentScore).where(AssessmentScore.user_id == user_id)
            )
            record = result.scalar_one_or_none()
            if not record:
                record = AssessmentScore(user_id=user_id)
                session.add(record)

            turn_count = record.turn_count + 1
            # EMA alpha: starts high for new users, decays toward floor for long-term users
            from app.config import settings as _s
            alpha = max(_s.assessment_ema_alpha_floor, _s.assessment_ema_alpha_start - (turn_count * 0.01))

            phq9_items = json.loads(record.phq9_items or "{}")
            gad7_items = json.loads(record.gad7_items or "{}")

            # Update PHQ-9 item scores
            new_phq9 = signals.get("phq9", {})
            for item in PHQ9_ITEMS:
                if item in new_phq9 and new_phq9[item] is not None:
                    prev = phq9_items.get(item, 0.0)
                    phq9_items[item] = round(alpha * float(new_phq9[item]) + (1 - alpha) * prev, 3)

            # Update GAD-7 item scores
            new_gad7 = signals.get("gad7", {})
            for item in GAD7_ITEMS:
                if item in new_gad7 and new_gad7[item] is not None:
                    prev = gad7_items.get(item, 0.0)
                    gad7_items[item] = round(alpha * float(new_gad7[item]) + (1 - alpha) * prev, 3)

            # Aggregate totals
            phq9_total = sum(phq9_items.values())
            gad7_total = sum(gad7_items.values())

            record.phq9_items = json.dumps(phq9_items)
            record.gad7_items = json.dumps(gad7_items)
            record.phq9_score = round(phq9_total, 2)
            record.gad7_score = round(gad7_total, 2)
            record.turn_count = turn_count
            record.updated_at = datetime.utcnow()

            await session.commit()

            snapshot = AssessmentHistory(
                user_id=user_id,
                session_id=session_id,
                phq9_score=record.phq9_score,
                gad7_score=record.gad7_score,
                phq9_severity=_severity(record.phq9_score, "phq9"),
                gad7_severity=_severity(record.gad7_score, "gad7"),
                signals_raw=json.dumps(signals),
                source=source,
            )
            session.add(snapshot)
            await session.commit()

            return {
                "phq9_score": record.phq9_score,
                "phq9_severity": _severity(record.phq9_score, "phq9"),
                "gad7_score": record.gad7_score,
                "gad7_severity": _severity(record.gad7_score, "gad7"),
                "turn_count": turn_count,
            }

    async def get_scores(self, user_id: str) -> Dict:
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(AssessmentScore).where(AssessmentScore.user_id == user_id)
            )
            record = result.scalar_one_or_none()
            if not record:
                return {
                    "phq9_score": 0.0, "phq9_severity": "minimal",
                    "gad7_score": 0.0, "gad7_severity": "minimal",
                    "turn_count": 0,
                }
            return {
                "phq9_score": record.phq9_score,
                "phq9_severity": _severity(record.phq9_score, "phq9"),
                "gad7_score": record.gad7_score,
                "gad7_severity": _severity(record.gad7_score, "gad7"),
                "phq9_items": json.loads(record.phq9_items),
                "gad7_items": json.loads(record.gad7_items),
                "turn_count": record.turn_count,
                "updated_at": record.updated_at.isoformat() if record.updated_at else None,
            }

    async def get_trajectory(self, user_id: str, limit: int = 30) -> List[Dict]:
        """Returns chronological score snapshots for mood arc visualization."""
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(AssessmentHistory)
                .where(AssessmentHistory.user_id == user_id)
                .order_by(AssessmentHistory.created_at.desc())
                .limit(limit)
            )
            rows = result.scalars().all()
            return [
                {
                    "session_id": r.session_id,
                    "phq9_score": r.phq9_score,
                    "phq9_severity": r.phq9_severity,
                    "gad7_score": r.gad7_score,
                    "gad7_severity": r.gad7_severity,
                    "source": r.source,
                    "created_at": r.created_at.isoformat(),
                }
                for r in reversed(rows)
            ]

    def format_for_prompt(self, scores: Dict) -> str:
        """Returns a clinical context string injected into companion prompt when severity > minimal."""
        phq9_sev = scores.get("phq9_severity", "minimal")
        gad7_sev = scores.get("gad7_severity", "minimal")
        if phq9_sev == "minimal" and gad7_sev == "minimal":
            return ""
        lines = ["[Background assessment signals — use as context, not diagnosis]"]
        if phq9_sev != "minimal":
            lines.append(f"Depression signals (PHQ-9): {phq9_sev} ({scores.get('phq9_score', 0):.1f}/27)")
        if gad7_sev != "minimal":
            lines.append(f"Anxiety signals (GAD-7): {gad7_sev} ({scores.get('gad7_score', 0):.1f}/21)")
        lines.append("Adjust empathy and support accordingly. Do NOT mention these scores to the user.")
        return "\n".join(lines)
