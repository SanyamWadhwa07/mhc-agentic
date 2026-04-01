import re

INTERNAL_PATTERNS = [
    r'<tool_call>.*?</tool_call>',
    r'<observation>.*?</observation>',
    r'<thought>.*?</thought>',
    r'\[SYSTEM\].*?\[/SYSTEM\]',
    r'GROQ_API_KEY\s*=\s*\S+',
]

COMPILED = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in INTERNAL_PATTERNS]


def scrub_output(text: str) -> str:
    for pattern in COMPILED:
        text = pattern.sub('', text)
    return text.strip()
