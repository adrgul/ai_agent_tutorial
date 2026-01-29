"""Mock ticketing system tool."""
from typing import Dict, Any, Optional
from app.domain.ticket import TicketTriage
from app.domain.events import TraceEvent
from app.core.logging import get_logger

logger = get_logger(__name__)


class TicketingTool:
    """Mock integration with ticketing system (e.g., Zendesk, Intercom)."""
    
    def __init__(self):
        # Mock ticket storage
        self.tickets: Dict[str, Dict[str, Any]] = {}
        self.ticket_counter = 1000
    
    def create_ticket(self, triage: TicketTriage, message: str, customer_id: Optional[str] = None) -> tuple[str, TraceEvent]:
        """
        Create a new ticket in the mock system.
        
        Args:
            triage: Ticket triage information
            message: Original customer message
            customer_id: Optional customer identifier
            
        Returns:
            Tuple of (ticket_id, trace_event)
        """
        ticket_id = f"TKT-{self.ticket_counter}"
        self.ticket_counter += 1
        
        ticket = {
            "id": ticket_id,
            "customer_id": customer_id,
            "message": message,
            "category": triage.category,
            "priority": triage.priority,
            "sentiment": triage.sentiment,
            "routing_team": triage.routing_team,
            "assignee_group": triage.assignee_group,
            "tags": triage.tags,
            "status": "open",
            "created_at": "2026-01-28T12:00:00Z",
        }
        
        self.tickets[ticket_id] = ticket
        logger.info(f"Created ticket {ticket_id} - {triage.category}/{triage.priority}")
        
        trace_event = TraceEvent.tool_result(
            "ticketing_tool",
            {
                "action": "create_ticket",
                "ticket_id": ticket_id,
                "category": triage.category,
                "priority": triage.priority,
            }
        )
        
        return ticket_id, trace_event
    
    def update_ticket(self, ticket_id: str, updates: Dict[str, Any]) -> TraceEvent:
        """
        Update an existing ticket.
        
        Args:
            ticket_id: Ticket identifier
            updates: Fields to update
            
        Returns:
            Trace event
        """
        if ticket_id not in self.tickets:
            logger.warning(f"Ticket {ticket_id} not found")
            return TraceEvent.tool_result("ticketing_tool", {"action": "update_failed", "ticket_id": ticket_id})
        
        self.tickets[ticket_id].update(updates)
        logger.info(f"Updated ticket {ticket_id}: {updates}")
        
        return TraceEvent.tool_result(
            "ticketing_tool",
            {
                "action": "update_ticket",
                "ticket_id": ticket_id,
                "updates": list(updates.keys()),
            }
        )
    
    def assign_ticket(self, ticket_id: str, assignee: str, team: str) -> TraceEvent:
        """
        Assign ticket to a team/agent.
        
        Args:
            ticket_id: Ticket identifier
            assignee: Agent or team name
            team: Team name
            
        Returns:
            Trace event
        """
        return self.update_ticket(
            ticket_id,
            {
                "assignee": assignee,
                "routing_team": team,
                "status": "assigned",
            }
        )
    
    def add_tags(self, ticket_id: str, tags: list[str]) -> TraceEvent:
        """
        Add tags to a ticket.
        
        Args:
            ticket_id: Ticket identifier
            tags: Tags to add
            
        Returns:
            Trace event
        """
        if ticket_id in self.tickets:
            existing_tags = set(self.tickets[ticket_id].get("tags", []))
            existing_tags.update(tags)
            self.tickets[ticket_id]["tags"] = list(existing_tags)
        
        return TraceEvent.tool_result(
            "ticketing_tool",
            {
                "action": "add_tags",
                "ticket_id": ticket_id,
                "tags": tags,
            }
        )
    
    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """Get ticket details."""
        return self.tickets.get(ticket_id)


# Global ticketing tool instance
ticketing_tool = TicketingTool()
