"""Test suite for message trimming functions."""

import pytest
from datetime import datetime

from ..state import Message
from ..reducers import trim_messages_by_budget, trim_messages_by_turns


def test_trim_by_turns_preserves_system():
    """System message should always be preserved"""
    system = Message(role="system", content="System prompt", timestamp=datetime.now())
    user1 = Message(role="user", content="Q1", timestamp=datetime.now())
    asst1 = Message(role="assistant", content="A1", timestamp=datetime.now())
    user2 = Message(role="user", content="Q2", timestamp=datetime.now())
    asst2 = Message(role="assistant", content="A2", timestamp=datetime.now())
    
    messages = [system, user1, asst1, user2, asst2]
    
    # Even with keep_turns=1
    result = trim_messages_by_turns(messages, keep_turns=1)
    
    assert result[0].role == "system"
    assert result[0].content == "System prompt"


def test_trim_by_turns_keeps_last_turns():
    """Should keep last N conversation turns"""
    messages = []
    
    # Add 5 turns
    for i in range(5):
        messages.append(Message(role="user", content=f"Q{i+1}", timestamp=datetime.now()))
        messages.append(Message(role="assistant", content=f"A{i+1}", timestamp=datetime.now()))
    
    result = trim_messages_by_turns(messages, keep_turns=2)
    
    # Should have 4 messages (2 turns)
    assert len(result) == 4
    assert result[0].content == "Q4"
    assert result[1].content == "A4"
    assert result[2].content == "Q5"
    assert result[3].content == "A5"


def test_trim_by_turns_no_trimming_needed():
    """If messages <= keep_turns, no trimming should occur"""
    user = Message(role="user", content="Q1", timestamp=datetime.now())
    asst = Message(role="assistant", content="A1", timestamp=datetime.now())
    
    messages = [user, asst]
    
    result = trim_messages_by_turns(messages, keep_turns=5)
    
    assert len(result) == 2


def test_trim_by_budget_preserves_system():
    """System message should always be preserved regardless of budget"""
    system = Message(role="system", content="A" * 1000, timestamp=datetime.now())  # Large system message
    user = Message(role="user", content="Hi", timestamp=datetime.now())
    
    messages = [system, user]
    
    # Very small budget
    result = trim_messages_by_budget(messages, token_budget=10)
    
    # System should still be there
    assert result[0].role == "system"


def test_trim_by_budget_removes_oldest_first():
    """Should remove oldest messages first when over budget"""
    system = Message(role="system", content="System", timestamp=datetime.now())
    msg1 = Message(role="user", content="A" * 100, timestamp=datetime.now())  # ~25 tokens
    msg2 = Message(role="assistant", content="B" * 100, timestamp=datetime.now())  # ~25 tokens
    msg3 = Message(role="user", content="C" * 100, timestamp=datetime.now())  # ~25 tokens
    msg4 = Message(role="assistant", content="D" * 100, timestamp=datetime.now())  # ~25 tokens
    
    messages = [system, msg1, msg2, msg3, msg4]
    
    # Budget for ~60 tokens (system + 2 most recent)
    result = trim_messages_by_budget(messages, token_budget=60)
    
    # Should keep system + last 2 messages
    assert len(result) == 3
    assert result[0].role == "system"
    assert result[1].content == "C" * 100
    assert result[2].content == "D" * 100


def test_trim_by_budget_no_trimming_needed():
    """If under budget, no trimming should occur"""
    system = Message(role="system", content="System", timestamp=datetime.now())
    user = Message(role="user", content="Hi", timestamp=datetime.now())
    
    messages = [system, user]
    
    # Large budget
    result = trim_messages_by_budget(messages, token_budget=1000)
    
    assert len(result) == 2


def test_trim_by_turns_incomplete_turn():
    """Should handle incomplete turns (user without assistant response)"""
    user1 = Message(role="user", content="Q1", timestamp=datetime.now())
    asst1 = Message(role="assistant", content="A1", timestamp=datetime.now())
    user2 = Message(role="user", content="Q2", timestamp=datetime.now())
    asst2 = Message(role="assistant", content="A2", timestamp=datetime.now())
    user3 = Message(role="user", content="Q3", timestamp=datetime.now())
    # No assistant response yet
    
    messages = [user1, asst1, user2, asst2, user3]
    
    result = trim_messages_by_turns(messages, keep_turns=1)
    
    # Should keep last complete turn + incomplete user message
    assert len(result) == 3
    assert result[0].content == "Q2"
    assert result[1].content == "A2"
    assert result[2].content == "Q3"


def test_trim_empty_messages():
    """Should handle empty message list"""
    result = trim_messages_by_turns([], keep_turns=2)
    assert len(result) == 0
    
    result = trim_messages_by_budget([], token_budget=100)
    assert len(result) == 0
