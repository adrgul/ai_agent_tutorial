"""Text chunking utilities for sentence-based splitting with token limits."""

import nltk
from typing import List
import logging

# Download sentence tokenizer on first use
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

logger = logging.getLogger(__name__)


def approximate_token_count(text: str) -> int:
    """
    Approximate the number of tokens in a text by splitting on whitespace.
    This is a simple heuristic; can be replaced with a proper tokenizer later.
    
    Args:
        text: Input text to count tokens for
        
    Returns:
        Approximate token count
    """
    return len(text.split())


def chunk_text(text: str, max_tokens: int = 500) -> List[str]:
    """
    Split text into chunks based on sentences, respecting a maximum token limit.
    
    The algorithm:
    1. Split the text into sentences using NLTK
    2. Concatenate sentences into chunks until adding the next sentence would exceed max_tokens
    3. If a single sentence exceeds max_tokens, include it as its own chunk
    
    Args:
        text: The input text to chunk
        max_tokens: Maximum number of tokens per chunk (default: 500)
        
    Returns:
        List of text chunks
    """
    if not text or not text.strip():
        return []
    
    # Split into sentences
    sentences = nltk.sent_tokenize(text)
    
    if not sentences:
        return []
    
    chunks = []
    current_chunk = []
    current_token_count = 0
    
    for sentence in sentences:
        sentence_tokens = approximate_token_count(sentence)
        
        # If adding this sentence would exceed the limit
        if current_token_count + sentence_tokens > max_tokens and current_chunk:
            # Save current chunk and start a new one
            chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_token_count = sentence_tokens
        else:
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_token_count += sentence_tokens
    
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    logger.info(f"Split text into {len(chunks)} chunks (max {max_tokens} tokens each)")
    return chunks
