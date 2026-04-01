import structlog
from app.safety.crisis_detector import CrisisDetector
from app.safety.input_sanitizer import sanitize_input
from app.safety.pii_scrubber import scrub_pii
from app.safety.semantic_safety import SemanticSafety

log = structlog.get_logger()
crisis_detector = CrisisDetector()
semantic_safety = SemanticSafety()

CRISIS_RESPONSE = """Main samajh sakta/sakti hoon ke tum abhi bahut mushkil waqt se guzar rahe ho.

Abhi please in helplines pe call karo:
📞 iCall: 9152987821
📞 Vandrevala Foundation: 1860-2662-345
📞 AASRA: 9820466627

Tum akele nahi ho. 💙"""


async def safety_gate_node(state):
    message = state["message"]

    # Step 1: Input sanitization (injection protection)
    sanitized = sanitize_input(message)

    # Step 2: PII scrubbing
    sanitized = scrub_pii(sanitized)

    # Step 3: Deterministic keyword check
    if crisis_detector.is_hard_crisis(sanitized):
        log.warning("crisis_detected", user_id=state["user_id"], method="keyword")
        return {**state, "is_crisis": True, "crisis_response": CRISIS_RESPONSE, "sanitized_message": sanitized}

    # Step 4: Semantic embedding check
    if await semantic_safety.is_unsafe(sanitized):
        log.warning("crisis_detected", user_id=state["user_id"], method="semantic")
        return {**state, "is_crisis": True, "crisis_response": CRISIS_RESPONSE, "sanitized_message": sanitized}

    return {**state, "is_crisis": False, "crisis_response": None, "sanitized_message": sanitized}
