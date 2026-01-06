"""
Facts Extractor Node - Extract structured facts from conversation.

Uses LLM to identify key facts (preferences, personal info, context).
Performs upsert logic: new facts are added, existing facts are updated.
"""
import os
from typing import Dict, Any, List
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..state import AppState, Fact, TraceEntry
from ..utils.retry import retry_with_backoff


# LLM for fact extraction
llm = ChatOpenAI(
    model="gpt-4",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY")
)


FACT_EXTRACTION_PROMPT = """Extract key facts from the conversation.
Focus on:
- User preferences
- Personal information
- Important context
- Decisions made

Return a JSON array of facts, each with:
{
  "key": "unique_fact_key",
  "value": "fact_value",
  "category": "preference|personal|context|decision"
}

Conversation:
{conversation}

Return ONLY the JSON array, no other text."""


@retry_with_backoff(max_retries=3, initial_delay=1.0)
async def extract_facts_with_llm(conversation_text: str) -> List[Dict[str, str]]:
    """Call LLM to extract facts"""
    messages = [
        SystemMessage(content="You are a fact extraction assistant. Return only valid JSON."),
        HumanMessage(content=FACT_EXTRACTION_PROMPT.format(conversation=conversation_text))
    ]
    
    response = await llm.ainvoke(messages)
    
    # Parse JSON response
    import json
    facts_data = json.loads(response.content)
    
    return facts_data


async def facts_extractor_node(state: AppState, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and upsert facts from recent conversation.
    
    Args:
        state: Current AppState
        config: Configuration (unused here)
    
    Returns:
        Update to facts channel with new/updated facts
    """
    # Get recent messages (last 4)
    recent_messages = state.messages[-4:] if len(state.messages) >= 4 else state.messages
    
    if not recent_messages:
        return {"trace": [TraceEntry(step="facts_extractor", action="skip", details="No messages")]}
    
    # Format conversation for LLM
    conversation_text = "\n".join([
        f"{msg.role}: {msg.content}"
        for msg in recent_messages
    ])
    
    try:
        # Extract facts with LLM
        facts_data = await extract_facts_with_llm(conversation_text)
        
        # Convert to Fact objects
        new_facts = []
        for fact_dict in facts_data:
            fact = Fact(
                key=fact_dict["key"],
                value=fact_dict["value"],
                category=fact_dict.get("category", "context"),
                timestamp=datetime.now()
            )
            new_facts.append(fact)
        
        # Add trace entry
        trace_entry = TraceEntry(
            step="facts_extractor",
            action="extracted_facts",
            details=f"Extracted {len(new_facts)} facts"
        )
        
        return {
            "facts": new_facts,
            "trace": [trace_entry]
        }
        
    except Exception as e:
        print(f"Error extracting facts: {e}")
        trace_entry = TraceEntry(
            step="facts_extractor",
            action="error",
            details=f"Failed: {str(e)}"
        )
        return {"trace": [trace_entry]}
