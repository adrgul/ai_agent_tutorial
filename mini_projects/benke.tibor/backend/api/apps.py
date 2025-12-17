"""
Django app configuration.
"""
import logging
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        """Initialize services on app startup."""
        logger.info("Initializing API app...")

        try:
            # Import dependencies
            from pathlib import Path
            from infrastructure.openai_clients import OpenAIClientFactory
            from infrastructure.repositories import (
                FileUserRepository,
                FileConversationRepository,
            )
            from infrastructure.rag_client import MockQdrantClient  # Use Mock for development
            from infrastructure.postgres_client import postgres_client
            from services.agent import QueryAgent
            from services.chat_service import ChatService

            # Initialize Postgres connection pool (defer to first request if in event loop)
            try:
                import asyncio
                # Check if event loop is already running (uvicorn/ASGI)
                try:
                    loop = asyncio.get_running_loop()
                    # Event loop running - schedule initialization
                    loop.create_task(postgres_client.initialize())
                    logger.info("✅ Postgres initialization scheduled")
                except RuntimeError:
                    # No event loop - safe to use asyncio.run()
                    asyncio.run(postgres_client.initialize())
                    logger.info("✅ Postgres initialized")
            except Exception as pg_error:
                logger.warning(f"⚠️ Postgres initialization failed (feedback disabled): {pg_error}")

            # Initialize repositories
            user_repo = FileUserRepository(data_dir=settings.USERS_DIR)
            conversation_repo = FileConversationRepository(data_dir=settings.SESSIONS_DIR)

            # Initialize RAG client (Mock for development - has pre-loaded docs)
            rag_client = MockQdrantClient()

            # Initialize LLM from centralized factory
            llm = OpenAIClientFactory.get_llm(
                model=settings.OPENAI_MODEL,
                temperature=settings.LLM_TEMPERATURE,
                api_key=settings.OPENAI_API_KEY
            )

            # Initialize agent
            agent = QueryAgent(llm_client=llm, rag_client=rag_client)

            # Initialize chat service
            chat_service = ChatService(
                user_repo=user_repo,
                conversation_repo=conversation_repo,
                agent=agent,
            )

            # Store in app config for later access
            self.chat_service = chat_service
            self.user_repo = user_repo
            self.conversation_repo = conversation_repo

            logger.info("API app initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize API app: {e}", exc_info=True)
            raise
