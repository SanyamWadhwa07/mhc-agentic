import re

INJECTION_PATTERNS = [
    r'ignore\s+previous\s+instructions?',
    r'forget\s+everything',
    r'you\s+are\s+now\s+(?:a\s+)?(?:different|new|evil)',
    r'disregard\s+(?:all\s+)?(?:previous|prior)',
    r'system\s*:\s*',
    r'<\s*system\s*>',
    r'\[INST\]',
    r'###\s*instruction',
]

COMPILED = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def sanitize_input(text: str) -> str:
    for pattern in COMPILED:
        text = pattern.sub('[removed]', text)
    return text.strip()
