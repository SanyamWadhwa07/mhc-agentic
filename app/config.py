from pydantic_settings import BaseSettings
from pydantic import Field


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
    emotional_intensity_threshold: float = 0.8

    # Safety
    crisis_keywords_path: str = "./app/safety/crisis_keywords.json"
    semantic_safety_threshold: float = 0.82

    # Response quality
    response_min_length: int = 80

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
