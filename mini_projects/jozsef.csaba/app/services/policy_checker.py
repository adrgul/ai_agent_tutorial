"""Policy Checker Service.

Following SOLID principles:
- Single Responsibility: Validates policy compliance
- Dependency Inversion: Depends on LLM abstraction
"""

import re
from typing import List

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import Settings
from app.models.schemas import AnswerDraft, PolicyCheck, TriageResult


class PolicyCheckerService:
    """Service for checking policy compliance in response drafts."""

    def __init__(self, settings: Settings):
        """Initialize policy checker service.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            temperature=0.1,  # Lower temperature for consistent policy checks
            openai_api_key=settings.openai_api_key,
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a policy compliance checker for customer service responses. Check if the draft follows company policies.

Check for:
1. Refund promises: Are refunds guaranteed or promised outside policy?
2. SLA mentions: Is SLA timeframe mentioned or implied?
3. Escalation needs: Does this require management approval?
4. Policy violations: Any promises that violate standard policies?

Policies:
- Never promise refunds without case review
- Don't guarantee specific timeframes beyond standard SLA
- Don't make commitments requiring management approval
- Don't offer compensation without authorization
- Always cite KB articles for policy-backed statements

Return ONLY valid JSON:
{{
    "refund_promise": true|false,
    "sla_mentioned": true|false,
    "escalation_needed": true|false,
    "compliance": "passed|warning|failed",
    "warnings": ["warning 1", "warning 2"]
}}"""),
            ("user", """Draft Response:
{draft_text}

Category: {category}
Priority: {priority}

Check policy compliance and return JSON.""")
        ])

        self.parser = JsonOutputParser()

    async def check_policy(
        self,
        draft: AnswerDraft,
        triage_result: TriageResult,
    ) -> PolicyCheck:
        """Check draft for policy compliance.

        Args:
            draft: Generated answer draft
            triage_result: Triage classification

        Returns:
            Policy check result
        """
        # Combine draft parts
        draft_text = f"{draft.greeting}\n\n{draft.body}\n\n{draft.closing}"

        # Create chain
        chain = self.prompt | self.llm | self.parser

        # Invoke LLM
        result = await chain.ainvoke({
            "draft_text": draft_text,
            "category": triage_result.category,
            "priority": triage_result.priority.value,
        })

        # Additional heuristic checks
        warnings = self._run_heuristic_checks(draft_text, triage_result)
        result["warnings"].extend(warnings)

        return PolicyCheck(
            refund_promise=result["refund_promise"],
            sla_mentioned=result["sla_mentioned"],
            escalation_needed=result["escalation_needed"],
            compliance=result["compliance"],
            warnings=result["warnings"],
        )

    def check_policy_sync(
        self,
        draft: AnswerDraft,
        triage_result: TriageResult,
    ) -> PolicyCheck:
        """Synchronous version of policy check.

        Args:
            draft: Generated answer draft
            triage_result: Triage classification

        Returns:
            Policy check result
        """
        # Combine draft parts
        draft_text = f"{draft.greeting}\n\n{draft.body}\n\n{draft.closing}"

        # Create chain
        chain = self.prompt | self.llm | self.parser

        # Invoke LLM
        result = chain.invoke({
            "draft_text": draft_text,
            "category": triage_result.category,
            "priority": triage_result.priority.value,
        })

        # Additional heuristic checks
        warnings = self._run_heuristic_checks(draft_text, triage_result)
        result["warnings"].extend(warnings)

        return PolicyCheck(
            refund_promise=result["refund_promise"],
            sla_mentioned=result["sla_mentioned"],
            escalation_needed=result["escalation_needed"],
            compliance=result["compliance"],
            warnings=result["warnings"],
        )

    def _run_heuristic_checks(
        self,
        draft_text: str,
        triage_result: TriageResult,
    ) -> List[str]:
        """Run additional heuristic policy checks.

        Args:
            draft_text: Draft response text
            triage_result: Triage classification

        Returns:
            List of warnings
        """
        warnings = []
        text_lower = draft_text.lower()

        # Check for direct refund promises
        refund_keywords = [
            "will refund",
            "guaranteed refund",
            "promise to refund",
            "we'll refund",
        ]
        if any(keyword in text_lower for keyword in refund_keywords):
            warnings.append("Direct refund promise detected - verify authorization")

        # Check for unrealistic timeframes
        unrealistic_patterns = [
            r"within \d+ (minute|hour)s?",
            r"immediately",
            r"right away",
        ]
        if any(re.search(pattern, text_lower) for pattern in unrealistic_patterns):
            warnings.append("Potentially unrealistic timeframe mentioned")

        # Check for missing KB citations on policy matters
        policy_keywords = ["policy", "refund", "sla", "timeframe"]
        has_policy_content = any(keyword in text_lower for keyword in policy_keywords)
        has_citations = bool(re.search(r"\[KB-\d+\]", draft_text))

        if has_policy_content and not has_citations:
            warnings.append("Policy statement without KB citation")

        return warnings
