"""
Configuration module for loading application settings.

Single Responsibility: This module is solely responsible for loading
and validating configuration from environment variables.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Config:
    """
    Application configuration loaded from environment variables.
    
    Attributes:
        openai_api_key: OpenAI API key for embeddings.
        embedding_model: Name of the OpenAI embedding model to use.
        chroma_db_path: Path to the ChromaDB persistence directory.
        collection_name: Name of the ChromaDB collection.
    """
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    chroma_db_path: str = "./chroma_db"
    collection_name: str = "prompts"
    
    @classmethod
    def from_env(cls) -> "Config":
        """
        Load configuration from environment variables.
        
        Loads from a .env file if present, then reads environment variables.
        
        Returns:
            Config instance with loaded values.
            
        Raises:
            ValueError: If required environment variables are missing.
        """
        # Load .env file if it exists
        load_dotenv()
        
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Please copy .env.example to .env and add your API key."
            )
        
        return cls(
            openai_api_key=openai_api_key,
            embedding_model=os.getenv("EMBEDDING_MODEL", cls.embedding_model),
            chroma_db_path=os.getenv("CHROMA_DB_PATH", cls.chroma_db_path),
            collection_name=os.getenv("COLLECTION_NAME", cls.collection_name),
        )
