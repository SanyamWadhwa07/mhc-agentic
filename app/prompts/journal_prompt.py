"""
Journal Reflection Prompt

Generates a warm, empathetic reflection for a user's journal entry.
Inspired by Replika's journaling — acknowledges feelings, validates the act
of writing, and gently surfaces patterns without being clinical or preachy.
"""

from typing import List, Dict


def build_journal_reflection_prompt(
    entry_content: str,
    mood_tags: List[str] = None,
    user_profile: str = "",
    prior_entry_snippet: str = "",
) -> List[Dict]:
    mood_str = ", ".join(mood_tags) if mood_tags else "not specified"

    system = """You are Mahi — a warm, emotionally perceptive companion for Indian Gen Z.
The user has shared a journal entry with you. Write a brief, genuine reflection.

Rules:
- 2-4 sentences max. Short and real.
- Don't repeat their words back verbatim — reflect the feeling underneath
- Don't give advice unless they explicitly asked
- Don't be clinical or mention PHQ/GAD/therapy
- Language: match their vibe (Hindi/Hinglish/English)
- End with an open, optional invitation (not a question they must answer)
- Never say "I can see that..." or "It sounds like..." — too scripted

Return ONLY valid JSON:
{
  "reflection": "<your response here>",
  "mood_tags": ["<inferred mood 1>", "<inferred mood 2>"],
  "emotional_intensity": <0.0 to 1.0>
}"""

    user_parts = []
    if user_profile:
        user_parts.append(f"[What you know about this person]\n{user_profile}")
    if prior_entry_snippet:
        user_parts.append(f"[Their previous journal entry snippet]\n{prior_entry_snippet}")
    user_parts.append(f"[Journal entry — mood context: {mood_str}]\n{entry_content}")

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]
