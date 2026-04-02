from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    groq_api_key: str = ""
    groq_fast_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_quality_model: str = "llama-3.3-70b-versatile"
    quality_response_model: str = "openai/gpt-oss-120b"

    # RAG
    chroma_persist_dir: str = "./chroma_db"
    embedding_model: str = "all-MiniLM-L6-v2"
    rag_confidence_threshold: float = 0.6

    # Pipeline
    react_max_steps: int = 4
    memory_summary_interval: int = 10
    rate_limit_per_minute: int = 10

    # Mode routing thresholds
    emotional_intensity_threshold: float = 0.5     # above this → emotional mode
    rl_min_feedback_turns: int = 5                 # min feedback turns before RL bias applies
    rl_emotion_override_threshold: float = 0.6     # don't downgrade emotional mode above this intensity
    high_emotion_preference_margin: float = 0.2    # emotional vs neutral avg margin to prefer emotional
    risk_decay_turns: int = 3                      # consecutive low-risk turns to reset prior medium/high risk

    # LLM call settings
    llm_temperature: float = 0.5                   # lower = more consistent JSON, less creative drift

    # Action signals — Hinglish phrases that route to action mode
    action_signals: List[str] = [
        "kya karun", "koi suggestion", "batao kaise",
        "help chahiye", "kya karna chahiye", "advice do",
        "kya karu", "kuch suggest karo",
    ]

    # Greeting tokens — pure greetings get no context injection and no projection
    greeting_tokens: List[str] = [
        "hi", "hey", "hello", "heyy", "heyyy", "hiii", "hiiii",
        "yo", "sup", "namaste", "namaskar", "hola", "howdy",
        "hai", "wassup", "whatsup",
    ]

    # Safety
    crisis_keywords_path: str = "./app/safety/crisis_keywords.json"
    semantic_safety_threshold: float = 0.82

    # Response quality
    response_min_length: int = 40   # was 80 — short genuine responses shouldn't regenerate

    # Assessment (PHQ-9 / GAD-7)
    assessment_enabled: bool = True
    assessment_min_severity: str = "mild"   # inject context only above this level
    assessment_ema_alpha_start: float = 0.4  # EMA alpha for new users
    assessment_ema_alpha_floor: float = 0.1  # EMA alpha floor for long-term users

    # Journaling
    journal_context_turns: int = 3          # recent non-private entries injected per chat turn
    journal_max_content_length: int = 10000

    # Database
    database_url: str = "sqlite+aiosqlite:///./mhc.db"
    redis_url: str = "redis://localhost:6379"

    # Debug
    debug_mode: bool = False
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
