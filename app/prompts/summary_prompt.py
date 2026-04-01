from typing import List, Dict


def build_summary_prompt(history: List[Dict]) -> List[Dict]:
    history_text = "\n".join([
        f"User: {turn.get('message', '')}\nAssistant: {turn.get('response', '')}"
        for turn in history
    ])

    return [
        {
            "role": "system",
            "content": """Create a concise session summary that preserves:
1. Last known risk_level
2. Any referral flags
3. Active clinical themes (depression, anxiety, relationship issues, etc.)
4. Key personal context (family situation, stressors, life events mentioned)

Format: Plain text, 3-5 sentences max. Be specific about names, situations, and risk signals."""
        },
        {
            "role": "user",
            "content": f"Session history to summarize:\n\n{history_text}"
        }
    ]
