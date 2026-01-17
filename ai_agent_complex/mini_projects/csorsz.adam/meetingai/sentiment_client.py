import os
import json
from typing import Any, Dict
import httpx


class AsyncSentimentClient:
    """Asynchronous sentiment analysis client.

    Behavior:
    - If `HUGGINGFACE_API_TOKEN` (env) is set, calls the Hugging Face Inference API.
    - Else if `OPENAI_API_KEY` (env) is set, calls OpenAI Chat Completions to classify sentiment.
    - Returns dict with at least `sentiment` field (one of: "frustrated","neutral","satisfied") and `raw`.
    """

    def __init__(self, hf_model: str | None = None):
        self.hf_token = os.environ.get("HUGGINGFACE_API_TOKEN")
        self.hf_model = hf_model or os.environ.get("HUGGINGFACE_MODEL") or "distilbert-base-uncased-finetuned-sst-2-english"
        self.openai_key = os.environ.get("OPENAI_API_KEY")

    async def analyze(self, text: str) -> Dict[str, Any]:
        if self.hf_token:
            return await self._analyze_hf(text)
        if self.openai_key:
            return await self._analyze_openai(text)
        raise RuntimeError("No sentiment API token configured (set HUGGINGFACE_API_TOKEN or OPENAI_API_KEY)")

    async def _analyze_hf(self, text: str) -> Dict[str, Any]:
        url = f"https://api-inference.huggingface.co/models/{self.hf_model}"
        headers = {"Authorization": f"Bearer {self.hf_token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json={"inputs": text}, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # HF models usually return a list of {label,score} for classification
        sentiment = "neutral"
        try:
            if isinstance(data, list) and data:
                label = data[0].get("label", "").upper()
                if "NEGATIVE" in label:
                    sentiment = "frustrated"
                elif "POSITIVE" in label:
                    sentiment = "satisfied"
                else:
                    sentiment = "neutral"
            else:
                sentiment = "neutral"
        except Exception:
            sentiment = "neutral"

        return {"sentiment": sentiment, "raw": data}

    async def _analyze_openai(self, text: str) -> Dict[str, Any]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_key}",
            "Content-Type": "application/json",
        }
        # Ask model to reply strict JSON with sentiment field (frustrated|neutral|satisfied)
        system = "You are a sentiment classification assistant. Reply ONLY with valid JSON."
        # Note: keep the instruction concise and explicit about allowed values.
        prompt = (
            "Classify the sentiment of the following meeting notes and reply ONLY with a JSON object:\n"
            "{\"sentiment\": \"frustrated|neutral|satisfied\", \"explanation\": \"...\"}\n---\n" + text
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

        # Extract text
        try:
            text_out = data["choices"][0]["message"]["content"]
            # Force parse JSON from model output
            parsed = json.loads(text_out)
            sentiment = parsed.get("sentiment", "neutral")
            return {"sentiment": sentiment, "raw": data, "extracted": parsed}
        except Exception:
            return {"sentiment": "neutral", "raw": data}
