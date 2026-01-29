"""OpenAI LLM provider implementation."""
import json
from typing import List, Dict, Any, Optional
from app.infrastructure.llm.base import LLMClient
from app.core.config import config
from app.core.logging import get_logger

logger = get_logger(__name__)


class OpenAIProvider(LLMClient):
    """OpenAI LLM provider using real API."""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or config.MODEL_NAME
        
        if not config.has_api_key():
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
            )
        
        try:
            import openai
            self.client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            logger.info(f"OpenAI client initialized with model: {self.model_name}")
        except ImportError as e:
            raise ImportError(
                "openai package not installed. Run: pip install openai"
            ) from e
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate chat completion using OpenAI API."""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            logger.debug(f"OpenAI completion tokens: {response.usage.total_tokens}")
            return content
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def get_embeddings(self, text: str, model: str = "text-embedding-3-small") -> List[float]:
        """Generate embeddings for text using OpenAI API."""
        try:
            response = self.client.embeddings.create(
                model=model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"OpenAI embeddings error: {e}")
            raise
    
    def get_model_name(self) -> str:
        """Return model name."""
        return self.model_name
