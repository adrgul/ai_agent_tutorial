from langgraph.graph import StateGraph, END

from src.application.nodes import AgentNodes
from src.domain.state import AgentState


class AgentGraph:
    """
    Builds and compiles the LangGraph StateGraph for the agent's workflow.
    """

    def __init__(self, agent_nodes: AgentNodes):
        self.agent_nodes = agent_nodes
        self.workflow = StateGraph(AgentState)

    def build(self):
        """
        Defines the graph's nodes and edges, then compiles it.
        """
        # Add nodes
        self.workflow.add_node("call_llm", self.agent_nodes.call_llm)
        self.workflow.add_node("get_weather_info", self.agent_nodes.get_weather_info)

        # Set entry point
        self.workflow.set_entry_point("call_llm")

        # Define edges
        self.workflow.add_conditional_edges(
            "call_llm",
            self.agent_nodes.decide_next_step,
            {
                "call_tool_weather": "get_weather_info",
                "end_response": END,
            },
        )
        self.workflow.add_edge("get_weather_info", END)

        return self.workflow.compile()
