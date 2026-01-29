"""Configuration management for the application."""
import os
from typing import Optional


class Config:
    """Application configuration loaded from environment variables."""
    
    # LLM Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Cache TTL (in seconds)
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "300"))
    
    # LangGraph configuration
    MAX_RECURSION_LIMIT: int = int(os.getenv("MAX_RECURSION_LIMIT", "25"))
    
    @classmethod
    def has_api_key(cls) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(cls.OPENAI_API_KEY and cls.OPENAI_API_KEY.strip())


config = Config()
