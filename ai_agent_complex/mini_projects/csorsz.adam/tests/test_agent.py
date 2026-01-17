import pytest

from meetingai.agent import MeetingAgent


@pytest.mark.asyncio
async def test_agent_calls_sentiment(monkeypatch):
    async def fake_planner(self, notes):
        return {"call_tool": True, "tool": "analyze_sentiment", "reason": "test"}

    async def fake_analyze(self, text):
        return {"sentiment": "satisfied", "raw": {"score": 0.9}}

    monkeypatch.setattr(MeetingAgent, "_call_planner", fake_planner)
    # Patch the instance's sentiment_client.analyze via class
    monkeypatch.setattr("meetingai.sentiment_client.AsyncSentimentClient.analyze", fake_analyze)

    agent = MeetingAgent(openai_key=None)
    res = await agent.run("This is a test meeting note that is positive.")
    assert res.get("tool_output", {}).get("sentiment") == "satisfied"


@pytest.mark.asyncio
async def test_agent_skips_tool_when_planner_says_no(monkeypatch):
    async def fake_planner_no(self, notes):
        return {"call_tool": False, "tool": None, "reason": "no sentiment needed"}

    monkeypatch.setattr(MeetingAgent, "_call_planner", fake_planner_no)

    agent = MeetingAgent(openai_key=None)
    res = await agent.run("Short note")
    assert "tool_output" not in res
