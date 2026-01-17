from langchain_groq import ChatGroq

from src.domain.interfaces import LLMClientProtocol
from src.infrastructure.config import AppSettings


class GroqLLMClient(LLMClientProtocol):
    """
    Concrete implementation of LLMClientProtocol for Groq.
    """

    def __init__(self, settings: AppSettings):
        self.client = ChatGroq(
            temperature=0,
            groq_api_key=settings.GROQ_API_KEY,
            model_name="llama-3.1-8b-instant",
        )

    def invoke(self, prompt: str) -> str:
        """
        Invokes the Groq LLM with a given prompt.
        """
        response = self.client.invoke(prompt)
        return response.content
