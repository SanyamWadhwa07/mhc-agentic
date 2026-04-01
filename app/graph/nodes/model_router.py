from app.config import settings


async def model_router_node(state):
    risk_level = state.get("risk_level", "low")
    emotional_intensity = state.get("emotional_intensity", 0.0)
    rag_confidence = state.get("rag_confidence", 1.0)
    react_steps = state.get("react_steps", 0)

    use_120b = (
        risk_level in ["medium", "high"] or
        emotional_intensity > settings.emotional_intensity_threshold or
        rag_confidence < settings.rag_confidence_threshold or
        react_steps >= 3
    )

    model = settings.quality_response_model if use_120b else settings.groq_quality_model
    return {**state, "model_used": model, "selected_model": model}
