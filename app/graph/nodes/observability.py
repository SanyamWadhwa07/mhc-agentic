import time
import structlog

log = structlog.get_logger()


async def observability_node(state):
    start_time = state.get("start_time", time.time())

    metrics = {
        "latency_ms": round((time.time() - start_time) * 1000),
        "path": state.get("path", "unknown"),
        "model_used": state.get("model_used", "unknown"),
        "react_steps_used": state.get("react_steps", 0),
        "rag_confidence": state.get("rag_confidence", 1.0),
        "emotional_intensity": state.get("emotional_intensity", 0.0),
        "risk_level": state.get("risk_level", "low"),
        "safety_triggered": state.get("is_crisis", False),
        "rate_limited": state.get("is_rate_limited", False),
        "referral_needed": state.get("referral_needed", False),
        "selected_model": state.get("selected_model", state.get("model_used", "unknown")),
        "fallback_triggered": state.get("fallback_triggered", False),
    }

    log.info("request_complete", **metrics)
    return {**state, "metrics": metrics}
