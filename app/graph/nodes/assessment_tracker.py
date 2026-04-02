"""
Assessment Tracker Node

Runs as a fire-and-forget background task after memory_update.
Extracts PHQ-9/GAD-7 signals from the current turn using a fast LLM call,
then updates the rolling assessment scores for the user.

Design: fully non-blocking — never delays the response pipeline.
"""

import asyncio
import json
import structlog
from app.config import settings

log = structlog.get_logger()


async def _extract_and_update(state: dict):
    try:
        message = state.get("sanitized_message", state.get("message", ""))
        user_id = state["user_id"]
        session_id = state["session_id"]

        # Combine user message + any clinical flags for richer signal
        clinical_flags = state.get("clinical_flags", [])
        text = message
        if clinical_flags:
            text += f"\n[Clinical signals detected: {', '.join(clinical_flags)}]"

        # Fast LLM call for signal extraction
        from app.services.llm_service import LLMService
        from app.prompts.assessment_prompt import build_assessment_prompt

        llm = LLMService()
        prompt = build_assessment_prompt(text, context="chat")
        result, _ = await llm.call(
            model=settings.groq_fast_model,
            messages=prompt,
            response_format={"type": "json_object"},
        )
        signals = json.loads(result)

        # Filter: if all items are null, skip DB write
        phq9_vals = [v for v in signals.get("phq9", {}).values() if v is not None]
        gad7_vals = [v for v in signals.get("gad7", {}).values() if v is not None]
        if not phq9_vals and not gad7_vals:
            return  # no signal this turn — skip

        # Update rolling scores
        from app.services.assessment_service import AssessmentService
        svc = AssessmentService()
        scores = await svc.update_from_signals(
            user_id=user_id,
            session_id=session_id,
            signals=signals,
            source="chat",
        )
        log.info(
            "assessment_updated",
            user_id=user_id,
            phq9=scores.get("phq9_score"),
            gad7=scores.get("gad7_score"),
        )

    except Exception as e:
        log.error("assessment_tracker_failed", error=str(e))


def _log_done(task: asyncio.Task):
    if not task.cancelled() and task.exception():
        log.error("assessment_task_exception", error=str(task.exception()))


async def assessment_tracker_node(state: dict) -> dict:
    task = asyncio.create_task(
        _extract_and_update(state),
        name=f"assessment_{state.get('user_id', 'unknown')}",
    )
    task.add_done_callback(_log_done)
    return state
