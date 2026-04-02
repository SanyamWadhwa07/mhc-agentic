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
    user_profile = state.get("user_profile", "")

    prompt = build_companion_prompt(message, history, summary, emotional_intensity, user_profile=user_profile)

    try:
        import json
        selected_model = state.get("model_used", "llama-3.3-70b-versatile")
        result, actual_model = await llm.call(
            model=selected_model,
            messages=prompt,
            response_format={"type": "json_object"}
        )

        data = json.loads(result)

        risk_level = data.get("risk_level", "low")
        referral_needed = data.get("referral_needed", False)
        if risk_level in ["medium", "high"]:
            referral_needed = True  # deterministic — never trust LLM on this

        return {
            **state,
            "model_used": actual_model,
            "response": data.get("response", ""),
            "emotions": data.get("emotions", []),
            "risk_level": risk_level,
            "clinical_flags": data.get("clinical_flags", []),
            "referral_needed": referral_needed,
        }
    except Exception as e:
        log.error("direct_responder_error", error=str(e))
        return {**state, "response": "Yaar, kuch issue aa gaya. Thodi der mein try karo. 💙"}
