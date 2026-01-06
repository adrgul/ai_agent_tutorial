"""
Simple token estimator for teaching purposes.

Uses rough approximation: ~4 characters per token (GPT tokenization average).
For production, use tiktoken library.
"""


def estimate_tokens(text: str) -> int:
    """
    Estimate token count from text length.
    
    Rule of thumb: ~4 characters per token for English text.
    This is approximate but good enough for teaching/demo purposes.
    """
    if not text:
        return 0
    return max(1, len(text) // 4)


def estimate_messages_tokens(messages: list) -> int:
    """
    Estimate total tokens in a list of messages.
    
    Includes role tokens and separators.
    """
    total = 0
    for msg in messages:
        # Role overhead: ~4 tokens per message for role + separators
        total += 4
        # Content
        if hasattr(msg, 'content'):
            total += estimate_tokens(msg.content)
        elif isinstance(msg, dict) and 'content' in msg:
            total += estimate_tokens(msg['content'])
    return total
