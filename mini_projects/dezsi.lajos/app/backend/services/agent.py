from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
import json

from domain.models import Analysis, TriageDecision, AnswerDraft, TicketOutput
from domain.interfaces import ILLMClient, IVectorDBClient

class AgentState(TypedDict):
    messages: List[BaseMessage]
    analysis: Dict[str, Any]
    triage: Dict[str, Any]
    context: List[str]
    draft: Dict[str, Any]
    final_output: Dict[str, Any]

class TriageAgent:
    def __init__(self, llm_client: ILLMClient, vector_db: IVectorDBClient):
        self.llm = llm_client
        self.vector_db = vector_db
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        workflow.add_node("analyze_intent", self._analyze_intent)
        workflow.add_node("triage_ticket", self._triage_ticket)
        workflow.add_node("retrieve_context", self._retrieve_context)
        workflow.add_node("draft_response", self._draft_response)
        workflow.add_node("create_output", self._create_output)

        workflow.set_entry_point("analyze_intent")
        
        workflow.add_edge("analyze_intent", "triage_ticket")
        workflow.add_edge("triage_ticket", "retrieve_context")
        workflow.add_edge("retrieve_context", "draft_response")
        workflow.add_edge("draft_response", "create_output")
        workflow.add_edge("create_output", END)

        return workflow.compile()

    async def _analyze_intent(self, state: AgentState):
        messages = state["messages"]
        last_message = messages[-1].content
        prompt = f"""Analyze the following support ticket message and extract the summary, intent, and complexity.
        Message: {last_message}
        """
        analysis = await self.llm.generate_structured(prompt, Analysis)
        return {"analysis": analysis.model_dump()}

    async def _triage_ticket(self, state: AgentState):
        analysis = state["analysis"]
        prompt = f"""Based on the analysis below, triage the ticket into one of the following tiers:
        - Tier 1 Support: Basic troubleshooting, Passwords, Routine requests.
        - Tier 2 Support: Advanced technical support, Data issues, Integration logic.
        - Tier 3 Support: Critical/Complex engineering, Root cause analysis, Config changes.
        - Vendor Product Support: Core product bugs.

        Analysis: {json.dumps(analysis)}
        
        Provide the decision, responsible party, reasoning, and if escalation is needed.
        """
        decision = await self.llm.generate_structured(prompt, TriageDecision)
        return {"triage": decision.model_dump()}

    async def _retrieve_context(self, state: AgentState):
        analysis = state["analysis"]
        query = f"{analysis['intent']} {analysis['summary']}"
        results = await self.vector_db.search(query)
        context = [f"Source: {r['source']}\nContent: {r['text']}" for r in results]
        return {"context": context}

    async def _draft_response(self, state: AgentState):
        context = state.get("context", [])
        analysis = state["analysis"]
        triage = state["triage"]
        user_message = state["messages"][-1].content
        
        context_str = "\n\n".join(context)
        
        prompt = f"""You are a helpful Medical Support Assistant.
        Draft a polite and professional response to the user based on the context and triage decision.
        
        User Message: {user_message}
        
        Context:
        {context_str}
        
        Triage Info:
        {json.dumps(triage)}
        
        Analysis:
        {json.dumps(analysis)}
        
        If the issue is escalated (Tier 2/3/Product), inform the user that it has been forwarded to the responsible team.
        Provide citations if available in the context.
        """
        draft = await self.llm.generate_structured(prompt, AnswerDraft)
        return {"draft": draft.model_dump()}

    async def _create_output(self, state: AgentState):
        return {
            "final_output": {
                "analysis": state["analysis"],
                "triage_decision": state["triage"],
                "answer_draft": state["draft"]
            }
        }

    async def run(self, message: str):
        result = await self.graph.ainvoke({
            "messages": [HumanMessage(content=message)],
            "analysis": {},
            "triage": {},
            "context": [],
            "draft": {},
            "final_output": {}
        })
        return result["final_output"]
