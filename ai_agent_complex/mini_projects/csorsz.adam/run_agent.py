"""Run a small MeetingAI demo in this folder.

Usage:
  python run_agent.py notes.txt

Environment:
  - OPENAI_API_KEY: (optional) OpenAI API key used for planner or sentiment fallback
  - HUGGINGFACE_API_TOKEN: (optional) Hugging Face token for HF inference (preferred if set)

Place your local API key in `apikulcs.env` (already present) or set env vars.
"""

import sys
import asyncio
import os

from meetingai.agent import MeetingAgent


def load_env_file(path: str) -> None:
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip().strip('"').strip("'")
            if k not in os.environ:
                os.environ[k] = v


async def main(notes_path: str):
    load_env_file(os.path.join(os.path.dirname(__file__), "apikulcs.env"))
    if not os.path.exists(notes_path):
        print("Notes file not found:", notes_path)
        return
    notes = open(notes_path, encoding="utf8").read()
    agent = MeetingAgent()
    res = await agent.run(notes)
    import json
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_agent.py notes.txt")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
