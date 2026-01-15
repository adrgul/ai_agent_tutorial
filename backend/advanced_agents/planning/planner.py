"""
Planner Node - Generates structured execution plans using LLM.

This module implements the "Plan" part of Plan-and-Execute pattern.

WHY Plan-and-Execute?
- Breaks complex tasks into manageable steps
- Makes agent reasoning transparent and debuggable
- Enables optimization (reordering, parallelization)
- Better error recovery (can replan if step fails)
- Users can see what the agent intends to do before execution

HOW it works:
1. LLM analyzes user request
2. Generates structured JSON plan with steps
3. Each step specifies tool, arguments, dependencies
4. Plan is stored in state for executor to follow

Following SOLID:
- Single Responsibility: Only planning, not execution
- Open/Closed: Easy to add new planning strategies
- Dependency Inversion: Depends on LLM interface, not specific model
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from ..state import AdvancedAgentState, ExecutionPlan, PlanStep
from observability.metrics import record_node_duration
from observability.llm_instrumentation import instrumented_llm_call

logger = logging.getLogger(__name__)


class PlannerNode:
    """
    LangGraph node that generates execution plans.
    
    This node:
    1. Receives user request in state
    2. Prompts LLM to create a plan
    3. Parses LLM output into ExecutionPlan model
    4. Validates plan structure
    5. Stores plan in state for executor
    """
    
    def __init__(self, llm: ChatOpenAI, available_tools: Dict[str, Any]):
        """
        Initialize planner node.
        
        Args:
            llm: Language model for plan generation
            available_tools: Dictionary of tool_name -> tool_description
                            Used to tell LLM what tools are available
        """
        self.llm = llm
        self.available_tools = available_tools
        
        # Build tool descriptions for LLM prompt
        self.tool_descriptions = self._build_tool_descriptions()
    
    def _build_tool_descriptions(self) -> str:
        """
        Create formatted tool descriptions for LLM prompt.
        
        WHY: LLM needs to know what tools are available to make good plans.
        """
        descriptions = []
        for tool_name, tool_info in self.available_tools.items():
            desc = f"- {tool_name}: {tool_info.get('description', 'No description')}"
            if "parameters" in tool_info:
                desc += f"\n  Parameters: {tool_info['parameters']}"
            descriptions.append(desc)
        
        return "\n".join(descriptions)
    
    async def __call__(self, state: AdvancedAgentState) -> Dict[str, Any]:
        """
        Generate execution plan from user request.
        
        WHY async?
        - LLM calls are I/O bound
        - Allows other nodes to run while waiting for LLM
        
        Args:
            state: Current agent state with user message
            
        Returns:
            Updated state with execution_plan field populated
        """
        with record_node_duration("planner"):
            # Extract user message
            user_message = state["messages"][-1].content
            
            logger.info(f"[PLANNER] Generating plan for: {user_message[:100]}...")
            state["debug_logs"].append("[PLANNER] Starting plan generation...")
            
            # Extract user preferences from SystemMessage (if present)
            user_context = ""
            for msg in state.get("messages", []):
                if hasattr(msg, 'type') and msg.type == 'system':
                    content = msg.content
                    if "User Context:" in content or "Preferences:" in content:
                        user_context = content
                        logger.info(f"[PLANNER] Found user context: {user_context[:200]}")
                        break
            
            # CRITICAL FIX: Build tool descriptions from state (includes MCP tools)
            dynamic_tool_descriptions = self._build_dynamic_tool_descriptions(state)
            
            # Create planning prompt with all available tools
            system_prompt = self._create_planning_prompt(dynamic_tool_descriptions)
            
            # Build user prompt with context
            user_prompt = f"User request: {user_message}"
            if user_context:
                user_prompt = f"{user_context}\n\n{user_prompt}\n\nIMPORTANT: Use the user's default_city from preferences if they ask for weather without specifying a city."
            user_prompt += "\n\nGenerate an execution plan in JSON format."
            
            # Call LLM
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            try:
                response = await instrumented_llm_call(
                    self.llm,
                    messages,
                    task_type="planner",
                    model_name=self.llm.model_name
                )
                plan_json = response.content
                
                # Parse and validate plan
                plan = self._parse_plan(plan_json)
                
                logger.info(f"[PLANNER] Generated plan with {len(plan.steps)} steps")
                state["debug_logs"].append(f"[PLANNER] ✓ Plan created: {len(plan.steps)} steps")
                
                # Update state
                return {
                    "execution_plan": plan,
                    "current_step_index": 0,
                    "plan_completed": False,
                    "debug_logs": [f"[PLANNER] Plan ID: {plan.plan_id}"]
                }
                
            except Exception as e:
                logger.error(f"[PLANNER] Failed to generate plan: {e}")
                state["debug_logs"].append(f"[PLANNER] ✗ Error: {str(e)}")
                
                # Return a simple fallback plan
                fallback_plan = self._create_fallback_plan(user_message)
                return {
                    "execution_plan": fallback_plan,
                    "current_step_index": 0,
                    "plan_completed": False,
                    "debug_logs": ["[PLANNER] Using fallback plan due to error"]
                }
    
    def _build_dynamic_tool_descriptions(self, state: AdvancedAgentState) -> str:
        """
        Build tool descriptions dynamically from state, including MCP tools.
        
        WHY dynamic?
        - MCP tools are fetched at runtime, not at initialization
        - AlphaVantage/DeepWiki tools are stored in state
        - Planner needs to know about ALL available tools
        
        Args:
            state: Current state with alphavantage_tools and deepwiki_tools
            
        Returns:
            Formatted string of all tool descriptions
        """
        descriptions = []
        
        # Add base tools
        descriptions.append("### Built-in Tools:")
        for tool_name, tool_info in self.available_tools.items():
            desc = f"- {tool_name}: {tool_info.get('description', 'No description')}"
            if "parameters" in tool_info:
                desc += f"\n  Parameters: {tool_info['parameters']}"
            descriptions.append(desc)
        
        # Add AlphaVantage MCP tools if available
        alphavantage_tools = state.get("alphavantage_tools", [])
        if alphavantage_tools:
            descriptions.append("\n### AlphaVantage Financial & Market Data Tools:")
            for tool in alphavantage_tools[:50]:  # Limit to avoid token overflow
                tool_name = tool.get("name", "unknown")
                tool_desc = tool.get("description", "No description")
                input_schema = tool.get("inputSchema", {})
                properties = input_schema.get("properties", {})
                params = ", ".join(properties.keys()) if properties else "none"
                descriptions.append(f"- {tool_name}: {tool_desc}")
                if params != "none":
                    descriptions.append(f"  Parameters: {params}")
            logger.info(f"[PLANNER] Included {len(alphavantage_tools)} AlphaVantage tools")
        
        # Add DeepWiki MCP tools if available
        deepwiki_tools = state.get("deepwiki_tools", [])
        if deepwiki_tools:
            descriptions.append("\n### DeepWiki Knowledge Base Tools:")
            for tool in deepwiki_tools:
                tool_name = tool.get("name", "unknown")
                tool_desc = tool.get("description", "No description")
                descriptions.append(f"- {tool_name}: {tool_desc}")
            logger.info(f"[PLANNER] Included {len(deepwiki_tools)} DeepWiki tools")
        
        return "\n".join(descriptions)
    
    def _create_planning_prompt(self, tool_descriptions: str) -> str:
        """
        Create the system prompt for plan generation.
        
        WHY detailed prompt?
        - LLM needs clear instructions for structured output
        - Examples help LLM understand the format
        - Constraints prevent invalid plans
        
        Args:
            tool_descriptions: Formatted string of available tools
        """
        return f"""You are an expert AI planning agent. Your job is to break down user requests into structured execution plans.

Available tools:
{tool_descriptions}

RULES:
1. Output ONLY valid JSON matching the ExecutionPlan schema
2. Each step must specify a tool from the available tools
3. Steps can depend on other steps (use depends_on field)
4. Steps that don't depend on each other can run in parallel (set can_run_parallel=true)
5. Estimate realistic duration for the entire plan
6. Give each step a unique step_id (e.g., "step_1", "step_2")

OUTPUT FORMAT (JSON):
{{
  "plan_id": "plan_<timestamp>",
  "goal": "High-level description of what this plan achieves",
  "steps": [
    {{
      "step_id": "step_1",
      "description": "What this step does",
      "tool_name": "tool_name_from_available_tools",
      "arguments": {{"param": "value"}},
      "depends_on": [],
      "can_run_parallel": false
    }},
    {{
      "step_id": "step_2",
      "description": "Another step",
      "tool_name": "another_tool",
      "arguments": {{"param": "value"}},
      "depends_on": ["step_1"],
      "can_run_parallel": false
    }}
  ],
  "estimated_duration_seconds": 5.0
}}

EXAMPLE 1 - Sequential plan:
User: "What's the weather in London and convert 100 USD to EUR?"
Plan:
{{
  "plan_id": "plan_001",
  "goal": "Get weather for London and currency conversion",
  "steps": [
    {{
      "step_id": "step_1",
      "description": "Get weather forecast for London",
      "tool_name": "weather",
      "arguments": {{"city": "London"}},
      "depends_on": [],
      "can_run_parallel": true
    }},
    {{
      "step_id": "step_2", 
      "description": "Convert 100 USD to EUR",
      "tool_name": "fx_rates",
      "arguments": {{"from": "USD", "to": "EUR", "amount": 100}},
      "depends_on": [],
      "can_run_parallel": true
    }}
  ],
  "estimated_duration_seconds": 3.0
}}

EXAMPLE 2 - Dependent steps:
User: "Find my location and tell me the weather there"
Plan:
{{
  "plan_id": "plan_002",
  "goal": "Detect location and get weather",
  "steps": [
    {{
      "step_id": "step_1",
      "description": "Detect user location from IP",
      "tool_name": "ip_geolocation",
      "arguments": {{}},
      "depends_on": [],
      "can_run_parallel": false
    }},
    {{
      "step_id": "step_2",
      "description": "Get weather for detected location",
      "tool_name": "weather",
      "arguments": {{"city": "${{step_1.result.city}}"}},
      "depends_on": ["step_1"],
      "can_run_parallel": false
    }}
  ],
  "estimated_duration_seconds": 4.0
}}

Now generate a plan for the user's request."""
    
    def _parse_plan(self, plan_json: str) -> ExecutionPlan:
        """
        Parse LLM output into validated ExecutionPlan.
        
        WHY Pydantic?
        - Automatic validation of JSON structure
        - Type checking for all fields
        - Clear error messages if format is wrong
        
        Args:
            plan_json: JSON string from LLM
            
        Returns:
            Validated ExecutionPlan object
            
        Raises:
            ValidationError: If JSON doesn't match schema
        """
        # Extract JSON from markdown code blocks if present
        if "```json" in plan_json:
            plan_json = plan_json.split("```json")[1].split("```")[0].strip()
        elif "```" in plan_json:
            plan_json = plan_json.split("```")[1].split("```")[0].strip()
        
        # Parse JSON
        plan_dict = json.loads(plan_json)
        
        # Validate with Pydantic
        return ExecutionPlan(**plan_dict)
    
    def _create_fallback_plan(self, user_message: str) -> ExecutionPlan:
        """
        Create a simple fallback plan when planning fails.
        
        WHY fallback?
        - LLM might produce invalid JSON
        - Better to have a simple plan than crash
        - Educational: shows graceful degradation
        
        Args:
            user_message: Original user request
            
        Returns:
            Simple single-step plan
        """
        return ExecutionPlan(
            plan_id=f"fallback_{datetime.now().timestamp()}",
            goal="Respond to user request (fallback plan)",
            steps=[
                PlanStep(
                    step_id="step_1",
                    description="Directly respond to user",
                    tool_name="direct_response",
                    arguments={"message": user_message},
                    depends_on=[],
                    can_run_parallel=False
                )
            ],
            estimated_duration_seconds=1.0
        )
