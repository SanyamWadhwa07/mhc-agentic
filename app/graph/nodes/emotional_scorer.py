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

    # Component 2: Keyword intensity (0-1)
    keyword_hits = sum(1 for kw in HIGH_INTENSITY_KEYWORDS if kw in lower)
    keyword_score = min(keyword_hits / 3.0, 1.0)

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

    # Weighted average
    emotional_intensity = (
        sentiment_score * 0.35 +
        keyword_score * 0.35 +
        punct_score * 0.15 +
        repetition_score * 0.15
    )

    return {**state, "emotional_intensity": round(emotional_intensity, 3)}
