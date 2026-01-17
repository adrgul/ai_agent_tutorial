"""
Test suite for parallel reducer behavior.

TEACHING OBJECTIVE:
===================
These tests prove that reducers provide deterministic state merging
regardless of parallel execution order. This is critical for understanding
how LangGraph prevents race conditions.

Key Properties Tested:
----------------------
1. COMMUTATIVITY: merge(A, B) = merge(B, A)
   Order of parallel node completion doesn't matter

2. ASSOCIATIVITY: merge(merge(A, B), C) = merge(A, merge(B, C))
   Grouping of parallel outputs doesn't matter

3. IDEMPOTENCE: merge(A, A) = A
   Re-applying same update is safe (for retries)

4. DETERMINISM: Same inputs always produce same output
   No hidden state, no timestamps affecting comparison
"""

import pytest
from datetime import datetime, timedelta

from ..state import Message, Fact, Summary, TraceEntry
from ..reducers import (
    messages_reducer,
    facts_reducer,
    summary_reducer,
    trace_reducer
)


class TestParallelReducerProperties:
    """
    TEACHING: These tests demonstrate that reducers enable safe parallel execution.
    """
    
    def test_messages_reducer_commutative(self):
        """
        TEACHING: Message merge order doesn't matter.
        
        If two parallel nodes both add messages, the final result should be
        identical regardless of which node's output is processed first.
        """
        # Simulate two parallel nodes producing messages
        node1_messages = [
            Message(role="user", content="From node 1", timestamp=datetime.now())
        ]
        node2_messages = [
            Message(role="assistant", content="From node 2", timestamp=datetime.now())
        ]
        
        # Merge in different orders
        result1 = messages_reducer(node1_messages, node2_messages)
        result2 = messages_reducer(node2_messages, node1_messages)
        
        # Results should be identical (sorted by timestamp)
        assert len(result1) == len(result2)
        assert [m.content for m in result1] == [m.content for m in result2]
    
    def test_facts_reducer_commutative(self):
        """
        TEACHING: Fact merge order doesn't matter (last-write-wins by timestamp).
        
        If parallel nodes extract facts about the same key, the newer one wins
        regardless of processing order.
        """
        now = datetime.now()
        
        # Node 1 extracts older fact
        node1_facts = [
            Fact(key="color", value="blue", category="preference", timestamp=now)
        ]
        
        # Node 2 extracts newer fact (1 second later)
        node2_facts = [
            Fact(key="color", value="red", category="preference", timestamp=now + timedelta(seconds=1))
        ]
        
        # Merge in different orders
        result1 = facts_reducer(node1_facts, node2_facts)
        result2 = facts_reducer(node2_facts, node1_facts)
        
        # Both should have "red" (newer timestamp)
        assert len(result1) == 1
        assert len(result2) == 1
        assert result1[0].value == "red"
        assert result2[0].value == "red"
    
    def test_facts_reducer_same_timestamp_lexicographic(self):
        """
        TEACHING: When timestamps are identical, use lexicographic ordering for determinism.
        
        This prevents non-deterministic behavior in edge cases.
        """
        now = datetime.now()
        
        # Both facts have same timestamp
        fact1 = Fact(key="lang", value="python", category="preference", timestamp=now)
        fact2 = Fact(key="lang", value="rust", category="preference", timestamp=now)
        
        # Merge in different orders
        result1 = facts_reducer([fact1], [fact2])
        result2 = facts_reducer([fact2], [fact1])
        
        # Both should pick same value (lexicographically later: "rust" > "python")
        assert result1[0].value == result2[0].value
        assert result1[0].value == "rust"  # "rust" comes after "python"
    
    def test_summary_reducer_version_aware(self):
        """
        TEACHING: Summary replacement is version-aware and deterministic.
        
        Higher version always wins, regardless of merge order.
        """
        # Node 1 produces version 2
        summary1 = Summary(content="Summary v2", version=2, timestamp=datetime.now())
        
        # Node 2 produces version 3
        summary2 = Summary(content="Summary v3", version=3, timestamp=datetime.now())
        
        # Merge in different orders
        result1 = summary_reducer(summary1, summary2)
        result2 = summary_reducer(summary2, summary1)
        
        # Both should pick version 3
        assert result1.version == 3
        assert result2.version == 3
        assert result1.content == "Summary v3"
        assert result2.content == "Summary v3"
    
    def test_trace_reducer_append_order_matters_but_bounded(self):
        """
        TEACHING: Trace is append-only but bounded to prevent unbounded growth.
        
        Unlike other reducers, trace IS order-dependent (it's a log),
        but the max_size limit ensures deterministic behavior.
        """
        # Node 1 trace
        trace1 = [
            TraceEntry(step="node1", action="action1", details="detail1")
        ]
        
        # Node 2 trace
        trace2 = [
            TraceEntry(step="node2", action="action2", details="detail2")
        ]
        
        # Merge in different orders
        result1 = trace_reducer(trace1, trace2)
        result2 = trace_reducer(trace2, trace1)
        
        # Both should have both entries (order may differ but length is same)
        assert len(result1) == 2
        assert len(result2) == 2
    
    def test_messages_reducer_deduplication_idempotent(self):
        """
        TEACHING: Applying same message update twice has no effect (idempotence).
        
        Critical for retry safety - if a node's output is processed twice,
        no duplicates are created.
        """
        msg = Message(role="user", content="Hello", timestamp=datetime.now())
        
        # Merge same message multiple times
        result1 = messages_reducer([msg], [])
        result2 = messages_reducer(result1, [msg])  # Apply again
        
        # Should still have only 1 message
        assert len(result1) == 1
        assert len(result2) == 1
        assert result1[0].message_id == result2[0].message_id
    
    def test_facts_reducer_idempotent(self):
        """
        TEACHING: Re-applying same fact update is safe.
        
        If fact extraction runs twice on same data, no duplicates.
        """
        fact = Fact(key="name", value="Alice", category="personal", timestamp=datetime.now())
        
        # Merge same fact multiple times
        result1 = facts_reducer([fact], [])
        result2 = facts_reducer(result1, [fact])  # Apply again
        
        # Should still have only 1 fact
        assert len(result1) == 1
        assert len(result2) == 1
        assert result2[0].key == "name"
        assert result2[0].value == "Alice"


class TestParallelExecutionScenarios:
    """
    TEACHING: Realistic scenarios showing how parallel nodes interact.
    """
    
    def test_parallel_summarizer_and_facts_extraction(self):
        """
        TEACHING: Simulate parallel execution of summarizer + facts extractor.
        
        Scenario:
        - summarizer_node produces: summary update
        - facts_extractor_node produces: facts delta
        - Both run in parallel, reducers merge outputs
        """
        # Initial state
        existing_messages = [
            Message(role="user", content="I like Python", timestamp=datetime.now())
        ]
        existing_facts = []
        existing_summary = None
        
        # Node 1: Summarizer produces summary
        summary_from_parallel = Summary(
            content="User mentioned Python preference",
            version=1,
            timestamp=datetime.now()
        )
        
        # Node 2: Facts extractor produces facts
        facts_from_parallel = [
            Fact(key="language", value="Python", category="preference", timestamp=datetime.now())
        ]
        
        # Simulate reducer merge (order doesn't matter)
        merged_summary_1 = summary_reducer(existing_summary, summary_from_parallel)
        merged_facts_1 = facts_reducer(existing_facts, facts_from_parallel)
        
        # Reverse order
        merged_summary_2 = summary_reducer(summary_from_parallel, existing_summary)
        merged_facts_2 = facts_reducer(facts_from_parallel, existing_facts)
        
        # Both orders produce same result
        assert merged_summary_1.version == merged_summary_2.version
        assert len(merged_facts_1) == len(merged_facts_2)
        assert merged_facts_1[0].value == merged_facts_2[0].value
    
    def test_three_parallel_nodes_associative(self):
        """
        TEACHING: Associativity means grouping doesn't matter.
        
        If we have 3 parallel nodes (A, B, C), these should be equivalent:
        - merge(merge(A, B), C)
        - merge(A, merge(B, C))
        """
        fact_a = Fact(key="a", value="1", category="test", timestamp=datetime.now())
        fact_b = Fact(key="b", value="2", category="test", timestamp=datetime.now())
        fact_c = Fact(key="c", value="3", category="test", timestamp=datetime.now())
        
        # Group (A, B) first, then merge with C
        result1 = facts_reducer(
            facts_reducer([fact_a], [fact_b]),
            [fact_c]
        )
        
        # Group (B, C) first, then merge with A
        result2 = facts_reducer(
            [fact_a],
            facts_reducer([fact_b], [fact_c])
        )
        
        # Results should be identical
        assert len(result1) == 3
        assert len(result2) == 3
        assert {f.key for f in result1} == {f.key for f in result2}


class TestReducerEdgeCases:
    """
    TEACHING: Edge cases that reducers must handle correctly.
    """
    
    def test_empty_merge(self):
        """Merging with empty list should work"""
        msg = Message(role="user", content="Test", timestamp=datetime.now())
        
        result = messages_reducer([msg], [])
        assert len(result) == 1
        
        result = messages_reducer([], [msg])
        assert len(result) == 1
    
    def test_both_empty(self):
        """Merging two empty lists should return empty"""
        result = messages_reducer([], [])
        assert len(result) == 0
        
        result = facts_reducer([], [])
        assert len(result) == 0
    
    def test_none_summary_merge(self):
        """Merging with None summary should work"""
        summary = Summary(content="Test", version=1, timestamp=datetime.now())
        
        result = summary_reducer(None, summary)
        assert result.version == 1
        
        result = summary_reducer(summary, None)
        assert result.version == 1
    
    def test_fact_conflict_resolution(self):
        """
        When same key appears in parallel outputs with different timestamps,
        newer one should win.
        """
        now = datetime.now()
        
        # Parallel node 1: older timestamp
        fact1 = Fact(key="status", value="old", category="test", timestamp=now)
        
        # Parallel node 2: newer timestamp
        fact2 = Fact(key="status", value="new", category="test", timestamp=now + timedelta(seconds=1))
        
        result = facts_reducer([fact1], [fact2])
        
        assert len(result) == 1
        assert result[0].value == "new"  # Newer wins


# Run with: pytest tests/test_parallel_reducers.py -v
