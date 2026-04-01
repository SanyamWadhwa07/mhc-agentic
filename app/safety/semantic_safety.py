import numpy as np
from app.config import settings

try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False

CRISIS_ANCHOR_PHRASES = [
    "I want to kill myself",
    "I want to end my life",
    "I don't want to live anymore",
    "everything would be better without me",
    "I am a burden to everyone",
    "I want to disappear permanently",
    "I have no reason to live",
    "marna chahta hoon",
    "jeena nahi chahta",
    "khatam kar loon apne aap ko",
    "sab mere bina theek rahenge",
    "bas sab khatam ho jaye",
]


class SemanticSafety:
    def __init__(self):
        self._model = None
        self._anchor_embeddings = None

    def _load(self):
        if self._model is None:
            if not _ST_AVAILABLE:
                return
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._anchor_embeddings = self._model.encode(CRISIS_ANCHOR_PHRASES, normalize_embeddings=True)

    async def is_unsafe(self, message: str) -> bool:
        if not _ST_AVAILABLE:
            # Fallback: semantic check unavailable, rely on keyword check only
            return False
        self._load()
        if self._model is None:
            return False
        msg_embedding = self._model.encode([message], normalize_embeddings=True)
        similarities = np.dot(self._anchor_embeddings, msg_embedding.T).flatten()
        max_sim = float(np.max(similarities))
        return max_sim >= settings.semantic_safety_threshold
