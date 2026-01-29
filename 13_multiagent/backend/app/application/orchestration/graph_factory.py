"""Graph factory - builds graphs for each pattern."""
from typing import Literal
from langgraph.graph import StateGraph
from app.application.orchestration.patterns.router import create_router_graph
from app.application.orchestration.patterns.subagents import create_subagents_graph
from app.application.orchestration.patterns.handoffs import create_handoffs_graph
from app.application.orchestration.patterns.skills import create_skills_graph
from app.application.orchestration.patterns.custom_workflow import create_custom_workflow_graph
from app.core.logging import get_logger

logger = get_logger(__name__)

PatternType = Literal["router", "subagents", "handoffs", "skills", "custom_workflow"]


class GraphFactory:
    """Factory for creating LangGraph workflows based on pattern selection."""
    
    @staticmethod
    def create(pattern: PatternType) -> StateGraph:
        """
        Create a compiled graph for the specified pattern.
        
        Args:
            pattern: The pattern type to create
            
        Returns:
            Compiled StateGraph ready for execution
            
        Raises:
            ValueError: If pattern is not recognized
        """
        logger.info(f"Creating graph for pattern: {pattern}")
        
        if pattern == "router":
            graph = create_router_graph()
        elif pattern == "subagents":
            graph = create_subagents_graph()
        elif pattern == "handoffs":
            graph = create_handoffs_graph()
        elif pattern == "skills":
            graph = create_skills_graph()
        elif pattern == "custom_workflow":
            graph = create_custom_workflow_graph()
        else:
            raise ValueError(f"Unknown pattern: {pattern}")
        
        # Compile the graph
        compiled = graph.compile()
        logger.info(f"Graph compiled successfully for pattern: {pattern}")
        
        return compiled
    
    @staticmethod
    def get_available_patterns() -> list[dict]:
        """
        Get list of available patterns with descriptions.
        
        Returns:
            List of pattern metadata dicts
        """
        return [
            {
                "id": "router",
                "name": "Router Pattern",
                "description": "Conditional routing to specialist agents with fan-out for mixed intents",
                "concepts": ["Conditional edges", "Send (fan-out)", "Parallel execution", "Synthesis"],
            },
            {
                "id": "subagents",
                "name": "Subagents Pattern",
                "description": "Orchestrator calls specialized subagents as tools based on LLM decision",
                "concepts": ["Tool-calling", "Subagent delegation", "Orchestration", "Dynamic routing"],
            },
            {
                "id": "handoffs",
                "name": "Handoffs Pattern",
                "description": "State-driven agent switching with policy-based escalation",
                "concepts": ["State switching", "active_agent", "Handoff events", "Policy triggers"],
            },
            {
                "id": "skills",
                "name": "Skills Pattern",
                "description": "On-demand context loading - skills activated only when needed",
                "concepts": ["Lazy loading", "Context fetching", "Skill assessment", "Efficient execution"],
            },
            {
                "id": "custom_workflow",
                "name": "Custom Workflow Pattern",
                "description": "Deterministic pipeline with agentic nodes and recursion control",
                "concepts": ["Deterministic flow", "Recursion limit", "Revise loop", "Policy validation"],
            },
        ]
