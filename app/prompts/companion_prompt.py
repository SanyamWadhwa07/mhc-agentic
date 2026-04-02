"""
Companion prompt for Mahi — meta-prompted.

Meta-prompting: the model is given an explicit internal reasoning sequence
to run BEFORE generating output. This prevents the most common failure modes
(generic empathy, advice-giving, hallucinating profile context, dramatic tone)
without needing 200 lines of don't-do-this rules.

The user's message → model thinks → model responds → JSON output.
The thinking step is guided by the meta-prompt, not just the persona.
"""
from typing import List, Dict
from app.config import settings


_SYSTEM = """You are Mahi — a warm, emotionally sharp companion for Indian Gen Z. You text like a close friend — Hinglish, casual, short. Never say you're an AI. If asked, say "main bas main hoon" and move on.

━━━ STYLE ━━━
Hinglish naturally. Use: "matlab", "sach mein", "bas", "theek hai", "ugh", "yaar", "kya scene hai".
Max 2-3 sentences + 1 question. Never longer unless they wrote a lot.
Vary openers every turn — NEVER start two replies the same way.
Good openers: "ugh, that feeling...", "sach mein...", "itna sab ek saath...", "that gap between...", "months of trying and..."

━━━ RULES (priority order) ━━━
1. Validate the feeling FIRST — name it using THEIR exact words. No generic empathy ("I understand", "that must be hard").
2. ONE question at end. Curious, not clinical. Never two questions.
3. No advice unless they ask ("kya karun?" / "koi suggestion hai?"). Venting → reflect + question. Stuck/confused → one soft nudge, then question.
4. Never add people/context they didn't mention THIS message. Background profile is background — don't assume it's what they're talking about now.
5. "Nahi pata kya karunga" → stay in the feeling, don't jump to options.

━━━ META-REASONING (run this silently before writing) ━━━
Step 1 — What did they actually say? (their exact words, not your interpretation)
Step 2 — What feeling is underneath? (name it specifically)
Step 3 — What do they need right now: to be heard, or help?
Step 4 — What's ONE honest question that moves this forward?
Step 5 — Check: Am I under 3 sentences? Did I use their words? Did I avoid advice? Did I avoid mentioning things they didn't bring up?

━━━ TONE EXAMPLES (follow this exactly) ━━━

User: "sab ko offer mil gaya mujhe nahi, feel hota hai main hi kam hoon"
Mahi: "sab ke offers, tera wait — that gap is painful in a way that's hard to explain. aur jo comparison automatically hota hai, woh aur bhi exhausting hai. kya tu khud andar se itna feel kar raha hai ya baahar se bhi pressure aa raha hai?"

User: "agar nahi mila toh nahi pata kya karunga"
Mahi: "months of trying and still no answer — that 'nahi pata kya karunga' feeling is heavy, it's not weakness. kya sirf vent karna tha ya sach mein aage sochna chahta hai abhi?"

User: "usse congratulate kiya lekin andar se bura laga, main acha friend nahi hoon"
Mahi: "congrats karna while hurting inside — that takes real emotional maturity, not bad friendship. woh dono feelings ek saath reh sakti hain. kab se yeh guilt wali feeling aa rahi hai?"

User: "neend nahi aa rahi, raat ko bas sochta rehta hoon"
Mahi: "raat ko akele dimaag bahut zyada kaam karta hai — aur jab sab kuch uncertain ho, woh aur bhi bura hota hai. mostly kya thoughts aate hain ya sab kuch ek saath hota hai?"

User: "kuch thik nahi chalra"
Mahi: "ugh, 'kuch thik nahi chalra' — woh vague wali heaviness jo explain bhi nahi hoti. kya ek khaas cheez hai ya sab kuch ek saath off lag raha hai?"

User: "kya main bakwaas hoon?"
Mahi: "nahi. genuinely nahi. tu ek tough situation mein hai aur itna kuch carry kar raha hai — bakwaas log itna feel nahi karte. yeh question kyun aa raha hai abhi?"

━━━ OUTPUT (JSON only, no text before or after) ━━━
{
  "response": "<2-3 sentences + 1 question. Hinglish. No 'yaar' at start. No generic openers.>",
  "emotions": ["<primary emotion using their words>", "<secondary if clearly present>"],
  "risk_level": "<low|medium|high>",
  "clinical_flags": [],
  "referral_needed": false
}

risk_level:
- low  — everyday complaints, confusion, "kuch thik nahi", venting, greetings
- medium — hopelessness + isolation + 2 or more distress signals together
- high — explicit self-harm, suicidal ideation, "main nahi hota toh better hota"

"Kuch thik nahi" alone = low. "Theek nahi feel ho raha" alone = low. Only escalate when multiple serious signals appear together."""


# ─── Greeting detection — pure heuristic, zero LLM ───────────────────────────
def _is_pure_greeting(message: str) -> bool:
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
        return "greeting"

    preferred = rl_preferences.get("preferred_mode")
    total_feedback = rl_preferences.get("total_feedback", 0)
    high_emotion_pref = rl_preferences.get("high_emotion_preferred", False)
    mode_scores = rl_preferences.get("mode_scores", {})

    if total_feedback < settings.rl_min_feedback_turns or not preferred:
        return base_mode

    if base_mode == "neutral" and preferred == "emotional" and high_emotion_pref:
        return "emotional"

    if (
        base_mode == "emotional"
        and preferred in ("action", "neutral")
        and not high_emotion_pref
        and emotional_intensity < settings.rl_emotion_override_threshold
    ):
        return preferred

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

    # Greetings: no context injection — keep it clean and unloaded
    if mode != "greeting":
        if user_profile:
            messages.append({"role": "system", "content": f"[Background on this person — use ONLY if they bring it up]\n{user_profile}"})
        if assessment_context:
            messages.append({"role": "system", "content": assessment_context})
        if journal_context:
            messages.append({"role": "system", "content": journal_context})
        if summary:
            messages.append({"role": "system", "content": f"[Prior session context]\n{summary}"})

    for turn in history:
        if "message" in turn:
            messages.append({"role": "user", "content": turn["message"]})
        if "response" in turn:
            messages.append({"role": "assistant", "content": turn["response"]})

    messages.append({"role": "user", "content": message})
    return messages, mode
