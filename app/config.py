"""Central configuration. Values come from environment variables or a .env file."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM (any OpenAI-compatible endpoint: Groq, Gemini, Ollama, ...) ---
    llm_base_url: str = "https://api.groq.com/openai/v1"
    llm_api_key: str = ""
    llm_model: str = "openai/gpt-oss-20b"
    llm_timeout_s: float = 30.0
    llm_max_retries: int = 2
    llm_min_request_interval_s: float = 2.0

    # --- Embeddings ---
    embedding_backend: str = "sentence-transformers"  # or "hash" (tests only)
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Storage ---
    chroma_dir: str = "data/chroma"

    # --- Chunking / retrieval ---
    chunk_size: int = 800        # characters
    chunk_overlap: int = 120     # characters
    top_k: int = 5
    min_score: float = 0.30      # cosine similarity below this = "not relevant"
    max_context_chars: int = 6000
    min_grounding: float = 0.15  # output guardrail: share of answer words found in cited chunks

    # --- Limits ---
    max_question_chars: int = 1000
    max_upload_mb: int = 10
    rate_limit_per_min: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
