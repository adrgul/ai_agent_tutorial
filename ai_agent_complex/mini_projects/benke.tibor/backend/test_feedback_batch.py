"""
Test script to verify batch feedback lookup is working correctly.
"""
import asyncio
import sys
import os
import django

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from infrastructure.postgres_client import postgres_client

async def test_batch_feedback():
    """Test batch feedback lookup with real Qdrant doc IDs."""
    
    # Ensure client is initialized
    await postgres_client.ensure_initialized()
    
    # Test citation IDs (actual Qdrant point IDs)
    citation_ids = [
        '1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk0',  # Should have 75% like
        '1ACEdQxgUuAsDHKPBqKyp2kt88DjfXjhv#chunk1',  # Should have no feedback
        '1utetoO-ApR4lmOpY1HS63va_gqmjDfsA#chunk0',  # Should have no feedback
    ]
    
    print(f"Testing batch lookup for {len(citation_ids)} citations...")
    print(f"Citation IDs: {citation_ids}\n")
    
    # Call batch lookup
    feedback_map = await postgres_client.get_citation_feedback_batch(citation_ids, 'marketing')
    
    print(f"✅ Batch lookup complete!")
    print(f"📊 Results: Found feedback for {len(feedback_map)}/{len(citation_ids)} citations\n")
    
    # Display results
    for cid in citation_ids:
        like_pct = feedback_map.get(cid)
        if like_pct is not None:
            print(f"  ✅ {cid}: {like_pct:.1f}% like")
        else:
            print(f"  ⚪ {cid}: No feedback data")
    
    # Test boost calculation
    print("\n🎯 Boost Calculation Test:")
    for cid in citation_ids:
        like_pct = feedback_map.get(cid)
        
        # This is the same logic from qdrant_rag_client.py
        if like_pct is None:
            boost = 0.0
            tier = "neutral (no data)"
        elif like_pct >= 70:
            boost = 0.3
            tier = "high (≥70%)"
        elif like_pct >= 50:
            boost = 0.1
            tier = "medium (50-69%)"
        else:
            boost = -0.2
            tier = "low (<50%)"
        
        original_score = 0.650  # Example semantic similarity score
        final_score = original_score * (1 + boost)
        
        print(f"  {cid[:40]}...")
        print(f"    Like%: {like_pct if like_pct is not None else 'None'}, Tier: {tier}, Boost: {boost:+.1f}")
        print(f"    Score: {original_score:.3f} → {final_score:.3f} (change: {boost*100:+.0f}%)")
    
    # Close pool
    await postgres_client.close()
    print("\n✅ Test complete!")

if __name__ == "__main__":
    asyncio.run(test_batch_feedback())
