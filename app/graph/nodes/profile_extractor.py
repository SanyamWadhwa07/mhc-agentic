import json
import structlog
from app.services.llm_service import LLMService
from app.config import settings

log = structlog.get_logger()
llm = LLMService()

_EXTRACT_PROMPT = """Extract structured information about the user from their message. Return JSON only.

Fields to extract (only include if clearly present — do NOT guess):
- name: string or null (if user mentions their name, e.g. "main Priya hoon")
- age_range: string or null ("teens", "20s", "30s", etc.)
- occupation: string or null (student, engineer, etc.)
- key_stressors: list of strings (topics causing stress: "JEE prep", "job search", etc.)
- people_mentioned: list of strings (names/relationships: "mom", "Rohan", "best friend")
- ongoing_situations: list of strings (specific ongoing events: "NEET exam next week", "breakup 2 weeks ago")
- preferences: dict with optional keys:
  - wants_advice: boolean (true only if they explicitly asked "kya karun?" or similar)

Return empty lists/null for fields with no clear signal. Never hallucinate.

User message: {message}

JSON output:"""


async def profile_extractor_node(state):
    message = state.get("sanitized_message", state.get("message", ""))
    user_id = state["user_id"]

    try:
        prompt = [
            {"role": "user", "content": _EXTRACT_PROMPT.format(message=message)}
        ]
        result, _ = await llm.call(
            model=settings.groq_fast_model,
            messages=prompt,
            response_format={"type": "json_object"}
        )
        updates = json.loads(result)

        # Import here to avoid circular deps at module load time
        from app.services.profile_service import ProfileService
        from app.services.session_service import SessionService
        svc = SessionService()
        profile_svc = ProfileService(svc.engine)
        await profile_svc.update_profile(user_id, updates)

        # Load full formatted profile for this turn (injected into companion prompt)
        user_profile = await profile_svc.format_for_prompt(user_id)
        return {**state, "user_profile": user_profile}

    except Exception as e:
        log.error("profile_extractor_error", error=str(e))
        return {**state, "user_profile": state.get("user_profile", "")}
