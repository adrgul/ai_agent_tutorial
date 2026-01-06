"""
Answer Node - Generate final response using appropriate memory context.

Constructs prompts differently based on memory mode:
- rolling: Full message history
- summary: Summary + recent messages
- facts: Facts + recent messages
- hybrid: Summary + facts + RAG context + recent messages
"""
import os
from typing import Dict, Any, List
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from ..state import AppState, Message, TraceEntry
from ..utils.retry import retry_with_backoff


# LLM for answer generation
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0.7,
    api_key=os.getenv("OPENAI_API_KEY")
)


def build_context_prompt(state: AppState, memory_mode: str) -> str:
    """Build context section based on memory mode"""
    context_parts = []
    
    if memory_mode == "summary" or memory_mode == "hybrid":
        if state.summary:
            context_parts.append(f"Conversation Summary:\n{state.summary.content}")
    
    if memory_mode == "facts" or memory_mode == "hybrid":
        if state.facts:
            facts_text = "\n".join([
                f"- {fact.key}: {fact.value} ({fact.category})"
                for fact in state.facts
            ])
            context_parts.append(f"Known Facts:\n{facts_text}")
    
    if memory_mode == "hybrid":
        if state.retrieved_context:
            docs_text = "\n".join([
                f"- {doc['content'][:200]}... (score: {doc['score']:.2f})"
                for doc in state.retrieved_context.documents
            ])
            context_parts.append(f"Retrieved Context:\n{docs_text}")
    
    return "\n\n".join(context_parts) if context_parts else ""


@retry_with_backoff(max_retries=3, initial_delay=1.0)
async def generate_answer_with_llm(messages: List, system_prompt: str) -> str:
    """Call LLM to generate answer"""
    # Convert to LangChain messages
    lc_messages = [SystemMessage(content=system_prompt)]
    
    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
    
    response = await llm.ainvoke(lc_messages)
    return response.content


async def answer_node(state: AppState, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate final answer using appropriate memory context.
    
    Args:
        state: Current AppState
        config: Contains memory_mode
    
    Returns:
        Update to messages channel with assistant response
    """
    memory_mode = config.get("configurable", {}).get("memory_mode", "rolling")
    
    # Build context from memory
    context_prompt = build_context_prompt(state, memory_mode)
    
    # Build system prompt
    system_prompt = f"""You are a helpful AI assistant.

{context_prompt}

Use the context above to provide informed, personalized responses.
Be conversational and helpful."""
    
    # Get recent messages for prompt (last 6)
    recent_messages = state.messages[-6:] if len(state.messages) >= 6 else state.messages
    
    try:
        # Generate answer
        answer_content = await generate_answer_with_llm(recent_messages, system_prompt)
        
        # Create assistant message
        assistant_message = Message(
            role="assistant",
            content=answer_content,
            timestamp=datetime.now(),
            metadata={"memory_mode": memory_mode}
        )
        
        # Add trace entry
        trace_entry = TraceEntry(
            step="answer",
            action="generated_response",
            details=f"Mode: {memory_mode}, length: {len(answer_content)}"
        )
        
        return {
            "messages": [assistant_message],
            "trace": [trace_entry]
        }
        
    except Exception as e:
        print(f"Error generating answer: {e}")
        
        # Fallback error message
        error_message = Message(
            role="assistant",
            content="I apologize, but I encountered an error generating a response. Please try again.",
            timestamp=datetime.now(),
            metadata={"error": str(e)}
        )
        
        trace_entry = TraceEntry(
            step="answer",
            action="error",
            details=f"Failed: {str(e)}"
        )
        
        return {
            "messages": [error_message],
            "trace": [trace_entry]
        }
