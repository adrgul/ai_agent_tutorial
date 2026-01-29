"""Handoffs pattern - state-driven agent switching."""
from langgraph.graph import StateGraph, END
from app.domain.state import SupportState, AgentAssistOutput
from app.domain.events import TraceEvent
from app.domain.ticket import TicketTriage
from app.domain.policies import check_handoff_policy, generate_case_brief
from app.infrastructure.llm.openai_provider import OpenAIProvider
from app.infrastructure.tools.kb_tool import retrieve_kb_articles, format_kb_sources
from app.infrastructure.tools.customer_tool import get_customer_context, format_customer_context
from typing import Literal


def self_service_agent(state: SupportState) -> SupportState:
    """
    Self-service agent attempts to resolve customer issue using OpenAI.
    
    This agent uses KB and OpenAI to answer and determines if handoff is needed.
    """
    state["trace"].append(TraceEvent.node_start("self_service_agent"))
    
    message = state["messages"][-1]["content"]
    llm = OpenAIProvider()
    
    # Get customer context
    customer_context, customer_event = get_customer_context(state.get("customer_id"))
    state["trace"].append(customer_event)
    
    # Retrieve KB articles
    articles, kb_event = retrieve_kb_articles(message, top_k=3)
    state["trace"].append(kb_event)
    state["sources"].extend(format_kb_sources(articles))
    
    # Build context
    kb_context = "\n".join([f"- {a['title']}: {a['content']}" for a in articles])
    customer_info = format_customer_context(customer_context) if customer_context else "Anonymous customer"
    
    # Generate answer using OpenAI
    prompt = f"""You are a self-service support agent. Provide a helpful answer using the knowledge base.

Customer context:
{customer_info}

Question: {message}

Knowledge base:
{kb_context}

Provide a clear, helpful answer with KB article citations in [KB-XXX] format."""
    
    try:
        answer = llm.chat_completion([{"role": "user", "content": prompt}], temperature=0.4)
        state["final_answer"] = answer
    except Exception as e:
        logger.error(f"Self-service response generation failed: {e}")
        state["final_answer"] = "I apologize, but I'm having trouble generating a response. Please try again."
    
    # Perform triage for tracking using OpenAI
    triage_prompt = f"""Classify this support message:

{message}

Provide:
Category: Billing, Technical, Account, Shipping, or Other
Priority: P1, P2, or P3
Sentiment: positive, neutral, or negative

Format:
Category: [category]
Priority: [priority]
Sentiment: [sentiment]"""
    
    try:
        triage_response = llm.chat_completion(
            [{"role": "user", "content": triage_prompt}],
            temperature=0.2
        ).strip()
        
        # Parse triage
        triage_lines = {line.split(':')[0].strip().lower(): line.split(':', 1)[1].strip() 
                       for line in triage_response.split('\n') if ':' in line}
        
        category = triage_lines.get('category', 'Other')
        priority = triage_lines.get('priority', 'P3').upper()
        sentiment = triage_lines.get('sentiment', 'neutral').lower()
        
    except Exception as e:
        logger.warning(f"Triage failed: {e}, using defaults")
        category, priority, sentiment = "Other", "P3", "neutral"
    
    state["ticket"] = TicketTriage(
        category=category,
        priority=priority,
        sentiment=sentiment,
        routing_team="Self-Service",
        tags=["self_service"],
        confidence=0.80,
    )
    
    state["trace"].append(TraceEvent.node_end("self_service_agent"))
    
    return state


def check_handoff_needed(state: SupportState) -> SupportState:
    """
    Check if handoff to human is needed based on policies.
    
    This node evaluates handoff policies and sets active_agent accordingly.
    """
    state["trace"].append(TraceEvent.node_start("check_handoff"))
    
    message = state["messages"][-1]["content"]
    sentiment = state["ticket"].sentiment if state.get("ticket") else None
    
    # Check handoff policy
    handoff_policy = check_handoff_policy(message, sentiment)
    
    if handoff_policy:
        # Trigger handoff
        state["active_agent"] = "HUMAN"
        
        # Emit handoff event
        state["trace"].append(TraceEvent.handoff(
            from_agent="self_service_agent",
            to_agent="human_agent",
            reason=handoff_policy.reason
        ))
        
        # Update ticket priority if needed
        if state.get("ticket"):
            state["ticket"].priority = handoff_policy.priority
            state["ticket"].tags.append("escalated")
    else:
        # No handoff needed, stay with self-service
        state["active_agent"] = "SELF_SERVICE"
    
    state["trace"].append(TraceEvent.node_end("check_handoff"))
    
    return state


def route_by_agent(state: SupportState) -> Literal["human_escalation", "finalize"]:
    """
    Conditional edge: route based on active_agent.
    
    This demonstrates state-driven routing.
    """
    if state["active_agent"] == "HUMAN":
        return "human_escalation"
    else:
        return "finalize"


def human_escalation_agent(state: SupportState) -> SupportState:
    """
    Human escalation agent prepares case for human handoff.
    
    This agent generates a case brief and agent assist output for the human.
    """
    state["trace"].append(TraceEvent.node_start("human_escalation_agent"))
    
    message = state["messages"][-1]["content"]
    
    # Generate case brief
    context = {
        "category": state["ticket"].category if state.get("ticket") else "Unknown",
        "priority": state["ticket"].priority if state.get("ticket") else "P2",
        "sentiment": state["ticket"].sentiment if state.get("ticket") else "neutral",
        "handoff_reason": "Policy trigger detected",
        "sources": state.get("sources", []),
    }
    
    case_brief = generate_case_brief(message, context)
    
    # Generate agent assist output
    llm = OpenAIProvider()
    
    draft_prompt = f"""Generate a professional draft reply for a human agent to review.
The case has been escalated due to policy triggers.

Customer message: {message}

Case context:
{case_brief}

Write an empathetic, policy-compliant draft that a human agent can customize."""
    
    draft_reply = llm.chat_completion([{"role": "user", "content": draft_prompt}], temperature=0.5)
    
    state["agent_assist"] = AgentAssistOutput(
        draft_reply=draft_reply,
        case_summary=[
            f"Escalated {state['ticket'].category} case" if state.get('ticket') else "Escalated case",
            f"Priority: {state['ticket'].priority}" if state.get('ticket') else "Priority: P2",
            "Requires human review due to policy trigger",
        ],
        next_actions=[
            "Review case brief and customer history",
            "Verify customer identity and account details",
            "Assess situation against policy guidelines",
            "Provide personalized resolution",
            "Document outcome and update ticket",
        ],
    )
    
    # Update final answer with handoff message
    state["final_answer"] = f"""This case requires human assistance and has been escalated to our specialist team.

**Case Brief:**
{case_brief}

**Next Steps:**
A human agent will review your case and contact you shortly. Our team will provide personalized assistance based on your specific situation.

**Reference:** Your case has been prioritized as {state['ticket'].priority if state.get('ticket') else 'P2'}."""
    
    state["trace"].append(TraceEvent.node_end("human_escalation_agent"))
    
    return state


def finalize_response(state: SupportState) -> SupportState:
    """Finalize the response (no handoff)."""
    state["trace"].append(TraceEvent.node_start("finalize"))
    
    # Generate agent assist even for self-service cases
    if not state.get("agent_assist"):
        llm = OpenAIProvider()
        message = state["messages"][-1]["content"]
        
        state["agent_assist"] = AgentAssistOutput(
            draft_reply=state.get("final_answer", "Response generated"),
            case_summary=[
                "Self-service resolution",
                f"Category: {state['ticket'].category}" if state.get('ticket') else "General inquiry",
                "No escalation required",
            ],
            next_actions=[
                "Monitor customer satisfaction",
                "Check if follow-up needed",
            ],
        )
    
    state["trace"].append(TraceEvent.node_end("finalize"))
    return state


def create_handoffs_graph() -> StateGraph:
    """
    Create the Handoffs pattern graph.
    
    Key concepts demonstrated:
    - State-driven agent switching (active_agent field)
    - Handoff events in trace
    - Policy-based escalation
    - Case brief generation for human agents
    """
    graph = StateGraph(SupportState)
    
    # Add nodes
    graph.add_node("self_service", self_service_agent)
    graph.add_node("check_handoff", check_handoff_needed)
    graph.add_node("human_escalation", human_escalation_agent)
    graph.add_node("finalize", finalize_response)
    
    # Set entry point
    graph.set_entry_point("self_service")
    
    # Flow: self_service -> check_handoff
    graph.add_edge("self_service", "check_handoff")
    
    # Conditional routing based on active_agent
    graph.add_conditional_edges(
        "check_handoff",
        route_by_agent,
        {
            "human_escalation": "human_escalation",
            "finalize": "finalize",
        }
    )
    
    # Both paths end
    graph.add_edge("human_escalation", END)
    graph.add_edge("finalize", END)
    
    return graph
