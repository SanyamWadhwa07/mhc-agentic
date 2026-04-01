from app.safety.crisis_detector import CrisisDetector

detector = CrisisDetector()

RISK_WEIGHTS = {
    "hard": 1.0,
    "soft": 0.6,
    "contextual": 0.3,
    "indian_context": 0.2,
}


class RiskEvaluator:
    async def run(self, conversation: list) -> dict:
        full_text = " ".join(
            turn.get("message", "") for turn in conversation
            if isinstance(turn, dict)
        )

        signals = detector.get_risk_signals(full_text)
        score = sum(RISK_WEIGHTS[k] * v for k, v in signals.items())

        if score >= 0.8 or signals["hard"]:
            risk_level = "high"
        elif score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {"risk_level": risk_level, "score": round(score, 2), "signals": signals}
