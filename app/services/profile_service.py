import json
from datetime import datetime
from typing import Optional
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, select
from app.services.session_service import Base
from app.config import settings

log = structlog.get_logger()


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    age_range: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    occupation: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    key_stressors: Mapped[str] = mapped_column(Text, default="[]")
    people_mentioned: Mapped[str] = mapped_column(Text, default="[]")
    ongoing_situations: Mapped[str] = mapped_column(Text, default="[]")
    preferences: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProfileService:
    def __init__(self, engine):
        self.engine = engine

    async def get_profile(self, user_id: str) -> dict:
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            if not profile:
                return {}
            return {
                "name": profile.name,
                "age_range": profile.age_range,
                "occupation": profile.occupation,
                "key_stressors": json.loads(profile.key_stressors),
                "people_mentioned": json.loads(profile.people_mentioned),
                "ongoing_situations": json.loads(profile.ongoing_situations),
                "preferences": json.loads(profile.preferences),
            }

    async def update_profile(self, user_id: str, updates: dict):
        async with AsyncSession(self.engine) as session:
            result = await session.execute(
                select(UserProfile).where(UserProfile.user_id == user_id)
            )
            profile = result.scalar_one_or_none()
            if not profile:
                profile = UserProfile(user_id=user_id)
                session.add(profile)

            if "name" in updates and updates["name"]:
                profile.name = updates["name"]
            if "age_range" in updates and updates["age_range"]:
                profile.age_range = updates["age_range"]
            if "occupation" in updates and updates["occupation"]:
                profile.occupation = updates["occupation"]

            # Merge lists (deduplicate)
            for list_field in ["key_stressors", "people_mentioned", "ongoing_situations"]:
                if list_field in updates and updates[list_field]:
                    current = json.loads(getattr(profile, list_field) or "[]")
                    merged = list(set(current + updates[list_field]))[-10:]  # keep last 10
                    setattr(profile, list_field, json.dumps(merged))

            if "preferences" in updates:
                current_prefs = json.loads(profile.preferences or "{}")
                current_prefs.update(updates["preferences"])
                profile.preferences = json.dumps(current_prefs)

            profile.updated_at = datetime.utcnow()
            await session.commit()

    async def format_for_prompt(self, user_id: str) -> str:
        profile = await self.get_profile(user_id)
        if not profile:
            return ""

        parts = []
        if profile.get("name"):
            parts.append(f"User's name: {profile['name']}")
        if profile.get("occupation"):
            parts.append(f"They are a: {profile['occupation']}")
        if profile.get("key_stressors"):
            parts.append(f"Known stressors: {', '.join(profile['key_stressors'][:3])}")
        if profile.get("people_mentioned"):
            parts.append(f"People in their life: {', '.join(profile['people_mentioned'][:5])}")
        if profile.get("ongoing_situations"):
            parts.append(f"Background context (use ONLY if user explicitly references it — never assume current message is about these): {', '.join(profile['ongoing_situations'][:3])}")

        return "\n".join(parts) if parts else ""
