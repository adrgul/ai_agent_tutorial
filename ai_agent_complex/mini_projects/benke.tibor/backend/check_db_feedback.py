#!/usr/bin/env python3
import asyncio
from infrastructure.postgres_client import postgres_client

async def main():
    await postgres_client.ensure_initialized()
    
    conn = await postgres_client.get_standalone_connection()
    
    # Check feedback data
    rows = await conn.fetch("SELECT citation_id, domain, feedback_type FROM citation_feedback LIMIT 10")
    print(f"\n📊 Feedback in database ({len(rows)} rows):")
    for row in rows:
        print(f"  - {row['citation_id']} ({row['domain']}) → {row['feedback_type']}")
    
    # Check citation_stats
    stats = await conn.fetch("SELECT citation_id, domain, like_percentage FROM citation_stats LIMIT 10")
    print(f"\n📈 Citation stats ({len(stats)} rows):")
    for row in stats:
        print(f"  - {row['citation_id']} ({row['domain']}) → {row['like_percentage']}%")
    
    await conn.close()

asyncio.run(main())
