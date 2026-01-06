"""Configuration settings for the RAG application."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Qdrant settings
QDRANT_URL = "http://localhost:6333"
QDRANT_COLLECTION = "rag_chunks"

# Groq API settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"  # Fast Groq model

# Embedding settings
EMBEDDING_MODEL_NAME = "BAAI/bge-m3"

# RAG settings
TOP_K = 8
MAX_CONTEXT_CHARS = 8000
MAX_CHUNK_TOKENS = 600
