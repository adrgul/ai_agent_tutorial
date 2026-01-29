"""Router pattern - conditional routing to specialist agents with fan-out."""
from typing import Literal, Union
from langgraph.graph import StateGraph, END
from langgraph.constants import Send
from app.domain.state import SupportState
from app.domain.events import TraceEvent
from app.domain.ticket import TicketTriage
from app.infrastructure.llm.openai_provider import OpenAIProvider
from app.infrastructure.tools.kb_tool import retrieve_kb_articles, format_kb_sources
from app.infrastructure.cache.memory_cache import routing_cache
from app.core.logging import get_logger
import hashlib

logger = get_logger(__name__)


def classify_intent(state: SupportState) -> SupportState:
    """
    Classify user intent using OpenAI to determine routing.
    
    This node demonstrates: conditional edge decision making with LLM classification.
    """
    message = state["messages"][-1]["content"]
    
    # Add trace event
    state["trace"].append(TraceEvent.node_start("classify_intent", {"message_preview": message[:50]}))
    
    # Check cache first
    cache_key = hashlib.md5(message.encode()).hexdigest()
    cached_route = routing_cache.get(cache_key)
    
    if cached_route:
        state["trace"].append(TraceEvent.cache_hit({"route": cached_route}))
        state["routing_decision"] = cached_route
        state["trace"].append(TraceEvent.node_end("classify_intent"))
        return state
    
    # Use OpenAI to classify intent
    llm = OpenAIProvider()
    
    classification_prompt = f"""Classify the following customer support message into categories.
The message may belong to multiple categories (mixed intent).

Categories:
- billing: payments, charges, refunds, invoices
- technical: errors, bugs, technical issues, not working
- account: login, password, profile, access

Customer message: {message}

Respond with ONE of these exact values:
- "billing" (only billing-related)
- "technical" (only technical issues)
- "account" (only account-related)
- "mixed_billing_tech" (both billing and technical)
- "mixed_billing_account" (both billing and account)
- "general" (none of the above or unclear)

Classification:"""
    
    try:
        route_raw = llm.chat_completion(
            [{"role": "user", "content": classification_prompt}],
            temperature=0.2
        ).strip().lower()
        
        # Validate and normalize the response
        valid_routes = [
            "billing", "technical", "account", 
            "mixed_billing_tech", "mixed_billing_account", "general"
        ]
        route = route_raw if route_raw in valid_routes else "general"
        
    except Exception as e:
        logger.error(f"Classification failed: {e}, using general route")
        route = "general"
    
    # Cache the decision
    routing_cache.set(cache_key, route)
    state["trace"].append(TraceEvent.cache_miss({"route": route}))
    
    state["routing_decision"] = route
    state["trace"].append(TraceEvent.node_end("classify_intent"))
    
    return state


def route_to_specialist(state: SupportState) -> Union[list[Send], Literal["billing_specialist", "tech_specialist", "account_specialist", "synthesize"]]:
    """
    Conditional edge: route based on classification.
    
    This demonstrates: conditional edges and Send for fan-out in LangGraph.
    Returns either a single node name or a list of Send objects for parallel execution.
    """
    route = state["routing_decision"]
    
    # Handle mixed intents with fan-out using Send
    if route.startswith("mixed_"):
        sends = []
        
        if "billing" in route:
            sends.append(Send("billing_specialist", state))
        if "tech" in route:
            sends.append(Send("tech_specialist", state))
        if "account" in route:
            sends.append(Send("account_specialist", state))
        
        # Emit trace event for fan-out
        state["trace"].append(
            TraceEvent.send_fanout({
                "specialists": [s.node for s in sends],
                "reason": "Mixed intent detected"
            })
        )
        
        return sends
    elif route == "billing":
        return "billing_specialist"
    elif route == "technical":
        return "tech_specialist"
    elif route == "account":
        return "account_specialist"
    else:
        return "synthesize"


def billing_specialist(state: SupportState) -> SupportState:
    """Billing specialist agent."""
    state["trace"].append(TraceEvent.node_start("billing_specialist"))
    
    llm = OpenAIProvider()
    message = state["messages"][-1]["content"]
    
    # Retrieve relevant KB articles
    articles, kb_event = retrieve_kb_articles(f"billing {message}", top_k=2)
    state["trace"].append(kb_event)
    state["sources"].extend(format_kb_sources(articles))
    
    # Generate specialist response
    kb_context = "\n".join([f"- {a['title']}: {a['content']}" for a in articles])
    
    prompt = f"""You are a billing specialist. Answer this billing question:

{message}

Relevant knowledge:
{kb_context}

Provide a focused answer about billing. Include policy references."""
    
    response = llm.chat_completion([{"role": "user", "content": prompt}], temperature=0.3)
    
    # Store result
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["billing"] = response
    
    state["trace"].append(TraceEvent.node_end("billing_specialist"))
    return state


def tech_specialist(state: SupportState) -> SupportState:
    """Technical specialist agent."""
    state["trace"].append(TraceEvent.node_start("tech_specialist"))
    
    llm = OpenAIProvider()
    message = state["messages"][-1]["content"]
    
    # Retrieve relevant KB articles
    articles, kb_event = retrieve_kb_articles(f"technical troubleshooting {message}", top_k=2)
    state["trace"].append(kb_event)
    state["sources"].extend(format_kb_sources(articles))
    
    # Generate specialist response
    kb_context = "\n".join([f"- {a['title']}: {a['content']}" for a in articles])
    
    prompt = f"""You are a technical support specialist. Answer this technical question:

{message}

Relevant knowledge:
{kb_context}

Provide troubleshooting steps and technical guidance."""
    
    response = llm.chat_completion([{"role": "user", "content": prompt}], temperature=0.3)
    
    # Store result
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["technical"] = response
    
    state["trace"].append(TraceEvent.node_end("tech_specialist"))
    return state


def account_specialist(state: SupportState) -> SupportState:
    """Account specialist agent."""
    state["trace"].append(TraceEvent.node_start("account_specialist"))
    
    llm = OpenAIProvider()
    message = state["messages"][-1]["content"]
    
    # Retrieve relevant KB articles
    articles, kb_event = retrieve_kb_articles(f"account security {message}", top_k=2)
    state["trace"].append(kb_event)
    state["sources"].extend(format_kb_sources(articles))
    
    # Generate specialist response
    kb_context = "\n".join([f"- {a['title']}: {a['content']}" for a in articles])
    
    prompt = f"""You are an account management specialist. Answer this account question:

{message}

Relevant knowledge:
{kb_context}

Provide account-related guidance and security best practices."""
    
    response = llm.chat_completion([{"role": "user", "content": prompt}], temperature=0.3)
    
    # Store result
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["account"] = response
    
    state["trace"].append(TraceEvent.node_end("account_specialist"))
    return state


def synthesize_response(state: SupportState) -> SupportState:
    """
    Synthesize final response from specialist(s).
    
    This node merges multiple specialist outputs or formats single specialist output.
    """
    state["trace"].append(TraceEvent.node_start("synthesize_response"))
    
    specialist_results = state.get("specialist_results") or {}
    
    if len(specialist_results) > 1:
        # Multiple specialists - merge their responses
        combined = "\n\n".join([
            f"**{spec.title()} Team:**\n{response}"
            for spec, response in specialist_results.items()
        ])
        
        final_answer = f"""I've consulted our specialist teams to address your question:

{combined}

Sources: {', '.join(state['sources']) if state['sources'] else 'Internal knowledge'}

Is there anything specific you'd like me to clarify?"""
    
    elif len(specialist_results) == 1:
        # Single specialist
        spec_name, response = list(specialist_results.items())[0]
        final_answer = f"""{response}

Sources: {', '.join(state['sources']) if state['sources'] else 'Internal knowledge'}"""
    
    else:
        # No specialists (general query)
        llm = OpenAIProvider()
        message = state["messages"][-1]["content"]
        final_answer = llm.chat_completion([
            {"role": "user", "content": f"Provide a helpful response to: {message}"}
        ])
    
    state["final_answer"] = final_answer
    state["trace"].append(TraceEvent.node_end("synthesize_response"))
    
    return state


def create_router_graph() -> StateGraph:
    """
    Create the Router pattern graph.
    
    Key concepts demonstrated:
    - Conditional edges (route_to_specialist)
    - Send for fan-out (fanout_specialists)
    - Multiple specialist nodes
    - Synthesis of parallel results
    """
    graph = StateGraph(SupportState)
    
    # Add nodes
    graph.add_node("classify_intent", classify_intent)
    graph.add_node("billing_specialist", billing_specialist)
    graph.add_node("tech_specialist", tech_specialist)
    graph.add_node("account_specialist", account_specialist)
    graph.add_node("synthesize", synthesize_response)
    
    # Set entry point
    graph.set_entry_point("classify_intent")
    
    # Add conditional routing edge
    # When route_to_specialist returns a list of Send objects, they execute in parallel
    # When it returns a string node name, that single node executes
    graph.add_conditional_edges(
        "classify_intent",
        route_to_specialist,
        ["billing_specialist", "tech_specialist", "account_specialist", "synthesize"]
    )
    
    # All specialists flow to synthesis
    graph.add_edge("billing_specialist", "synthesize")
    graph.add_edge("tech_specialist", "synthesize")
    graph.add_edge("account_specialist", "synthesize")
    
    # Synthesize to END
    graph.add_edge("synthesize", END)
    
    return graph
