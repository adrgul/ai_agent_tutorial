"""
Main entry point for the vector embeddings demo application.

USAGE INSTRUCTIONS:
-------------------

1. Setup:
   - Copy .env.example to .env:
     $ cp .env.example .env
   
   - Edit .env and add your OpenAI API key:
     OPENAI_API_KEY=sk-your-actual-api-key-here

2. Build Docker image:
   $ docker build -t embedding-demo .

3. Run the application:
   $ docker run -it --env-file .env embedding-demo

4. Interact with the CLI:
   - Type prompts and press Enter
   - View similar prompts from the vector database
   - Type 'exit' to quit

ARCHITECTURE:
-------------
This application demonstrates SOLID principles:

- Single Responsibility: Each module has one clear purpose
  • config.py: Configuration loading
  • embeddings.py: Embedding generation
  • vector_store.py: Vector database operations
  • application.py: Business logic orchestration
  • cli.py: User interface

- Open/Closed: The app is open for extension via interfaces
  • Can swap embedding providers (OpenAI, Cohere, etc.)
  • Can swap vector stores (Chroma, Pinecone, Weaviate, etc.)

- Liskov Substitution: Concrete classes honor their interface contracts

- Interface Segregation: Small, focused interfaces (EmbeddingService, VectorStore)

- Dependency Inversion: High-level logic depends on abstractions, not implementations
"""

from app.config import Config
from app.embeddings import OpenAIEmbeddingService
from app.vector_store import ChromaVectorStore
from app.application import EmbeddingApp
from app.cli import CLI


def main() -> None:
    """
    Initialize and run the application.
    
    This function wires up all dependencies using constructor injection,
    demonstrating the Dependency Inversion Principle.
    """
    try:
        # Load configuration
        config = Config.from_env()
        
        # Initialize embedding service (concrete implementation)
        embedding_service = OpenAIEmbeddingService(
            api_key=config.openai_api_key,
            model=config.embedding_model
        )
        
        # Initialize vector store (concrete implementation)
        vector_store = ChromaVectorStore(
            db_path=config.chroma_db_path,
            collection_name=config.collection_name
        )
        
        # Create application with injected dependencies
        # (app depends on abstractions, not concrete classes)
        app = EmbeddingApp(
            embedding_service=embedding_service,
            vector_store=vector_store
        )
        
        # Create and run CLI
        cli = CLI(app)
        cli.run()
        
    except ValueError as e:
        print(f"Configuration error: {e}")
        exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
