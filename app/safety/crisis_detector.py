import json
import re
from pathlib import Path
from app.config import settings


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

    def is_hard_crisis(self, message: str) -> bool:
        return any(self._matches(message, kw) for kw in self.keywords.get("hard_crisis", []))

    def is_soft_crisis(self, message: str) -> bool:
        return any(self._matches(message, kw) for kw in self.keywords.get("soft_crisis", []))

    def get_risk_signals(self, message: str) -> dict:
        return {
            "hard": self.is_hard_crisis(message),
            "soft": self.is_soft_crisis(message),
            "contextual": any(self._matches(message, kw) for kw in self.keywords.get("contextual", [])),
            "indian_context": any(self._matches(message, kw) for kw in self.keywords.get("indian_context", [])),
        }
