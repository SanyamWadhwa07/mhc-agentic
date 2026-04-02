"""
Journal API endpoints.

POST /journal                  — create a new journal entry (triggers AI reflection)
GET  /journal/{user_id}        — list entries (paginated)
GET  /journal/{user_id}/context — get recent entries formatted for prompt injection
"""

import json
import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from app.services.journal_service import JournalService
from app.services.assessment_service import AssessmentService
from app.services.profile_service import ProfileService
from app.services.session_service import SessionService

log = structlog.get_logger()
router = APIRouter(prefix="/journal", tags=["journal"])

journal_svc = JournalService()
assessment_svc = AssessmentService()


class JournalCreateRequest(BaseModel):
    user_id: str
    content: str = Field(min_length=1, max_length=10000)
    mood_tags: Optional[List[str]] = None
    is_private: bool = False


class JournalCreateResponse(BaseModel):
    id: int
    user_id: str
    content: str
    mood_tags: List[str]
    ai_reflection: Optional[str]
    emotional_intensity: float
    created_at: str


@router.post("", response_model=JournalCreateResponse)
async def create_journal_entry(request: JournalCreateRequest):
    """
    Create a journal entry. Triggers:
    1. AI reflection generation (Mahi responds to the entry)
    2. PHQ-9/GAD-7 signal extraction (updates background assessment)
    """
    try:
        from app.config import settings
        from app.services.llm_service import LLMService
        from app.prompts.journal_prompt import build_journal_reflection_prompt
        from app.prompts.assessment_prompt import build_assessment_prompt
        from app.graph.nodes.emotional_scorer import _score_text  # reuse scorer

        llm = LLMService()

        # Load user profile for richer reflection
        svc = SessionService()
        profile_svc = ProfileService(svc.engine)
        user_profile = await profile_svc.format_for_prompt(request.user_id)

        # Load prior entry snippet for continuity
        prior_entries = await journal_svc.get_entries(request.user_id, limit=1, offset=1)
        prior_snippet = prior_entries[0]["content"][:150] if prior_entries else ""

        # 1. Generate AI reflection
        reflection_prompt = build_journal_reflection_prompt(
            entry_content=request.content,
            mood_tags=request.mood_tags,
            user_profile=user_profile,
            prior_entry_snippet=prior_snippet,
        )
        reflection_raw, _ = await llm.call(
            model=settings.groq_quality_model,
            messages=reflection_prompt,
            response_format={"type": "json_object"},
        )
        reflection_data = json.loads(reflection_raw)
        ai_reflection = reflection_data.get("reflection", "")
        inferred_tags = reflection_data.get("mood_tags", [])
        emotional_intensity = float(reflection_data.get("emotional_intensity", 0.0))

        merged_tags = list(set((request.mood_tags or []) + inferred_tags))

        # 2. Extract assessment signals (best-effort, non-blocking)
        import asyncio

        async def _assess():
            try:
                assess_prompt = build_assessment_prompt(request.content, context="journal")
                result, _ = await llm.call(
                    model=settings.groq_fast_model,
                    messages=assess_prompt,
                    response_format={"type": "json_object"},
                )
                signals = json.loads(result)
                phq9_vals = [v for v in signals.get("phq9", {}).values() if v is not None]
                gad7_vals = [v for v in signals.get("gad7", {}).values() if v is not None]
                if phq9_vals or gad7_vals:
                    await assessment_svc.update_from_signals(
                        user_id=request.user_id,
                        session_id="journal",
                        signals=signals,
                        source="journal",
                    )
            except Exception as e:
                log.error("journal_assessment_failed", error=str(e))

        asyncio.create_task(_assess())

        # 3. Save entry
        entry = await journal_svc.create_entry(
            user_id=request.user_id,
            content=request.content,
            mood_tags=merged_tags,
            ai_reflection=ai_reflection,
            emotional_intensity=emotional_intensity,
            is_private=request.is_private,
        )

        return JournalCreateResponse(**{k: entry[k] for k in JournalCreateResponse.model_fields})

    except Exception as e:
        log.error("journal_create_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create journal entry")


@router.get("/{user_id}")
async def list_journal_entries(
    user_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    entries = await journal_svc.get_entries(user_id, limit=limit, offset=offset)
    return {"user_id": user_id, "entries": entries, "count": len(entries)}


@router.get("/{user_id}/context")
async def get_journal_context(user_id: str, n: int = Query(default=3, ge=1, le=10)):
    """Returns recent non-private entries formatted for companion prompt injection."""
    context = await journal_svc.get_recent_context(user_id, n=n)
    return {"user_id": user_id, "context": context}
