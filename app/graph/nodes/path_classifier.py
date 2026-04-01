import re

CLINICAL_KEYWORDS = [
    # PHQ-9 signals
    "depressed", "depression", "hopeless", "worthless", "suicidal",
    "can't sleep", "neend nahi", "no interest", "kuch acha nahi lagta",
    "thaka hua", "exhausted", "concentrate nahi", "slow hona",
    # GAD-7 signals
    "anxiety", "anxious", "worry", "ghabrahat", "tension", "nervous",
    "panic", "heartbeat", "palpitation",
    # Indian context
    "board exam", "jee", "neet", "shaadi", "divorce", "domestic",
    "pagal", "mental", "psychiatrist", "therapy chahiye"
]


def has_clinical_keywords(message: str) -> bool:
    lower = message.lower()
    return any(kw in lower for kw in CLINICAL_KEYWORDS)


def topic_count(message: str) -> int:
    # Rough heuristic: count sentence fragments
    parts = re.split(r'[,;।\n]|\baur\b|\band\b|\bor\b', message, flags=re.IGNORECASE)
    return len([p for p in parts if len(p.strip()) > 10])


def message_length_factor(message: str) -> float:
    words = len(message.split())
    if words > 50: return 1.0
    if words > 30: return 0.5
    return 0.0


async def path_classifier_node(state):
    message = state["sanitized_message"]
    session_history = state.get("session_history", [])
    last_risk = state.get("last_risk_level", "low")
    emotional_intensity = state.get("emotional_intensity", 0.0)

    # Hard rules → complex immediately
    if last_risk in ["medium", "high"]:
        return {**state, "path": "complex", "complexity_score": 5.0}

    if has_clinical_keywords(message):
        return {**state, "path": "complex", "complexity_score": 4.0}

    tc = topic_count(message)
    if tc >= 2:
        return {**state, "path": "complex", "complexity_score": 3.5}

    exchange_count = len(session_history)
    if exchange_count >= 3:
        return {**state, "path": "complex", "complexity_score": 3.0}

    # Numeric score
    clinical_signal = 1 if has_clinical_keywords(message) else 0
    prior_risk = 1 if last_risk in ["medium", "high"] else 0

    complexity_score = (
        clinical_signal * 2 +
        prior_risk * 2 +
        emotional_intensity +
        min(tc, 3) +
        message_length_factor(message)
    )

    path = "complex" if complexity_score >= 3 else "simple"
    return {**state, "path": path, "complexity_score": round(complexity_score, 2)}
