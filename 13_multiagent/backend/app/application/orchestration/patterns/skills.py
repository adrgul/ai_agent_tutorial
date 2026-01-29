"""Skills pattern - on-demand context loading."""
from langgraph.graph import StateGraph, END
from app.domain.state import SupportState, AgentAssistOutput
from app.domain.events import TraceEvent
from app.domain.ticket import TicketTriage
from app.infrastructure.llm.openai_provider import OpenAIProvider
from app.infrastructure.tools.kb_tool import retrieve_kb_articles, format_kb_sources
from app.infrastructure.tools.customer_tool import get_customer_context, format_customer_context
from app.infrastructure.tools.ticketing_tool import ticketing_tool
from app.core.logging import get_logger

logger = get_logger(__name__)


def assess_needs(state: SupportState) -> SupportState:
    """
    Assess which skills/context are needed using OpenAI.
    
    This node analyzes the request and decides which skills to activate.
    """
    state["trace"].append(TraceEvent.node_start("assess_needs"))
    
    message = state["messages"][-1]["content"]
    llm = OpenAIProvider()
    
    assessment_prompt = f"""Analyze this customer support message and determine which skills/context are needed.

Available skills:
- kb_skill: Knowledge base retrieval for policy questions, how-to guides
- customer_skill: Customer account data, order history, tier information
- ticketing_skill: Create and track support tickets

Customer message: {message}

Which skills are needed? Respond with a comma-separated list.
Examples: "kb_skill,customer_skill" or "kb_skill,ticketing_skill" or "kb_skill,customer_skill,ticketing_skill"

Skills needed:"""
    
    try:
        response = llm.chat_completion(
            [{"role": "user", "content": assessment_prompt}],
            temperature=0.2
        ).strip().lower()
        
        # Parse the response
        skills_list = [s.strip() for s in response.split(',')]
        
        # Validate skills
        valid_skills = {"kb_skill", "customer_skill", "ticketing_skill"}
        needs = {
            skill: (skill in skills_list)
            for skill in valid_skills
        }
        
        # Ensure at least one skill is activated
        if not any(needs.values()):
            needs = {"kb_skill": True, "customer_skill": False, "ticketing_skill": True}
        
    except Exception as e:
        logger.error(f"Needs assessment failed: {e}, using default skills")
        # Default to all skills if uncertain
        needs = {"kb_skill": True, "customer_skill": True, "ticketing_skill": True}
    
    # Store assessment
    state["routing_decision"] = ",".join([k for k, v in needs.items() if v])
    
    state["trace"].append(TraceEvent.node_end("assess_needs", {"skills_needed": state["routing_decision"]}))
    
    return state


def kb_skill(state: SupportState) -> SupportState:
    """
    KB skill: Load knowledge base context.
    
    This demonstrates on-demand context loading - KB is only retrieved if needed.
    """
    state["trace"].append(TraceEvent.node_start("kb_skill"))
    
    message = state["messages"][-1]["content"]
    
    # Retrieve KB articles
    state["trace"].append(TraceEvent.tool_call("kb_tool", {"query": message[:50]}))
    articles, kb_event = retrieve_kb_articles(message, top_k=3)
    state["trace"].append(kb_event)
    state["sources"].extend(format_kb_sources(articles))
    
    # Store KB content in state for later synthesis
    kb_content = "\n".join([
        f"[{a['id']}] {a['title']}: {a['content']}"
        for a in articles
    ])
    
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["kb_skill"] = kb_content
    
    state["trace"].append(TraceEvent.tool_result("kb_tool", {"articles_count": len(articles)}))
    state["trace"].append(TraceEvent.node_end("kb_skill"))
    
    return state


def customer_skill(state: SupportState) -> SupportState:
    """
    Customer skill: Load customer context.
    
    This demonstrates on-demand context loading - customer data is only fetched if needed.
    """
    state["trace"].append(TraceEvent.node_start("customer_skill"))
    
    # Get customer context
    state["trace"].append(TraceEvent.tool_call("customer_tool", {"customer_id": state.get("customer_id", "anonymous")}))
    customer, customer_event = get_customer_context(state.get("customer_id"))
    state["trace"].append(customer_event)
    
    # Store customer context
    if customer:
        state["customer_tier"] = customer.get("sla_tier", "Standard")
        customer_info = format_customer_context(customer)
    else:
        customer_info = "Anonymous customer (no account information)"
    
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["customer_skill"] = customer_info
    
    state["trace"].append(TraceEvent.tool_result("customer_tool"))
    state["trace"].append(TraceEvent.node_end("customer_skill"))
    
    return state


def ticketing_skill(state: SupportState) -> SupportState:
    """
    Ticketing skill: Create and manage ticket using OpenAI for classification.
    
    This demonstrates on-demand skill activation for ticket management.
    """
    state["trace"].append(TraceEvent.node_start("ticketing_skill"))
    
    message = state["messages"][-1]["content"]
    llm = OpenAIProvider()
    
    # Use OpenAI for triage
    triage_prompt = f"""Classify this customer support message for ticket creation.

Message: {message}

Provide:
Category: Billing, Technical, Account, Shipping, or Other
Priority: P1, P2, or P3
Team: suggested team name

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
        lines = {line.split(':')[0].strip().lower(): line.split(':', 1)[1].strip() 
                 for line in response.split('\n') if ':' in line}
        
        category = lines.get('category', 'Other')
        priority = lines.get('priority', 'P2').upper()
        team = lines.get('team', 'General Support')
        
    except Exception as e:
        logger.warning(f"Ticketing classification failed: {e}, using fallback")
        # Fallback to keyword-based
        message_lower = message.lower()
        if any(kw in message_lower for kw in ["billing", "charge", "refund"]):
            category, team = "Billing", "Billing Team"
        elif any(kw in message_lower for kw in ["technical", "error"]):
            category, team = "Technical", "Tech Support"
        elif any(kw in message_lower for kw in ["account", "login"]):
            category, team = "Account", "Account Team"
        elif any(kw in message_lower for kw in ["ship", "delivery"]):
            category, team = "Shipping", "Shipping Team"
        else:
            category, team = "Other", "General Support"
        priority = "P2"
    
    # Create triage
    triage = TicketTriage(
        category=category,
        priority=priority,
        sentiment="neutral",
        routing_team=team,
        tags=["skills_pattern"],
        confidence=0.85,
    )
    
    state["ticket"] = triage
    
    # Create ticket
    state["trace"].append(TraceEvent.tool_call("ticketing_tool"))
    ticket_id, ticket_event = ticketing_tool.create_ticket(triage, message, state.get("customer_id"))
    state["trace"].append(ticket_event)
    
    if not state.get("specialist_results"):
        state["specialist_results"] = {}
    state["specialist_results"]["ticketing_skill"] = f"Ticket {ticket_id} created - {category}/{triage.priority}"
    
    state["trace"].append(TraceEvent.tool_result("ticketing_tool", {"ticket_id": ticket_id}))
    state["trace"].append(TraceEvent.node_end("ticketing_skill"))
    
    return state


def synthesize_with_skills(state: SupportState) -> SupportState:
    """
    Synthesize final response using loaded skills/context.
    
    This node demonstrates how context from skills is combined to generate response.
    """
    state["trace"].append(TraceEvent.node_start("synthesize_with_skills"))
    
    llm = OpenAIProvider()
    message = state["messages"][-1]["content"]
    
    # Gather all skill outputs
    skills_used = state.get("specialist_results", {})
    
    # Build context from skills
    context_parts = []
    
    if "kb_skill" in skills_used:
        context_parts.append(f"Knowledge Base:\n{skills_used['kb_skill']}")
    
    if "customer_skill" in skills_used:
        context_parts.append(f"Customer Context:\n{skills_used['customer_skill']}")
    
    if "ticketing_skill" in skills_used:
        context_parts.append(f"Ticket Status:\n{skills_used['ticketing_skill']}")
    
    context = "\n\n".join(context_parts) if context_parts else "No additional context loaded"
    
    # Generate response using skills
    prompt = f"""You are a customer support agent with access to skills-based context.

Customer question: {message}

Available Context:
{context}

Provide a helpful, accurate response using the loaded context. Include citations if using KB articles."""
    
    answer = llm.chat_completion([{"role": "user", "content": prompt}], temperature=0.4)
    state["final_answer"] = answer
    
    # Generate agent assist
    state["agent_assist"] = AgentAssistOutput(
        draft_reply=answer,
        case_summary=[
            f"Skills used: {', '.join(skills_used.keys())}",
            f"Category: {state['ticket'].category}" if state.get('ticket') else "No ticket",
            f"Context loaded on-demand",
        ],
        next_actions=[
            "Verify response accuracy",
            "Check if additional skills needed",
            "Monitor customer satisfaction",
        ],
    )
    
    state["trace"].append(TraceEvent.node_end("synthesize_with_skills", {
        "skills_used": list(skills_used.keys())
    }))
    
    return state


def create_skills_graph() -> StateGraph:
    """
    Create the Skills pattern graph.
    
    Key concepts demonstrated:
    - On-demand context loading (skills only activated when needed)
    - Assessment node decides which skills to use
    - Tool calls for each skill clearly visible in trace
    - Synthesis uses only the loaded context
    """
    graph = StateGraph(SupportState)
    
    # Add nodes
    graph.add_node("assess_needs", assess_needs)
    graph.add_node("kb_skill", kb_skill)
    graph.add_node("customer_skill", customer_skill)
    graph.add_node("ticketing_skill", ticketing_skill)
    graph.add_node("synthesize", synthesize_with_skills)
    
    # Set entry point
    graph.set_entry_point("assess_needs")
    
    # Simple linear flow for demo (in production, this would be conditional)
    # All skills are executed in sequence if needed
    graph.add_edge("assess_needs", "kb_skill")
    graph.add_edge("kb_skill", "customer_skill")
    graph.add_edge("customer_skill", "ticketing_skill")
    graph.add_edge("ticketing_skill", "synthesize")
    graph.add_edge("synthesize", END)
    
    return graph
