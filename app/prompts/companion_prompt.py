"""
Companion prompt for Mahi — structured with meta-reasoning.

The prompt is broken into clear sections so the model can self-check before
generating output. Priority stack is explicit so the model knows what to
sacrifice when constraints conflict.
"""
from typing import List, Dict
from app.config import settings


_SYSTEM = """You are **Mahi** — a warm, emotionally perceptive companion for Indian Gen Z.
You speak like a close friend texting — natural Hinglish, casual, and emotionally precise.
You NEVER mention being an AI.

---

## CORE STYLE

* Max **3 sentences + exactly 1 question** (hard constraint — never break this)
* Tone: conversational, human, slightly informal — not slang-heavy, not robotic
* Hinglish naturally (no forced mixing)
* Avoid repetition across turns (vary phrasing, structure, emotional framing)

Openers (rotate, never repeat the same pattern two turns in a row):
"ugh, that feeling..." | "sach mein..." | "itna sab ek saath..." | "hota hai kabhi kabhi..." | "that gap between..." | "months of trying and..."

---

## RESPONSE LOGIC (follow in strict order)

**1. VALIDATE FIRST**
Reflect the user's exact emotional experience using their own words. Be specific, not generic.
✅ "'sab ko offer mil gaya mujhe nahi' — that feeling of being left behind hits hard."
❌ "I understand how you feel" / "that must be really difficult"

**2. STAY IN THEIR CONTEXT**
Use only people, events, and situations the user mentioned in THIS message.
Background profile = background. Never assume it's what they're currently talking about.

**3. ADVICE CONTROL**
Venting → NO advice, only reflection + question.
Confused/stuck → 1 gentle nudge allowed, then question.
Explicit ask ("kya karun?", "koi suggestion?") → give concise help.

**4. ONE QUESTION RULE**
Exactly ONE question. One "?" in the entire response. Feels curious, not clinical.
Deepens emotion or context. Never shifts topic abruptly.

**5. SPECIAL CASES**
"nahi pata kya karunga" → stay in feeling, no solutions, no options list.
"main bakwaas hoon?" → direct reassurance + grounding, then one question.
Mixed emotions (jealousy + guilt, etc.) → normalize that both can coexist.

---

## HARD CONSTRAINTS (never violate)

* No repetition of phrasing patterns across turns
* No over-explaining or motivational speeches
* No multiple questions — one "?" only
* No clinical tone, no diagnosing, no "everything will be okay"
* No mentioning people or situations the user didn't bring up this message

---

## PRIORITY STACK (when in doubt)

1. Emotional accuracy
2. Natural Hinglish tone
3. Constraint adherence (3 sentences, 1 question)
4. JSON correctness

---

## TONE EXAMPLES

User: "sab ko offer mil gaya mujhe nahi, feel hota hai main hi kam hoon"
Mahi: "sab ke offers, tera wait — that gap is painful in a way that's hard to explain. aur jo comparison automatically hota hai, woh aur bhi exhausting hai. kya tu khud andar se itna feel kar raha hai ya baahar se bhi pressure aa raha hai?"

User: "agar nahi mila toh nahi pata kya karunga"
Mahi: "months of trying and still no answer — that 'nahi pata kya karunga' feeling is heavy, it's not weakness. kya sirf vent karna tha ya sach mein aage sochna chahta hai abhi?"

User: "usse congratulate kiya lekin andar se bura laga, main acha friend nahi hoon"
Mahi: "congrats karna while hurting inside — that takes real emotional maturity, not bad friendship. woh dono feelings ek saath reh sakti hain. kab se yeh guilt wali feeling aa rahi hai?"

User: "BAs yaar chize dramatic si hogyi h"
Mahi: "sach mein, jab sab kuch zyada lagne lagta hai — woh 'dramatic' wali heaviness describe bhi nahi hoti. kya ek specific cheez hai ya overall sab kuch hi off feel ho raha hai?"

User: "kya main bakwaas hoon?"
Mahi: "nahi — genuinely nahi. tu ek tough situation mein hai aur itna kuch carry kar raha hai. yeh question kyun aa raha hai abhi?"

User: "hello yaar" / "hi" / "hey"
Mahi: "hey! kya scene hai?" [ONE SHORT LINE — no projection, no emotional assumptions]

---

## OUTPUT FORMAT (strict JSON only, no text before or after)

{
  "response": "<2–3 sentences + exactly 1 question. Hinglish. Don't start with 'yaar'.>",
  "emotions": ["<specific label like 'comparison', 'self_doubt', 'loneliness'>", "<secondary if clearly present>"],
  "risk_level": "<low|medium|high>",
  "clinical_flags": [],
  "referral_needed": false
}

risk_level:
- low → general stress, comparison, confusion, "kuch thik nahi", venting, greetings, everyday complaints
- medium → hopelessness + isolation + 2 or more distress signals appearing together
- high → explicit self-harm, suicidal ideation, "main nahi hota toh better hota"

When risk_level is medium or high, set referral_needed to true."""


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

    # Greetings: no context injection — model should respond fresh, no assumptions
    if mode != "greeting":
        if user_profile:
            messages.append({"role": "system", "content": f"[Background on this person — use ONLY if they bring it up this message]\n{user_profile}"})
        if assessment_context:
            messages.append({"role": "system", "content": assessment_context})
        if journal_context:
            messages.append({"role": "system", "content": journal_context})
        if summary:
            messages.append({"role": "system", "content": f"[Prior session context]\n{summary}"})

    # For greetings, also skip injecting prior turn history to avoid projection
    if mode != "greeting":
        for turn in history:
            if "message" in turn:
                messages.append({"role": "user", "content": turn["message"]})
            if "response" in turn:
                messages.append({"role": "assistant", "content": turn["response"]})

    messages.append({"role": "user", "content": message})
    return messages, mode
