"""Mock customer context retrieval tool."""
from typing import Dict, Any, Optional
from app.domain.events import TraceEvent


# Mock customer database
CUSTOMER_DB = {
    "CUST-001": {
        "id": "CUST-001",
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "plan": "Premium",
        "sla_tier": "Gold",
        "account_status": "active",
        "lifetime_value": 5420.00,
        "last_order": {
            "id": "ORD-9871",
            "date": "2026-01-15",
            "status": "delivered",
            "total": 89.99,
        },
        "support_history": {
            "total_tickets": 3,
            "avg_resolution_time": "2.5 hours",
            "satisfaction_score": 4.8,
        },
    },
    "CUST-002": {
        "id": "CUST-002",
        "name": "Bob Smith",
        "email": "bob@example.com",
        "plan": "Basic",
        "sla_tier": "Silver",
        "account_status": "active",
        "lifetime_value": 320.00,
        "last_order": {
            "id": "ORD-8765",
            "date": "2026-01-20",
            "status": "shipped",
            "total": 45.00,
        },
        "support_history": {
            "total_tickets": 1,
            "avg_resolution_time": "4 hours",
            "satisfaction_score": 4.2,
        },
    },
    "CUST-003": {
        "id": "CUST-003",
        "name": "Carol Davis",
        "email": "carol@example.com",
        "plan": "Enterprise",
        "sla_tier": "Platinum",
        "account_status": "active",
        "lifetime_value": 25000.00,
        "last_order": {
            "id": "ORD-9999",
            "date": "2026-01-25",
            "status": "processing",
            "total": 1200.00,
        },
        "support_history": {
            "total_tickets": 12,
            "avg_resolution_time": "1 hour",
            "satisfaction_score": 4.9,
        },
    },
}


def get_customer_context(customer_id: Optional[str]) -> tuple[Optional[Dict[str, Any]], TraceEvent]:
    """
    Retrieve customer context from mock database.
    
    Args:
        customer_id: Customer identifier
        
    Returns:
        Tuple of (customer context dict, trace event)
    """
    if not customer_id:
        # Return default/anonymous customer context
        context = {
            "id": "ANONYMOUS",
            "plan": "Free",
            "sla_tier": "Standard",
            "account_status": "guest",
        }
        trace_event = TraceEvent.tool_result(
            "customer_tool",
            {"action": "get_customer", "customer_id": "anonymous"}
        )
        return context, trace_event
    
    customer = CUSTOMER_DB.get(customer_id)
    
    if customer:
        trace_event = TraceEvent.tool_result(
            "customer_tool",
            {
                "action": "get_customer",
                "customer_id": customer_id,
                "plan": customer["plan"],
                "sla_tier": customer["sla_tier"],
            }
        )
    else:
        trace_event = TraceEvent.tool_result(
            "customer_tool",
            {"action": "customer_not_found", "customer_id": customer_id}
        )
    
    return customer, trace_event


def get_order_status(order_id: str) -> tuple[Optional[Dict[str, Any]], TraceEvent]:
    """
    Get order status (mock).
    
    Args:
        order_id: Order identifier
        
    Returns:
        Tuple of (order details, trace event)
    """
    # Search all customers for the order
    for customer in CUSTOMER_DB.values():
        if customer["last_order"]["id"] == order_id:
            order = customer["last_order"]
            trace_event = TraceEvent.tool_result(
                "customer_tool",
                {
                    "action": "get_order",
                    "order_id": order_id,
                    "status": order["status"],
                }
            )
            return order, trace_event
    
    trace_event = TraceEvent.tool_result(
        "customer_tool",
        {"action": "order_not_found", "order_id": order_id}
    )
    return None, trace_event


def format_customer_context(customer: Optional[Dict[str, Any]]) -> str:
    """Format customer context for LLM."""
    if not customer or customer.get("id") == "ANONYMOUS":
        return "Anonymous customer (no account information available)"
    
    return f"""
Customer: {customer['name']} ({customer['email']})
Plan: {customer['plan']} | SLA Tier: {customer['sla_tier']}
Account Status: {customer['account_status']}
Lifetime Value: ${customer['lifetime_value']:.2f}

Last Order: {customer['last_order']['id']}
- Date: {customer['last_order']['date']}
- Status: {customer['last_order']['status']}
- Total: ${customer['last_order']['total']:.2f}

Support History:
- Total Tickets: {customer['support_history']['total_tickets']}
- Avg Resolution: {customer['support_history']['avg_resolution_time']}
- Satisfaction: {customer['support_history']['satisfaction_score']}/5.0
""".strip()
