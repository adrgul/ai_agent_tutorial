"""Intent Detection Service.

Following SOLID principles:
- Single Responsibility: Only handles intent and sentiment detection
- Dependency Inversion: Depends on LLM abstraction
"""

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.models.schemas import IntentDetectionResult, ProblemType, Sentiment, TicketInput


class IntentDetectionService:
    """Service for detecting customer intent and sentiment."""

    def __init__(self, settings: Settings):
        """Initialize intent detection service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=settings.temperature,
            openai_api_key=settings.openai_api_key,
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert customer service analyst. Analyze the customer's message and determine:
1. Problem type: billing, technical, account, feature_request, or other
2. Sentiment: frustrated, neutral, or satisfied
3. Confidence score (0.0-1.0)
4. Brief reasoning

Return ONLY a valid JSON object with this exact structure:
{{
    "problem_type": "billing|technical|account|feature_request|other",
    "sentiment": "frustrated|neutral|satisfied",
    "confidence": 0.95,
    "reasoning": "Brief explanation"
}}"""),
            ("user", """Subject: {subject}

Message: {message}

Analyze this customer message and return the JSON response.""")
        ])

        self.parser = JsonOutputParser()

    async def detect_intent(self, ticket: TicketInput) -> IntentDetectionResult:
        """Detect customer intent and sentiment.

        Args:
            ticket: Customer ticket input

        Returns:
            Intent detection result
        """
        # Create chain
        chain = self.prompt | self.llm | self.parser

        # Invoke LLM
        result = await chain.ainvoke({
            "subject": ticket.subject,
            "message": ticket.message,
        })

        # Parse and validate
        return IntentDetectionResult(
            problem_type=ProblemType(result["problem_type"]),
            sentiment=Sentiment(result["sentiment"]),
            confidence=float(result["confidence"]),
            reasoning=result["reasoning"],
        )

    def detect_intent_sync(self, ticket: TicketInput) -> IntentDetectionResult:
        """Synchronous version of intent detection.

        Args:
            ticket: Customer ticket input

        Returns:
            Intent detection result
        """
        # Create chain
        chain = self.prompt | self.llm | self.parser

        # Invoke LLM
        result = chain.invoke({
            "subject": ticket.subject,
            "message": ticket.message,
        })

        # Parse and validate
        return IntentDetectionResult(
            problem_type=ProblemType(result["problem_type"]),
            sentiment=Sentiment(result["sentiment"]),
            confidence=float(result["confidence"]),
            reasoning=result["reasoning"],
        )
