import re

OVERCLINICAL_PATTERNS = [
    (r'\bthe patient\b', 'you', re.IGNORECASE),
    (r'\bthe subject\b', 'you', re.IGNORECASE),
    (r'\bclinical presentation\b', 'how you feel', re.IGNORECASE),
    (r'\bsymptomatology\b', 'feelings', re.IGNORECASE),
    (r'\bpathological\b', 'difficult', re.IGNORECASE),
    (r'\bprecipitating factors\b', 'what triggered this', re.IGNORECASE),
]


def strip_overclinical_language(text: str) -> str:
    for pattern, replacement, flags in OVERCLINICAL_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=flags)
    return text


def enforce_hinglish_style(text: str) -> str:
    # Ensure response doesn't start with "I" in a robotic way
    text = text.strip()
    if text.startswith("I am an AI") or text.startswith("As an AI"):
        text = "Main tumhare saath hoon. " + text.split(".", 1)[-1].strip()
    return text


async def output_normalizer_node(state):
    response = state.get("response", "")

    response = strip_overclinical_language(response)
    response = enforce_hinglish_style(response)
    response = response.strip()

    return {**state, "response": response}
