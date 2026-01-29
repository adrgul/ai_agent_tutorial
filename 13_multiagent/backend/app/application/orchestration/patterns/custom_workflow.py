"""Custom workflow - deterministic pipeline with agentic nodes and recursion limit."""
from langgraph.graph import StateGraph, END
from app.domain.state import SupportState, AgentAssistOutput
from app.domain.events import TraceEvent
from app.domain.ticket import TicketTriage
from app.domain.policies import check_handoff_policy
from app.infrastructure.llm.openai_provider import OpenAIProvider
from app.infrastructure.tools.kb_tool import retrieve_kb_articles, format_kb_sources
from app.infrastructure.tools.ticketing_tool import ticketing_tool
from app.core.logging import get_logger
from typing import Literal
import re

logger = get_logger(__name__)


def sanitize_input(state: SupportState) -> SupportState:
    """
    Sanitize and clean input.
    
    First deterministic step in the pipeline.
    """
    state["trace"].append(TraceEvent.node_start("sanitize_input"))
    
    message = state["messages"][-1]["content"]
    
    # Basic sanitization (remove excessive whitespace, etc.)
    sanitized = re.sub(r'\s+', ' ', message).strip()
    
    # Update message
    state["messages"][-1]["content"] = sanitized
    
    state["trace"].append(TraceEvent.node_end("sanitize_input", {"original_length": len(message), "sanitized_length": len(sanitized)}))
    
    return state


def extract_entities(state: SupportState) -> SupportState:
    """
    Extract entities from message.
    
    Second deterministic step - extracts order IDs, emails, product names, error codes.
    """
    state["trace"].append(TraceEvent.node_start("extract_entities"))
    
    message = state["messages"][-1]["content"]
    
    entities = {}
    
    # Extract order IDs (format: ORD-XXXX)
    order_ids = re.findall(r'ORD-\d+', message, re.IGNORECASE)
    if order_ids:
        entities["order_ids"] = order_ids
    
    # Extract emails
    emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message)
    if emails:
        entities["emails"] = emails
    
    # Extract error codes (format: ERR-XXX or ERROR XXX)
    error_codes = re.findall(r'(?:ERR|ERROR)[-\s]?\d+', message, re.IGNORECASE)
    if error_codes:
        entities["error_codes"] = error_codes
    
    # Store entities in state
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["entities"] = entities
    
    state["trace"].append(TraceEvent.node_end("extract_entities", {"entities": entities}))
    
    return state


def triage_request(state: SupportState) -> SupportState:
    """
    Triage the request using OpenAI for classification.
    
    Third step - AI-powered classification.
    """
    state["trace"].append(TraceEvent.node_start("triage_request"))
    
    message = state["messages"][-1]["content"]
    llm = OpenAIProvider()
    
    # Use OpenAI for triage
    triage_prompt = f"""Classify this customer support message for ticket routing.

Message: {message}

Provide:
Category: Billing, Refund, Technical, Account, Shipping, or Other
Priority: P1 (urgent), P2 (medium), or P3 (low)
Team: suggested team name

Consider urgency keywords (urgent, asap, emergency) for P1 priority.

Format:
Category: [category]
Priority: [priority]
Team: [team]"""
    
    try:
        response = llm.chat_completion(
            [{"role": "user", "content": triage_prompt}],
            temperature=0.2
        ).strip()
        
        # Parse response
        triage_data = {}
        for line in response.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                triage_data[key.strip().lower()] = value.strip()
        
        category = triage_data.get('category', 'Other')
        priority = triage_data.get('priority', 'P2').upper()
        team = triage_data.get('team', 'General Support')
        
        # Validate priority
        if priority not in ['P1', 'P2', 'P3']:
            priority = 'P2'
            
    except Exception as e:
        logger.error(f"Triage classification failed: {e}, using fallback")
        # Fallback to keyword-based
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in ["billing", "charge", "payment", "invoice"]):
            category, team, priority = "Billing", "Billing Team", "P2"
        elif any(kw in message_lower for kw in ["refund", "return", "money back"]):
            category, team, priority = "Refund", "Billing Team", "P1"
        elif any(kw in message_lower for kw in ["technical", "error", "bug", "crash", "not working"]):
            category, team, priority = "Technical", "Tech Support", "P2"
        elif any(kw in message_lower for kw in ["account", "login", "password", "access"]):
            category, team, priority = "Account", "Account Team", "P2"
        elif any(kw in message_lower for kw in ["ship", "delivery", "tracking", "package"]):
            category, team, priority = "Shipping", "Shipping Team", "P3"
        else:
            category, team, priority = "Other", "General Support", "P3"
        
        if any(kw in message_lower for kw in ["urgent", "asap", "immediately", "emergency"]):
            priority = "P1"
    
    # Create triage
    triage = TicketTriage(
        category=category,
        priority=priority,
        sentiment="neutral",
        routing_team=team,
        tags=["custom_workflow"],
        confidence=0.90,
    )
    
    state["ticket"] = triage
    
    # Create ticket
    ticket_id, ticket_event = ticketing_tool.create_ticket(triage, message, state.get("customer_id"))
    state["trace"].append(ticket_event)
    
    state["trace"].append(TraceEvent.node_end("triage_request"))
    
    return state


def retrieve_knowledge(state: SupportState) -> SupportState:
    """
    Retrieve relevant knowledge.
    
    Fourth step - uses tools to fetch KB articles.
    """
    state["trace"].append(TraceEvent.node_start("retrieve_knowledge"))
    
    message = state["messages"][-1]["content"]
    
    # Retrieve KB articles
    state["trace"].append(TraceEvent.tool_call("kb_tool"))
    articles, kb_event = retrieve_kb_articles(message, top_k=3)
    state["trace"].append(kb_event)
    state["sources"].extend(format_kb_sources(articles))
    
    # Store KB content
    kb_content = "\n".join([f"[{a['id']}] {a['title']}: {a['content']}" for a in articles])
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["kb_content"] = kb_content
    
    state["trace"].append(TraceEvent.tool_result("kb_tool", {"articles": len(articles)}))
    state["trace"].append(TraceEvent.node_end("retrieve_knowledge"))
    
    return state


def draft_reply(state: SupportState) -> SupportState:
    """
    Draft initial reply (agentic node).
    
    Fifth step - LLM generates draft response.
    This demonstrates recursion: draft may need revision.
    """
    state["trace"].append(TraceEvent.node_start("draft_reply"))
    
    # Increment recursion depth
    state["recursion_depth"] = state.get("recursion_depth", 0) + 1
    
    llm = OpenAIProvider()
    message = state["messages"][-1]["content"]
    kb_content = state.get("specialist_results", {}).get("kb_content", "")
    category = state["ticket"].category if state.get("ticket") else "General"
    
    prompt = f"""Draft a customer support reply for this {category} request.

Customer message: {message}

Knowledge base:
{kb_content}

Write a helpful, professional response. Include KB citations if relevant."""
    
    draft = llm.chat_completion([{"role": "user", "content": prompt}], temperature=0.5)
    
    # Store draft
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["draft"] = draft
    
    state["trace"].append(TraceEvent.node_end("draft_reply", {
        "draft_length": len(draft),
        "recursion_depth": state["recursion_depth"]
    }))
    
    return state


def policy_check(state: SupportState) -> SupportState:
    """
    Check draft against policies.
    
    Sixth step - validates draft for policy compliance.
    """
    state["trace"].append(TraceEvent.node_start("policy_check"))
    
    draft = state.get("specialist_results", {}).get("draft", "")
    message = state["messages"][-1]["content"]
    
    # Check for policy violations in draft
    violations = []
    
    # Don't promise refunds without approval
    if "refund" in draft.lower() and "manager" not in draft.lower() and "review" not in draft.lower():
        if any(kw in message.lower() for kw in ["refund", "money back"]):
            violations.append("refund_promise")
    
    # Don't share personal data
    if any(pattern in draft.lower() for pattern in ["password is", "your password", "ssn", "credit card"]):
        violations.append("data_exposure")
    
    # Ensure professional tone
    if any(word in draft.lower() for word in ["stupid", "dumb", "idiot"]):
        violations.append("unprofessional_tone")
    
    # Store policy check result
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["policy_violations"] = violations
    state["specialist_results"]["policy_passed"] = len(violations) == 0
    
    state["trace"].append(TraceEvent.node_end("policy_check", {
        "violations": violations,
        "passed": len(violations) == 0
    }))
    
    return state


def route_after_policy(state: SupportState) -> Literal["revise_draft", "finalize_workflow"]:
    """
    Conditional edge: revise if policy violations, else finalize.
    
    This demonstrates recursion control in custom workflow.
    """
    violations = state.get("specialist_results", {}).get("policy_violations", [])
    recursion_depth = state.get("recursion_depth", 0)
    
    # Check recursion limit (prevents infinite loops)
    if recursion_depth >= 3:
        # Hit recursion limit - proceed even with violations
        state["trace"].append(TraceEvent.node_start("recursion_limit_check"))
        state["trace"].append(TraceEvent.node_end("recursion_limit_check", {
            "reason": "Max recursion depth reached",
            "depth": recursion_depth
        }))
        return "finalize_workflow"
    
    # If violations, revise
    if violations:
        return "revise_draft"
    else:
        return "finalize_workflow"


def revise_draft(state: SupportState) -> SupportState:
    """
    Revise draft to fix policy violations.
    
    This node demonstrates recursion - flows back to policy_check.
    """
    state["trace"].append(TraceEvent.node_start("revise_draft"))
    
    llm = OpenAIProvider()
    draft = state.get("specialist_results", {}).get("draft", "")
    violations = state.get("specialist_results", {}).get("policy_violations", [])
    
    prompt = f"""Revise this customer support draft to fix policy violations.

Original draft:
{draft}

Policy violations found:
{', '.join(violations)}

Guidelines:
- Don't promise refunds without manager approval
- Never share sensitive customer data
- Maintain professional tone
- Be empathetic and helpful

Provide revised draft:"""
    
    revised = llm.chat_completion([{"role": "user", "content": prompt}], temperature=0.4)
    
    # Update draft
    state["specialist_results"]["draft"] = revised
    
    state["trace"].append(TraceEvent.node_end("revise_draft", {
        "violations_fixed": violations
    }))
    
    return state


def finalize_workflow(state: SupportState) -> SupportState:
    """
    Finalize the workflow and prepare outputs.
    
    Last step in the deterministic pipeline.
    """
    state["trace"].append(TraceEvent.node_start("finalize_workflow"))
    
    draft = state.get("specialist_results", {}).get("draft", "Generated response")
    
    # Set final answer
    state["final_answer"] = draft
    
    # Generate agent assist
    state["agent_assist"] = AgentAssistOutput(
        draft_reply=draft,
        case_summary=[
            f"Category: {state['ticket'].category}" if state.get('ticket') else "Unclassified",
            f"Priority: {state['ticket'].priority}" if state.get('ticket') else "P3",
            f"Recursion depth: {state.get('recursion_depth', 0)}",
            f"Policy checks: {'Passed' if state.get('specialist_results', {}).get('policy_passed') else 'Failed'}",
        ],
        next_actions=[
            "Send response to customer",
            "Monitor ticket status",
            "Update ticket with resolution",
        ],
    )
    
    state["trace"].append(TraceEvent.node_end("finalize_workflow", {
        "total_recursions": state.get("recursion_depth", 0)
    }))
    
    return state


def create_custom_workflow_graph() -> StateGraph:
    """
    Create the Custom Workflow pattern graph.
    
    Key concepts demonstrated:
    - Deterministic pipeline (sanitize -> extract -> triage -> retrieve -> draft -> policy -> finalize)
    - Agentic nodes (draft_reply uses LLM)
    - Recursion with limit (draft -> policy -> revise -> policy, max 3 iterations)
    - Reducers (messages append, sources unique merge, trace append)
    - Recursion depth tracking in state
    """
    graph = StateGraph(SupportState)
    
    # Add all nodes
    graph.add_node("sanitize", sanitize_input)
    graph.add_node("extract_entities", extract_entities)
    graph.add_node("triage", triage_request)
    graph.add_node("retrieve_kb", retrieve_knowledge)
    graph.add_node("draft", draft_reply)
    graph.add_node("policy_check", policy_check)
    graph.add_node("revise", revise_draft)
    graph.add_node("finalize", finalize_workflow)
    
    # Set entry point
    graph.set_entry_point("sanitize")
    
    # Deterministic pipeline
    graph.add_edge("sanitize", "extract_entities")
    graph.add_edge("extract_entities", "triage")
    graph.add_edge("triage", "retrieve_kb")
    graph.add_edge("retrieve_kb", "draft")
    graph.add_edge("draft", "policy_check")
    
    # Conditional edge: policy check -> revise or finalize
    graph.add_conditional_edges(
        "policy_check",
        route_after_policy,
        {
            "revise_draft": "revise",
            "finalize_workflow": "finalize",
        }
    )
    
    # Recursion: revise -> policy_check (creates loop)
    graph.add_edge("revise", "policy_check")
    
    # Finalize to END
    graph.add_edge("finalize", END)
    
    return graph
