import numpy as np
from app.config import settings

try:
    from sentence_transformers import SentenceTransformer
    _ST_AVAILABLE = True
except ImportError:
    _ST_AVAILABLE = False

CRISIS_ANCHOR_PHRASES = [
    # --- Original 12 (suicide-focused) ---
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

    # --- Self-harm (non-suicidal) ---
    "want to cut myself",
    "cutting helps me feel better",
    "I hurt myself when things get bad",
    "burn myself",
    "scratch until it bleeds",
    "khud ko hurt karna chahta hoon",
    "apne aap ko cut karna chahta hoon",

    # --- Acute crisis states ---
    "can't breathe and it won't stop",
    "having a panic attack right now",
    "I'm losing control right now",
    "everything is spinning I can't cope",

    # --- Hopelessness variants ---
    "nothing will ever change",
    "what's the point of anything",
    "there is no future for me",
    "I can't see a way out of this",
    "nothing matters anymore",
    "koi fayda nahi kuch bhi karne ka",
    "kya matlab hai jeene ka",
    "koi umeed nahi bachi",

    # --- Passive ideation (not explicit but dangerous) ---
    "I wouldn't mind if I just didn't wake up",
    "wish I could just disappear forever",
    "everyone would be better off without me",
    "I don't deserve to exist",
    "na hota toh acha hota",
    "sab mere bina khush rahenge",
    "meri zaroorat nahi kisi ko",

    # --- Indian-specific crisis phrases ---
    "shaadi ke baad jeena band kar lunga",
    "board exam fail ke baad kya karunga",
    "ghar chod ke chali jaungi",
    "paas nahi hua toh mar jaaunga",
    "rank nahi aya toh kya karun",
    "maa baap ko muh nahi dikha sakta",

    # --- Burden thoughts ---
    "I am such a burden to my family",
    "life would be easier for everyone without me",
    "sabke liye sirf takleef hoon main",
    "ghar mein sirf problem hoon main",

    # --- Social withdrawal + isolation ---
    "nobody cares if I live or die",
    "I have nobody left",
    "completely alone in this world",
    "koi mujhe samajhta hi nahi",
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
