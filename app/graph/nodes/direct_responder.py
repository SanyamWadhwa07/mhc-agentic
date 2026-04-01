import structlog
from app.services.llm_service import LLMService
from app.prompts.companion_prompt import build_companion_prompt

log = structlog.get_logger()
llm = LLMService()


async def direct_responder_node(state):
    message = state["sanitized_message"]
    history = state.get("session_history", [])[-5:]
    summary = state.get("session_summary", "")
    emotional_intensity = state.get("emotional_intensity", 0.0)

    prompt = build_companion_prompt(message, history, summary, emotional_intensity)

    try:
        result = await llm.call(
            model=state.get("model_used", "llama-3.3-70b-versatile"),
            messages=prompt,
            response_format={"type": "json_object"}
        )

        import json
        data = json.loads(result)

        return {
            **state,
            "response": data.get("response", ""),
            "emotions": data.get("emotions", []),
            "risk_level": data.get("risk_level", "low"),
            "clinical_flags": data.get("clinical_flags", []),
            "referral_needed": data.get("referral_needed", False)
        }
    except Exception as e:
        log.error("direct_responder_error", error=str(e))
        return {**state, "response": "Yaar, kuch issue aa gaya. Thodi der mein try karo. 💙"}
