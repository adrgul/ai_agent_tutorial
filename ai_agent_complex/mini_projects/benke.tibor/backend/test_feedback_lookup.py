#!/usr/bin/env python3
import asyncio
from infrastructure.postgres_client import postgres_client

async def test():
    await postgres_client.initialize()
    result = await postgres_client.get_citation_feedback_percentage('BRAND-v3.2', 'marketing')
    print(f'✅ Feedback percentage: {result}')

asyncio.run(test())
