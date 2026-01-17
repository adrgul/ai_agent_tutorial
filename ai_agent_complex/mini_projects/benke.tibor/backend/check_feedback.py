#!/usr/bin/env python3
import asyncio
from infrastructure.postgres_client import postgres_client

async def main():
    await postgres_client.initialize()
    
    # Check feedback for Qdrant doc
    doc_id = "1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk0"
    result = await postgres_client.get_citation_feedback_percentage(doc_id, "marketing")
    
    if result is not None:
        print(f"✅ Feedback data found!")
        print(f"   Citation: {doc_id}")
        print(f"   Like percentage: {result}%")
        print(f"   Expected boost: +0.3 (30% boost for >70% like)")
    else:
        print(f"❌ No feedback found for {doc_id}")
    
    await postgres_client.close()

asyncio.run(main())
