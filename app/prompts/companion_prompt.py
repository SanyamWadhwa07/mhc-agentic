"""
Companion prompt for Mahi — kept intentionally short.

A capable 70B model doesn't need 200 lines of instructions.
Over-specification confuses the model and produces scripted, unnatural responses.
We only encode what the model cannot infer: persona identity, output schema, risk thresholds.

All routing thresholds and signal lists are read from config — nothing hardcoded here.
"""
from typing import List, Dict
from app.config import settings


_SYSTEM = """You are Mahi — a close friend and emotional companion for Indian Gen Z.

You text like a real friend: warm, calm, natural. Match whatever language the user uses — Hindi, English, or Hinglish. Don't force a style.

If asked whether you're an AI, say "main bas main hoon" and move on.

The only rules worth stating explicitly:
- Never project emotions the user didn't express. If they just say "hi", just say hi back.
- Don't ask a question every single turn. Sometimes just being present is enough.
- When someone shares pain, stay in their feeling — don't rush to advice or solutions.
- Keep responses short: 1-3 sentences. Vary your phrasing across turns.

Return ONLY valid JSON — no text before or after:
{
  "response": "<your reply>",
  "emotions": ["<emotion if clearly expressed, else empty>"],
  "risk_level": "low|medium|high",
  "clinical_flags": [],
  "referral_needed": false
}

risk_level:
- low  — everyday stress, confusion, neutral messages, greetings
- medium — hopelessness, isolation, repeated distress signals
- high — self-harm mentions, suicidal ideation, "main nahi hota toh..."

When risk_level is medium or high, set referral_needed to true."""


def _is_pure_greeting(message: str) -> bool:
    """Heuristic — no LLM needed. Configurable via settings.greeting_tokens."""
    cleaned = message.strip().lower().rstrip("!.,?").strip()
    tokens_set = set(settings.greeting_tokens)
    if cleaned in tokens_set:
        return True
    parts = cleaned.split()
    return len(parts) <= 2 and parts[0] in tokens_set


def _resolve_mode(emotional_intensity: float, force_empathy: bool, message: str) -> str:
    if _is_pure_greeting(message):
        return "greeting"
    if force_empathy or emotional_intensity > settings.emotional_intensity_threshold:
        return "emotional"
    lower = message.lower()
    if any(signal in lower for signal in settings.action_signals):
        return "action"
    return "neutral"


def _resolve_mode_with_rl(
    emotional_intensity: float,
    force_empathy: bool,
    message: str,
    rl_preferences: dict,
) -> str:
    base_mode = _resolve_mode(emotional_intensity, force_empathy, message)
    if base_mode == "greeting":
        return "greeting"  # never RL-override greetings

    preferred = rl_preferences.get("preferred_mode")
    total_feedback = rl_preferences.get("total_feedback", 0)
    high_emotion_pref = rl_preferences.get("high_emotion_preferred", False)
    mode_scores = rl_preferences.get("mode_scores", {})

    if total_feedback < settings.rl_min_feedback_turns or not preferred:
        return base_mode

    # Upgrade neutral → emotional if user clearly prefers it
    if base_mode == "neutral" and preferred == "emotional" and high_emotion_pref:
        return "emotional"

    # Downgrade emotional → preferred if low intensity and user doesn't prefer emotional
    if (
        base_mode == "emotional"
        and preferred in ("action", "neutral")
        and not high_emotion_pref
        and emotional_intensity < settings.rl_emotion_override_threshold
    ):
        return preferred

    # Use mode_scores margin: only switch if preferred mode is clearly better
    if preferred and preferred != base_mode:
        preferred_score = mode_scores.get(preferred, 0.5)
        current_score = mode_scores.get(base_mode, 0.5)
        if preferred_score - current_score > settings.high_emotion_preference_margin:
            return preferred

    return base_mode


def build_companion_prompt(
    message: str,
    history: List[Dict],
    summary: str = "",
    emotional_intensity: float = 0.0,
    force_empathy: bool = False,
    user_profile: str = "",
    journal_context: str = "",
    assessment_context: str = "",
    rl_preferences: dict = None,
) -> tuple:
    mode = _resolve_mode_with_rl(
        emotional_intensity, force_empathy, message, rl_preferences or {}
    )

    messages = [{"role": "system", "content": _SYSTEM}]

    # Greetings: skip all context injection — keep it clean and natural
    if mode != "greeting":
        if user_profile:
            messages.append({"role": "system", "content": f"[Context about this person]\n{user_profile}"})
        if assessment_context:
            messages.append({"role": "system", "content": assessment_context})
        if journal_context:
            messages.append({"role": "system", "content": journal_context})
        if summary:
            messages.append({"role": "system", "content": f"[Prior context]\n{summary}"})

    for turn in history:
        if "message" in turn:
            messages.append({"role": "user", "content": turn["message"]})
        if "response" in turn:
            messages.append({"role": "assistant", "content": turn["response"]})

    messages.append({"role": "user", "content": message})
    return messages, mode
