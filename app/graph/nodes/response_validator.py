import structlog
from app.config import settings
from app.services.llm_service import LLMService
from app.prompts.companion_prompt import build_companion_prompt

log = structlog.get_logger()
llm = LLMService()

EMPATHY_MARKERS = [
    "samajh", "feel", "lagta", "dard", "mushkil", "theek", "sath",
    "akele nahi", "hun main", "bataao", "sunna", "💙", "🌿", "❤"
]


def has_empathy_marker(response: str) -> bool:
    lower = response.lower()
    return any(marker in lower for marker in EMPATHY_MARKERS)


async def response_validator_node(state):
    response = state.get("response", "")

    needs_regen = False

    if len(response) < settings.response_min_length:
        log.warning("response_too_short", length=len(response))
        needs_regen = True

    if not has_empathy_marker(response):
        log.warning("response_missing_empathy")
        needs_regen = True

    if needs_regen:
        try:
            message = state["sanitized_message"]
            history = state.get("session_history", [])[-5:]
            summary = state.get("session_summary", "")
            emotional_intensity = state.get("emotional_intensity", 0.0)

            prompt = build_companion_prompt(message, history, summary, emotional_intensity, force_empathy=True)
            import json
            raw, _ = await llm.call(
                model=state.get("model_used", "llama-3.3-70b-versatile"),
                messages=prompt,
                response_format={"type": "json_object"}
            )
            data = json.loads(raw)
            validated_response = data.get("response", response)

            if len(validated_response) >= settings.response_min_length:
                return {**state, "response": validated_response}
        except Exception as e:
            log.error("response_validator_regen_failed", error=str(e))

    return state
