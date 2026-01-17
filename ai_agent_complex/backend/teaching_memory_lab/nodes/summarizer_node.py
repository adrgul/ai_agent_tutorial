"""
Summarizer Node - Create/update conversation summary with delta updates.

For "summary" and "hybrid" memory modes.
Uses delta prompting: "given previous summary and new messages, update summary".
Also performs message trimming based on memory mode.
"""
import os
from typing import Dict, Any
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..state import AppState, Summary, TraceEntry
from ..reducers import trim_messages_by_budget, trim_messages_by_turns
from ..utils.retry import retry_with_backoff


# LLM for summarization
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)


SUMMARY_PROMPT = """Update the conversation summary.

Previous Summary:
{previous_summary}

New Messages:
{new_messages}

Create a concise summary that:
1. Preserves key information from previous summary
2. Incorporates new developments from messages
3. Highlights user preferences, decisions, context

Return only the updated summary text, no preamble."""


@retry_with_backoff(max_retries=3, initial_delay=1.0)
async def generate_summary_with_llm(previous_summary: str, new_messages: str) -> str:
    """Call LLM to generate/update summary"""
    messages = [
        SystemMessage(content="You are a conversation summarization assistant."),
        HumanMessage(content=SUMMARY_PROMPT.format(
            previous_summary=previous_summary,
            new_messages=new_messages
        ))
    ]
    
    response = await llm.ainvoke(messages)
    return response.content


async def summarizer_node(state: AppState, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update summary and trim messages.
    
    Args:
        state: Current AppState
        config: Contains memory_mode
    
    Returns:
        Updates to summary and messages channels
    """
    memory_mode = config.get("configurable", {}).get("memory_mode", "summary")
    
    # Get previous summary
    previous_summary = state.summary.content if state.summary else "None"
    
    # Format new messages (last 4)
    recent_messages = state.messages[-4:] if len(state.messages) >= 4 else state.messages
    new_messages_text = "\n".join([
        f"{msg.role}: {msg.content}"
        for msg in recent_messages
    ])
    
    try:
        # Generate updated summary
        summary_content = await generate_summary_with_llm(previous_summary, new_messages_text)
        
        # Create new summary
        new_summary = Summary(
            content=summary_content,
            version=(state.summary.version + 1) if state.summary else 1,
            timestamp=datetime.now()
        )
        
        # Trim messages based on mode
        if memory_mode == "summary":
            # Keep only last 2 turns (system + 2 pairs)
            trimmed_messages = trim_messages_by_turns(state.messages, keep_turns=2)
        elif memory_mode == "hybrid":
            # Keep last 3 turns for hybrid mode
            trimmed_messages = trim_messages_by_turns(state.messages, keep_turns=3)
        else:
            # No trimming for other modes
            trimmed_messages = state.messages
        
        # Add trace entry
        trace_entry = TraceEntry(
            step="summarizer",
            action="updated_summary",
            details=f"Version {new_summary.version}, trimmed {len(state.messages) - len(trimmed_messages)} messages"
        )
        
        return {
            "summary": new_summary,
            "messages": trimmed_messages,
            "trace": [trace_entry]
        }
        
    except Exception as e:
        print(f"Error generating summary: {e}")
        trace_entry = TraceEntry(
            step="summarizer",
            action="error",
            details=f"Failed: {str(e)}"
        )
        return {"trace": [trace_entry]}
