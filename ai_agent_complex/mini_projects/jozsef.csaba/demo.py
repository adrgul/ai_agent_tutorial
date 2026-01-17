#!/usr/bin/env python
"""Demo script for Customer Service Triage Agent.

This script demonstrates the complete workflow with sample tickets.
"""

import json
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from app.core.config import get_settings
from app.core.dependencies import get_embedding_service, get_vector_store, initialize_knowledge_base
from app.models.schemas import TicketInput
from app.workflows.langgraph_workflow import TriageWorkflow

console = Console()


def print_section(title: str, content: str = None):
    """Print a formatted section."""
    if content:
        console.print(Panel(content, title=title, border_style="blue"))
    else:
        console.print(f"\n[bold blue]{title}[/bold blue]\n")


def format_ticket(ticket: TicketInput) -> str:
    """Format ticket for display."""
    return f"""
From: {ticket.customer_name} <{ticket.customer_email}>
Subject: {ticket.subject}

{ticket.message}
    """.strip()


def format_response(response) -> None:
    """Format and print the response."""
    # Triage section
    triage_table = Table(title="Triage Classification")
    triage_table.add_column("Field", style="cyan")
    triage_table.add_column("Value", style="green")

    triage = response.triage
    triage_table.add_row("Category", triage.category)
    triage_table.add_row("Subcategory", triage.subcategory)
    triage_table.add_row("Priority", triage.priority.value)
    triage_table.add_row("SLA (hours)", str(triage.sla_hours))
    triage_table.add_row("Team", triage.suggested_team)
    triage_table.add_row("Sentiment", triage.sentiment.value)
    triage_table.add_row("Confidence", f"{triage.confidence:.2%}")

    console.print(triage_table)
    console.print()

    # Answer draft
    draft = response.answer_draft
    draft_text = f"{draft.greeting}\n\n{draft.body}\n\n{draft.closing}"
    print_section("Generated Response Draft", draft_text)

    # Citations
    if response.citations:
        citations_table = Table(title="Knowledge Base Citations")
        citations_table.add_column("Doc ID", style="cyan")
        citations_table.add_column("Title", style="yellow")
        citations_table.add_column("Score", style="green")

        for citation in response.citations:
            citations_table.add_row(
                citation.doc_id,
                citation.title,
                f"{citation.score:.2%}"
            )

        console.print(citations_table)
        console.print()

    # Policy check
    policy = response.policy_check
    policy_status = "✅ PASSED" if policy.compliance == "passed" else "⚠️ WARNING"
    policy_text = f"""
Status: {policy_status}
Refund Promise: {'Yes' if policy.refund_promise else 'No'}
SLA Mentioned: {'Yes' if policy.sla_mentioned else 'No'}
Escalation Needed: {'Yes' if policy.escalation_needed else 'No'}
Warnings: {', '.join(policy.warnings) if policy.warnings else 'None'}
    """.strip()

    print_section("Policy Check", policy_text)


def main():
    """Run demo."""
    console.print("\n[bold magenta]Customer Service Triage Agent - Demo[/bold magenta]\n")

    # Initialize
    console.print("[yellow]Initializing system...[/yellow]")

    try:
        settings = get_settings()
        initialize_knowledge_base()

        vector_store = get_vector_store(settings)
        embedding_service = get_embedding_service(settings)
        workflow = TriageWorkflow(settings, vector_store, embedding_service)

        console.print(f"[green]✓ System initialized[/green]")
        console.print(f"[green]✓ Knowledge base loaded: {vector_store.num_documents} documents[/green]\n")
    except Exception as e:
        console.print(f"[red]✗ Initialization failed: {e}[/red]")
        console.print("[yellow]Make sure you have set OPENAI_API_KEY in .env file[/yellow]")
        return

    # Sample tickets
    tickets = [
        TicketInput(
            customer_name="John Doe",
            customer_email="john.doe@example.com",
            subject="Duplicate charge on my invoice",
            message="I noticed I was charged twice for the same transaction on December 5th. The amount is $49.99. Can you please help me get a refund? This is really frustrating.",
        ),
        TicketInput(
            customer_name="Jane Smith",
            customer_email="jane.smith@example.com",
            subject="API timeout errors",
            message="I'm getting TIMEOUT-500 errors when calling your API. It's been happening for the past hour and affecting our production system. Please help urgently!",
        ),
        TicketInput(
            customer_name="Bob Johnson",
            customer_email="bob.johnson@example.com",
            subject="Password reset not working",
            message="I tried to reset my password but I'm not receiving the email. I've checked my spam folder. Can you help?",
        ),
    ]

    # Process each ticket
    for idx, ticket in enumerate(tickets, 1):
        console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
        console.print(f"[bold cyan]Demo {idx}/{len(tickets)}[/bold cyan]")
        console.print(f"[bold cyan]{'='*80}[/bold cyan]\n")

        # Show ticket
        print_section("Incoming Ticket", format_ticket(ticket))

        # Process
        console.print("[yellow]Processing ticket through workflow...[/yellow]\n")

        try:
            response = workflow.process_ticket(ticket)

            # Show results
            console.print(f"[green]✓ Ticket processed: {response.ticket_id}[/green]\n")
            format_response(response)

        except Exception as e:
            console.print(f"[red]✗ Error processing ticket: {e}[/red]")
            continue

        # Pause between demos
        if idx < len(tickets):
            input("\n[dim]Press Enter to continue to next demo...[/dim]\n")

    console.print("\n[bold green]Demo completed![/bold green]")
    console.print("\nTo try the API, run:")
    console.print("[cyan]python app/main.py[/cyan]")
    console.print("Then visit: [link]http://localhost:8000/docs[/link]\n")


if __name__ == "__main__":
    try:
        from rich import print as rprint
        main()
    except ImportError:
        print("This demo requires 'rich' library. Install it with:")
        print("pip install rich")
    except KeyboardInterrupt:
        console.print("\n[yellow]Demo interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
