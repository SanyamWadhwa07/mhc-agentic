import re
from app.config import settings

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
    parts = re.split(r'[,;।\n]|\baur\b|\band\b|\bor\b', message, flags=re.IGNORECASE)
    return len([p for p in parts if len(p.strip()) > 10])


def message_length_factor(message: str) -> float:
    words = len(message.split())
    if words > 50: return 1.0
    if words > 30: return 0.5
    return 0.0


def _is_greeting(message: str) -> bool:
    cleaned = message.strip().lower().rstrip("!.,?").strip()
    tokens_set = set(settings.greeting_tokens)
    if cleaned in tokens_set:
        return True
    parts = cleaned.split()
    return len(parts) <= 2 and parts[0] in tokens_set


def _risk_has_decayed(session_history: list) -> bool:
    """
    Returns True if the last N turns were all low-risk, meaning a prior
    medium/high risk flag has effectively decayed and routing can reset.
    """
    n = settings.risk_decay_turns
    recent = session_history[-n:]
    return len(recent) >= n and all(
        t.get("risk_level", "low") == "low" for t in recent
    )


async def path_classifier_node(state):
    message = state["sanitized_message"]
    session_history = state.get("session_history", [])
    last_risk = state.get("last_risk_level", "low")
    emotional_intensity = state.get("emotional_intensity", 0.0)

    # Pure greetings are ALWAYS simple — never waste ReAct on "hi"
    if _is_greeting(message):
        return {**state, "path": "simple", "complexity_score": 0.0}

    # Risk decay: if prior risk was elevated but last N turns were all low, reset
    if last_risk in ["medium", "high"]:
        if _risk_has_decayed(session_history):
            last_risk = "low"  # decayed — treat as normal turn
        else:
            return {**state, "path": "complex", "complexity_score": 5.0}

    if has_clinical_keywords(message):
        return {**state, "path": "complex", "complexity_score": 4.0}

    tc = topic_count(message)
    if tc >= 2:
        return {**state, "path": "complex", "complexity_score": 3.5}

    # Numeric score — exchange_count no longer a hard gate
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
