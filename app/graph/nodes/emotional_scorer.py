import re

try:
    from textblob import TextBlob
    _TEXTBLOB_AVAILABLE = True
except ImportError:
    _TEXTBLOB_AVAILABLE = False

HIGH_INTENSITY_KEYWORDS = [
    "bahut", "bohot", "zyada", "bilkul", "completely", "totally",
    "always", "never", "forever", "destroy", "hate", "hating",
    "worst", "terrible", "horrible", "awful", "unbearable",
    "rone", "rona", "aansu", "dard", "takleef", "dukh", "gham",
    "akela", "tanha", "bekar", "nafrat", "gussa", "pareshan"
]

# Tiered Hinglish/Hindi keyword intensity system
HINGLISH_INTENSITY_KEYWORDS = {
    # tier 3 — high intensity (maps to score 1.0)
    "high": [
        "hopeless", "khatam", "marna", "suicide", "cut myself", "hurt myself",
        "koi fayda nahi", "nahi rehna", "barbad", "toot gaya", "toot gayi",
        "devastated", "can't go on", "end it", "worthless",
    ],
    # tier 2 — medium intensity (maps to score 0.65)
    "medium": [
        "anxious", "scared", "ghabra", "dara", "depressed", "bohot bura",
        "crying", "ro raha", "ro rahi", "panic", "stressed", "bahut tension",
        "overwhelmed", "exhausted", "thak gaya", "thak gayi", "lonely",
        "akela", "akeli", "angry", "gussa", "frustrated",
    ],
    # tier 1 — low intensity (maps to score 0.35)
    "low": [
        "sad", "bura", "udaas", "not good", "theek nahi", "worried", "chinta",
        "nervous", "uncomfortable", "off", "low", "meh", "boring", "bored",
    ],
}

# Phrases that indicate self-referential context (intensifier)
SELF_REFERENTIAL_PHRASES = ["khud ko", "apne aap ko"]

PUNCTUATION_PATTERN = re.compile(r'[!?]{2,}|\.{3,}')
CAPS_PATTERN = re.compile(r'[A-Z]{3,}')


async def emotional_scorer_node(state):
    message = state["sanitized_message"]
    lower = message.lower()
    words = lower.split()

    # Component 1: Sentiment score (0-1)
    try:
        if _TEXTBLOB_AVAILABLE:
            blob = TextBlob(message)
            sentiment_score = abs(blob.sentiment.polarity)  # intensity, not valence
        else:
            sentiment_score = 0.3
    except Exception:
        sentiment_score = 0.3

    # Component 2: Legacy keyword intensity (0-1)
    keyword_hits = sum(1 for kw in HIGH_INTENSITY_KEYWORDS if kw in lower)
    keyword_score = min(keyword_hits / 3.0, 1.0)

    # Component 2b: Tiered Hinglish keyword score
    hinglish_score = 0.0
    if any(kw in lower for kw in HINGLISH_INTENSITY_KEYWORDS["high"]):
        hinglish_score = 1.0
    elif any(kw in lower for kw in HINGLISH_INTENSITY_KEYWORDS["medium"]):
        hinglish_score = 0.65
    elif any(kw in lower for kw in HINGLISH_INTENSITY_KEYWORDS["low"]):
        hinglish_score = 0.35

    # Self-referential intensifier: "khud ko" / "apne aap ko" before a high-tier word
    if hinglish_score > 0 and any(phrase in lower for phrase in SELF_REFERENTIAL_PHRASES):
        hinglish_score = min(hinglish_score * 1.3, 1.0)

    # Blend: take the max of existing keyword_score and hinglish_score
    keyword_score = min(max(keyword_score, hinglish_score), 1.0)

    # Component 3: Punctuation density (0-1)
    punct_hits = len(PUNCTUATION_PATTERN.findall(message))
    caps_hits = len(CAPS_PATTERN.findall(message))
    punct_score = min((punct_hits + caps_hits) / 3.0, 1.0)

    # Component 4: Repetition patterns (0-1)
    word_counts = {}
    for w in words:
        if len(w) > 3:
            word_counts[w] = word_counts.get(w, 0) + 1
    max_repeat = max(word_counts.values()) if word_counts else 1
    repetition_score = min((max_repeat - 1) / 3.0, 1.0)

    # Weighted average — TextBlob score also blended with hinglish_score via max()
    textblob_blended = max(sentiment_score, hinglish_score)
    emotional_intensity = (
        textblob_blended * 0.35 +
        keyword_score * 0.35 +
        punct_score * 0.15 +
        repetition_score * 0.15
    )

    return {**state, "emotional_intensity": round(emotional_intensity, 3)}
