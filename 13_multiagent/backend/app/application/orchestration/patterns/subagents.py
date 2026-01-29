"""Subagents pattern - orchestrator calls subagents as tools."""
from langgraph.graph import StateGraph, END
from app.domain.state import SupportState, AgentAssistOutput
from app.domain.events import TraceEvent
from app.domain.ticket import TicketTriage
from app.infrastructure.llm.openai_provider import OpenAIProvider
from app.infrastructure.tools.kb_tool import retrieve_kb_articles, format_kb_sources
from app.infrastructure.tools.ticketing_tool import ticketing_tool
from app.core.logging import get_logger

logger = get_logger(__name__)


# Subagent implementations
class TriageSubagent:
    """Subagent for ticket triage using OpenAI."""
    
    @staticmethod
    def execute(message: str) -> TicketTriage:
        """Classify and triage the ticket using OpenAI."""
        llm = OpenAIProvider()
        
        triage_prompt = f"""Analyze this customer support message and provide triage classification.

Customer message: {message}

Provide the following in a structured format:
1. Category: Billing, Technical, Account, Shipping, Refund, or Other
2. Priority: P1 (urgent/critical), P2 (medium), or P3 (low)
3. Sentiment: positive, neutral, or negative
4. Routing Team: suggest the best team to handle this
5. Tags: 2-3 relevant tags

Format your response as:
Category: [category]
Priority: [priority]
Sentiment: [sentiment]
Team: [team name]
Tags: [tag1, tag2, tag3]"""
        
        try:
            response = llm.chat_completion(
                [{"role": "user", "content": triage_prompt}],
                temperature=0.2
            )
            
            # Parse the response
            lines = response.strip().split('\n')
            triage_data = {}
            for line in lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    triage_data[key.strip().lower()] = value.strip()
            
            # Extract and validate values
            category = triage_data.get('category', 'Other')
            priority = triage_data.get('priority', 'P2').upper()
            sentiment = triage_data.get('sentiment', 'neutral').lower()
            team = triage_data.get('team', 'General Support')
            tags_str = triage_data.get('tags', '')
            tags = [t.strip() for t in tags_str.replace('[', '').replace(']', '').split(',') if t.strip()]
            
            # Validate priority
            if priority not in ['P1', 'P2', 'P3']:
                priority = 'P2'
            
            # Validate sentiment
            if sentiment not in ['positive', 'neutral', 'negative']:
                sentiment = 'neutral'
            
            logger.info(f"Triage completed: {category}/{priority}, sentiment: {sentiment}")
            
            return TicketTriage(
                category=category,
                priority=priority,
                sentiment=sentiment,
                routing_team=team,
                tags=tags,
                confidence=0.90,
            )
            
        except Exception as e:
            logger.error(f"Triage classification failed: {e}, using fallback")
            # Fallback to simple keyword-based classification
            message_lower = message.lower()
            
            if any(kw in message_lower for kw in ["billing", "charge", "refund"]):
                category, team = "Billing", "Billing Team"
            elif any(kw in message_lower for kw in ["technical", "error", "bug"]):
                category, team = "Technical", "Tech Support"
            elif any(kw in message_lower for kw in ["account", "login", "password"]):
                category, team = "Account", "Account Team"
            elif any(kw in message_lower for kw in ["ship", "delivery", "tracking"]):
                category, team = "Shipping", "Shipping Team"
            else:
                category, team = "Other", "General Support"
            
            priority = "P1" if any(kw in message_lower for kw in ["urgent", "asap", "immediately"]) else "P2"
            sentiment = "negative" if any(kw in message_lower for kw in ["angry", "frustrated"]) else "neutral"
            
            return TicketTriage(
                category=category,
                priority=priority,
                sentiment=sentiment,
                routing_team=team,
                tags=["fallback_triage"],
                confidence=0.70,
            )


class KnowledgeSubagent:
    """Subagent for knowledge retrieval and grounded answering."""
    
    @staticmethod
    def execute(message: str) -> tuple[str, list[str]]:
        """Retrieve KB and generate grounded answer."""
        llm = OpenAIProvider()
        
        # Retrieve relevant articles
        articles, _ = retrieve_kb_articles(message, top_k=3)
        sources = format_kb_sources(articles)
        
        # Generate grounded answer
        kb_context = "\n".join([
            f"[{a['id']}] {a['title']}: {a['content']}"
            for a in articles
        ])
        
        prompt = f"""Answer this customer question using ONLY the provided knowledge base articles.
Include article IDs as citations.

Question: {message}

Knowledge Base:
{kb_context}

Provide a helpful, accurate answer with citations."""
        
        answer = llm.chat_completion([{"role": "user", "content": prompt}], temperature=0.3)
        
        return answer, sources


class AgentAssistSubagent:
    """Subagent for generating agent assist outputs."""
    
    @staticmethod
    def execute(message: str, category: str, sources: list[str]) -> AgentAssistOutput:
        """Generate draft reply, summary, and next actions."""
        llm = OpenAIProvider()
        
        # Generate draft reply
        draft_prompt = f"""Generate a professional, policy-compliant draft reply for a {category} support ticket.

Customer message: {message}

Available sources: {', '.join(sources[:3]) if sources else 'General knowledge'}

Write a helpful, empathetic draft reply."""
        
        draft_reply = llm.chat_completion([{"role": "user", "content": draft_prompt}], temperature=0.5)
        
        # Generate case summary
        summary_prompt = f"""Summarize this support case in 2-3 bullet points:

{message}

Category: {category}"""
        
        summary_text = llm.chat_completion([{"role": "user", "content": summary_prompt}], temperature=0.3)
        summary_points = [s.strip() for s in summary_text.split('\n') if s.strip() and (s.strip().startswith('-') or s.strip().startswith('•'))]
        if not summary_points:
            summary_points = [summary_text[:100]]
        
        # Generate next actions
        next_actions = [
            "Verify customer identity",
            f"Review {category.lower()} policy guidelines",
            "Check for similar recent cases",
            "Escalate if needed based on customer tier",
        ]
        
        return AgentAssistOutput(
            draft_reply=draft_reply,
            case_summary=summary_points[:3],
            next_actions=next_actions,
        )


def orchestrator_node(state: SupportState) -> SupportState:
    """
    Orchestrator node that decides which subagents to call.
    
    This demonstrates the Subagents pattern where an LLM-based orchestrator
    decides which specialized subagents to invoke based on the request.
    """
    state["trace"].append(TraceEvent.node_start("orchestrator"))
    
    message = state["messages"][-1]["content"]
    llm = OpenAIProvider()
    
    # LLM decides which subagents to call
    decision_prompt = f"""You are an orchestrator for a customer support system.
Decide which subagents to call for this customer message.

Available subagents:
- triage: Classify ticket category, priority, sentiment
- knowledge: Retrieve relevant KB articles and provide grounded answer
- agent_assist: Generate draft reply, case summary, and next actions

Customer message: {message}

Which subagents should be called? Respond with a comma-separated list.
For most cases, call all three. Format: triage,knowledge,agent_assist"""
    
    decision = llm.chat_completion([{"role": "user", "content": decision_prompt}], temperature=0.2)
    subagents_to_call = [s.strip() for s in decision.lower().split(",")]
    
    state["trace"].append(TraceEvent.node_end("orchestrator", {"subagents": subagents_to_call}))
    
    # Call triage subagent
    if "triage" in subagents_to_call:
        state["trace"].append(TraceEvent.tool_call("triage_subagent", {"message_preview": message[:50]}))
        triage_result = TriageSubagent.execute(message)
        state["ticket"] = triage_result
        state["trace"].append(TraceEvent.tool_result("triage_subagent", {
            "category": triage_result.category,
            "priority": triage_result.priority,
        }))
        
        # Create ticket in system
        ticket_id, ticket_event = ticketing_tool.create_ticket(triage_result, message, state.get("customer_id"))
        state["trace"].append(ticket_event)
    
    # Call knowledge subagent
    if "knowledge" in subagents_to_call:
        state["trace"].append(TraceEvent.tool_call("knowledge_subagent"))
        answer, sources = KnowledgeSubagent.execute(message)
        state["final_answer"] = answer
        state["sources"].extend(sources)
        state["trace"].append(TraceEvent.tool_result("knowledge_subagent", {
            "sources_count": len(sources)
        }))
    
    # Call agent assist subagent
    if "agent_assist" in subagents_to_call:
        state["trace"].append(TraceEvent.tool_call("agent_assist_subagent"))
        category = state["ticket"].category if state.get("ticket") else "General"
        assist_result = AgentAssistSubagent.execute(message, category, state.get("sources", []))
        state["agent_assist"] = assist_result
        state["trace"].append(TraceEvent.tool_result("agent_assist_subagent"))
    
    return state


def create_subagents_graph() -> StateGraph:
    """
    Create the Subagents pattern graph.
    
    Key concepts demonstrated:
    - Single orchestrator node
    - Subagents called as tools/functions
    - LLM decides which subagents to invoke
    - Trace shows subagent tool calls
    """
    graph = StateGraph(SupportState)
    
    # Single orchestrator node
    graph.add_node("orchestrator", orchestrator_node)
    
    # Set entry and exit
    graph.set_entry_point("orchestrator")
    graph.add_edge("orchestrator", END)
    
    return graph
