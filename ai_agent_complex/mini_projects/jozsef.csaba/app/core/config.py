"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    app_name: str = "Customer Service Triage Agent"
    app_version: str = "1.0.0"
    debug: bool = True

    # OpenAI
    openai_api_key: str

    # LLM Settings
    llm_model: str = "gpt-4-turbo-preview"
    embedding_model: str = "text-embedding-3-large"
    temperature: float = 0.3
    max_tokens: int = 2000

    # Vector Store
    faiss_index_path: str = "./data/faiss_index"
    top_k_retrieval: int = 10
    top_k_rerank: int = 3

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance (Dependency Injection pattern)."""
    return Settings()
