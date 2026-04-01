import asyncio
import structlog
from app.config import settings

log = structlog.get_logger()


async def _write_to_db(state: dict):
    try:
        from app.services.session_service import SessionService
        svc = SessionService()
        await svc.save_turn(
            user_id=state["user_id"],
            session_id=state["session_id"],
            message=state["message"],
            response=state["response"],
            emotions=state.get("emotions", []),
            risk_level=state.get("risk_level", "low"),
            clinical_flags=state.get("clinical_flags", []),
            referral_needed=state.get("referral_needed", False),
            metrics=state.get("metrics", {}),
        )
    except Exception as e:
        log.error("memory_write_failed", error=str(e))


async def _maybe_summarize(state: dict):
    from app.services.session_service import SessionService
    svc = SessionService()
    try:
        count = await svc.get_exchange_count(state["user_id"], state["session_id"])
        if count % settings.memory_summary_interval == 0:
            from app.services.llm_service import LLMService
            from app.prompts.summary_prompt import build_summary_prompt
            llm = LLMService()
            history = await svc.get_recent_history(state["user_id"], state["session_id"], n=10)
            prompt = build_summary_prompt(history)
            summary, _ = await llm.call(model=settings.groq_fast_model, messages=prompt)
            await svc.save_summary(state["user_id"], state["session_id"], summary)
    except Exception as e:
        log.error("summary_failed", error=str(e))


async def memory_update_node(state):
    # Fire and forget — non-blocking
    asyncio.create_task(_write_to_db(state))
    asyncio.create_task(_maybe_summarize(state))
    return state
