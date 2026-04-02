import json
import re
from pathlib import Path
from app.config import settings

NEGATION_WORDS = [
    "nahi karunga",
    "nahi karungi",
    "nahi karugi",
    "nahi hoon",
    "nahin",
    "nahi",
    "not",
    "never",
    "won't",
    "wont",
    "no",
    "don't",
    "dont",
]


class CrisisDetector:
    def __init__(self):
        kw_path = Path(settings.crisis_keywords_path)
        if kw_path.exists():
            with open(kw_path) as f:
                self.keywords = json.load(f)
        else:
            self.keywords = {"hard_crisis": [], "soft_crisis": [], "contextual": [], "indian_context": []}

    def _normalize(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text.lower().strip())

    def _matches(self, text: str, keyword: str) -> bool:
        normalized_text = self._normalize(text)
        normalized_kw = self._normalize(keyword)
        # Always use word boundaries — works for both single words and phrases
        # \b at start and end ensures "marna chahta hoon" won't match inside "kamarna chahta hoon"
        pattern = r'(?<!\w)' + re.escape(normalized_kw) + r'(?!\w)'
        return bool(re.search(pattern, normalized_text))

    def _is_negated(self, text: str, keyword: str) -> bool:
        """
        Returns True if the keyword match in text is preceded by a negation word
        within 5 words before the matched keyword position.
        """
        normalized_text = self._normalize(text)
        normalized_kw = self._normalize(keyword)
        pattern = r'(?<!\w)' + re.escape(normalized_kw) + r'(?!\w)'
        match = re.search(pattern, normalized_text)
        if not match:
            return False

        # Extract the 5 words immediately before the match position
        text_before_match = normalized_text[:match.start()]
        preceding_words = text_before_match.split()
        window = ' '.join(preceding_words[-5:]) if len(preceding_words) >= 5 else ' '.join(preceding_words)

        for negation in NEGATION_WORDS:
            # Check if the negation word/phrase appears in the 5-word window before the keyword
            neg_pattern = r'(?<!\w)' + re.escape(negation) + r'(?!\w)'
            if re.search(neg_pattern, window):
                return True
        return False

    def is_hard_crisis(self, message: str) -> bool:
        for kw in self.keywords.get("hard_crisis", []):
            if self._matches(message, kw) and not self._is_negated(message, kw):
                return True
        return False

    def is_soft_crisis(self, message: str) -> bool:
        # Soft crisis: err on the side of caution — negation does NOT suppress the signal
        return any(self._matches(message, kw) for kw in self.keywords.get("soft_crisis", []))

    def get_risk_signals(self, message: str) -> dict:
        return {
            "hard": self.is_hard_crisis(message),
            "soft": self.is_soft_crisis(message),
            "contextual": any(self._matches(message, kw) for kw in self.keywords.get("contextual", [])),
            "indian_context": any(self._matches(message, kw) for kw in self.keywords.get("indian_context", [])),
        }
