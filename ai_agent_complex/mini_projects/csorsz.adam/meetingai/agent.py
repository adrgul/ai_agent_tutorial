import os
import json
import asyncio
from typing import Any, Dict
import httpx

from .sentiment_client import AsyncSentimentClient


class MeetingAgent:
    """Minimal MeetingAI agent that uses an LLM planner and an async sentiment tool.

    Flow:
    1. Planner: ask the LLM whether to call sentiment analysis for given notes.
    2. If LLM requests sentiment, call the sentiment tool (AsyncSentimentClient).
    3. Return final result.
    """

    def __init__(self, openai_key: str | None = None):
        self.openai_key = openai_key or os.environ.get("OPENAI_API_KEY")
        self.sentiment_client = AsyncSentimentClient()

    async def _call_planner(self, notes: str) -> Dict[str, Any]:
        if not self.openai_key:
            # Default simple planner: always call sentiment
            return {"call_tool": True, "tool": "analyze_sentiment", "reason": "no planner key, defaulting to sentiment"}

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.openai_key}", "Content-Type": "application/json"}
        system = "You are a planner deciding which tool to call. Reply ONLY with valid JSON."
        prompt = (
            "Given the meeting notes below, decide whether to call the sentiment analysis tool.\n"
            "Reply ONLY with JSON: {\"call_tool\": true|false, \"tool\": \"analyze_sentiment\", \"reason\": \"...\"}\n\n" + notes
        )
        body = {
            "model": os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 150,
            "temperature": 0.0,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        try:
            text_out = data["choices"][0]["message"]["content"]
            parsed = json.loads(text_out)
            return parsed
        except Exception:
            # fallback: call sentiment
            return {"call_tool": True, "tool": "analyze_sentiment", "reason": "planner parse failed"}

    async def run(self, notes: str) -> Dict[str, Any]:
        # Planner step
        plan = await self._call_planner(notes)
        result: Dict[str, Any] = {"plan": plan}

        # Action step
        if plan.get("call_tool") and plan.get("tool") == "analyze_sentiment":
            sent = await self.sentiment_client.analyze(notes)
            result["tool_output"] = sent

        # Loop: here we could call the planner again to finalize; for demo, return result
        return result
