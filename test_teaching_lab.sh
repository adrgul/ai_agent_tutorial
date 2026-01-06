#!/bin/bash
# Quick test script for Teaching Memory Lab

BASE_URL="http://localhost:8000"

echo "=== Teaching Memory Lab Quick Test ==="
echo ""

# Test 1: Rolling Window
echo "Test 1: Rolling Window Mode"
echo "----------------------------"
curl -s -X POST $BASE_URL/api/teaching/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_rolling",
    "user_id": "test_user",
    "message": "Hello! My name is Alice and I love Python programming.",
    "memory_mode": "rolling"
  }' | jq -r '.response'

echo ""
echo "Follow-up question:"
curl -s -X POST $BASE_URL/api/teaching/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_rolling",
    "user_id": "test_user",
    "message": "What did I tell you about myself?",
    "memory_mode": "rolling"
  }' | jq -r '.response'

echo ""
echo ""

# Test 2: Summary Mode
echo "Test 2: Summary Mode"
echo "--------------------"
curl -s -X POST $BASE_URL/api/teaching/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_summary",
    "user_id": "test_user",
    "message": "I am learning LangGraph and building an AI agent with FastAPI.",
    "memory_mode": "summary"
  }' | jq -r '.response'

echo ""
echo "Follow-up (should use summary):"
curl -s -X POST $BASE_URL/api/teaching/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_summary",
    "user_id": "test_user",
    "message": "What am I learning about?",
    "memory_mode": "summary"
  }' | jq -r '.response'

echo ""
echo ""

# Test 3: Facts Mode
echo "Test 3: Facts Extraction Mode"
echo "------------------------------"
curl -s -X POST $BASE_URL/api/teaching/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_facts",
    "user_id": "test_user",
    "message": "My favorite color is blue and I prefer dark mode. I work as a data scientist.",
    "memory_mode": "facts"
  }' | jq -r '.response'

echo ""
echo "Follow-up (should recall facts):"
curl -s -X POST $BASE_URL/api/teaching/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_facts",
    "user_id": "test_user",
    "message": "What do you know about my preferences?",
    "memory_mode": "facts"
  }' | jq -r '.response'

echo ""
echo ""

# Test 4: Hybrid Mode
echo "Test 4: Hybrid Mode"
echo "-------------------"
curl -s -X POST $BASE_URL/api/teaching/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_hybrid",
    "user_id": "test_user",
    "message": "I am building a chatbot with LangGraph that uses memory management.",
    "memory_mode": "hybrid"
  }' | jq -r '.response'

echo ""
echo "Follow-up (should trigger summary + facts):"
curl -s -X POST $BASE_URL/api/teaching/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_hybrid",
    "user_id": "test_user",
    "message": "Remember what I said earlier about my project?",
    "memory_mode": "hybrid"
  }' | jq -r '.response'

echo ""
echo ""

# List checkpoints
echo "Test 5: List Checkpoints"
echo "------------------------"
curl -s -X GET "$BASE_URL/api/teaching/session/test_rolling/checkpoints?user_id=test_user" \
  | jq -r '.[] | "Checkpoint: \(.checkpoint_id) at \(.created_at)"' | head -3

echo ""
echo "=== All tests completed ==="
