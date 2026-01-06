"""Test suite for reducers - verify deterministic merging."""

import pytest
from datetime import datetime

from ..state import Message, Fact
from ..reducers import (
    messages_reducer,
    facts_reducer,
    trim_messages_by_budget,
    trim_messages_by_turns,
    generate_message_id
)


def test_messages_reducer_deduplication():
    """Test that messages with same ID are deduplicated"""
    msg1 = Message(role="user", content="Hello", timestamp=datetime.now())
    msg2 = Message(role="user", content="Hello", timestamp=datetime.now(), message_id=msg1.message_id)
    msg3 = Message(role="assistant", content="Hi", timestamp=datetime.now())
    
    result = messages_reducer([msg1, msg2, msg3], [])
    
    # Should only have 2 messages (msg2 is duplicate)
    assert len(result) == 2
    assert result[0].content == "Hello"
    assert result[1].content == "Hi"


def test_messages_reducer_sorting():
    """Test that messages are sorted by timestamp"""
    now = datetime.now()
    msg1 = Message(role="user", content="First", timestamp=now)
    msg2 = Message(role="user", content="Second", timestamp=now.replace(microsecond=now.microsecond + 1000))
    msg3 = Message(role="user", content="Third", timestamp=now.replace(microsecond=now.microsecond + 2000))
    
    # Add in wrong order
    result = messages_reducer([msg3, msg1, msg2], [])
    
    # Should be sorted
    assert result[0].content == "First"
    assert result[1].content == "Second"
    assert result[2].content == "Third"


def test_facts_reducer_upsert():
    """Test that facts are upserted (last-write-wins)"""
    now = datetime.now()
    fact1 = Fact(key="name", value="Alice", category="personal", timestamp=now)
    fact2 = Fact(key="name", value="Bob", category="personal", timestamp=now.replace(microsecond=now.microsecond + 1000))
    fact3 = Fact(key="color", value="blue", category="preference", timestamp=now)
    
    result = facts_reducer([fact1, fact2, fact3], [])
    
    # Should have 2 facts (name was updated)
    assert len(result) == 2
    
    # Find name fact
    name_fact = next(f for f in result if f.key == "name")
    assert name_fact.value == "Bob"


def test_trim_messages_by_turns():
    """Test trimming messages by conversation turns"""
    system_msg = Message(role="system", content="System", timestamp=datetime.now())
    user_msg1 = Message(role="user", content="Q1", timestamp=datetime.now())
    asst_msg1 = Message(role="assistant", content="A1", timestamp=datetime.now())
    user_msg2 = Message(role="user", content="Q2", timestamp=datetime.now())
    asst_msg2 = Message(role="assistant", content="A2", timestamp=datetime.now())
    user_msg3 = Message(role="user", content="Q3", timestamp=datetime.now())
    asst_msg3 = Message(role="assistant", content="A3", timestamp=datetime.now())
    
    messages = [system_msg, user_msg1, asst_msg1, user_msg2, asst_msg2, user_msg3, asst_msg3]
    
    # Keep last 2 turns
    result = trim_messages_by_turns(messages, keep_turns=2)
    
    # Should have system + 2 turns (4 messages)
    assert len(result) == 5
    assert result[0].role == "system"
    assert result[1].content == "Q2"
    assert result[2].content == "A2"
    assert result[3].content == "Q3"
    assert result[4].content == "A3"


def test_trim_messages_by_budget():
    """Test trimming messages by token budget"""
    system_msg = Message(role="system", content="System", timestamp=datetime.now())
    user_msg1 = Message(role="user", content="A" * 100, timestamp=datetime.now())  # ~25 tokens
    asst_msg1 = Message(role="assistant", content="B" * 100, timestamp=datetime.now())  # ~25 tokens
    user_msg2 = Message(role="user", content="C" * 100, timestamp=datetime.now())  # ~25 tokens
    asst_msg2 = Message(role="assistant", content="D" * 100, timestamp=datetime.now())  # ~25 tokens
    
    messages = [system_msg, user_msg1, asst_msg1, user_msg2, asst_msg2]
    
    # Budget for ~50 tokens (system + last 2 messages)
    result = trim_messages_by_budget(messages, token_budget=50)
    
    # Should trim first user/assistant pair
    assert len(result) == 3
    assert result[0].role == "system"
    assert result[1].content == "C" * 100
    assert result[2].content == "D" * 100


def test_generate_message_id_deterministic():
    """Test that message ID generation is deterministic"""
    msg1 = Message(role="user", content="Hello", timestamp=datetime.now())
    msg2 = Message(role="user", content="Hello", timestamp=msg1.timestamp)
    
    # Force same timestamp
    id1 = generate_message_id(msg1)
    id2 = generate_message_id(msg2)
    
    # Should be identical
    assert id1 == id2


def test_generate_message_id_different():
    """Test that different messages get different IDs"""
    msg1 = Message(role="user", content="Hello", timestamp=datetime.now())
    msg2 = Message(role="user", content="World", timestamp=datetime.now())
    
    id1 = generate_message_id(msg1)
    id2 = generate_message_id(msg2)
    
    # Should be different
    assert id1 != id2
