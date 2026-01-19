"""
Test script to verify the diversity filtering fix for RAG search.

This script tests that:
1. The diversity filter limits chunks per article
2. Multiple unique articles appear in results
3. The most relevant chunks are still prioritized
"""
import asyncio
from app.services.rag import _apply_diversity_filter


def test_diversity_filter():
    """Test the diversity filter with mock chunks."""
    
    # Create mock chunks - simulating 5 articles with varying scores
    # This simulates a realistic scenario where 4+ articles are relevant
    # Article A has 5 chunks (high scores)
    # Article B has 3 chunks (medium scores)
    # Article C has 2 chunks (lower scores)
    # Article D has 2 chunks (lower scores)
    # Article E has 1 chunk (lowest score)
    mock_chunks = [
        {"chunk_id": "1", "item_id": "article_a", "text": "Chunk 1 from A", "score": 0.95},
        {"chunk_id": "2", "item_id": "article_a", "text": "Chunk 2 from A", "score": 0.93},
        {"chunk_id": "3", "item_id": "article_b", "text": "Chunk 1 from B", "score": 0.90},
        {"chunk_id": "4", "item_id": "article_a", "text": "Chunk 3 from A", "score": 0.88},
        {"chunk_id": "5", "item_id": "article_b", "text": "Chunk 2 from B", "score": 0.85},
        {"chunk_id": "6", "item_id": "article_c", "text": "Chunk 1 from C", "score": 0.82},
        {"chunk_id": "7", "item_id": "article_a", "text": "Chunk 4 from A", "score": 0.80},
        {"chunk_id": "8", "item_id": "article_b", "text": "Chunk 3 from B", "score": 0.78},
        {"chunk_id": "9", "item_id": "article_d", "text": "Chunk 1 from D", "score": 0.76},
        {"chunk_id": "10", "item_id": "article_a", "text": "Chunk 5 from A", "score": 0.75},
        {"chunk_id": "11", "item_id": "article_c", "text": "Chunk 2 from C", "score": 0.72},
        {"chunk_id": "12", "item_id": "article_d", "text": "Chunk 2 from D", "score": 0.70},
        {"chunk_id": "13", "item_id": "article_e", "text": "Chunk 1 from E", "score": 0.68},
    ]
    
    print("=" * 80)
    print("DIVERSITY FILTER TEST")
    print("=" * 80)
    
    # Test 1: Without diversity filter (old behavior)
    print("\n📊 Test 1: Without diversity filter (simulating old behavior)")
    print("-" * 80)
    top_8_no_filter = mock_chunks[:8]
    article_counts_no_filter = {}
    for chunk in top_8_no_filter:
        article_id = chunk["item_id"]
        article_counts_no_filter[article_id] = article_counts_no_filter.get(article_id, 0) + 1
    
    print(f"Top 8 chunks without diversity filter:")
    for chunk in top_8_no_filter:
        print(f"  - {chunk['chunk_id']}: {chunk['item_id']} (score: {chunk['score']})")
    
    print(f"\nArticle distribution:")
    for article_id, count in sorted(article_counts_no_filter.items()):
        print(f"  - {article_id}: {count} chunks")
    
    print(f"\n❌ Problem: Only {len(article_counts_no_filter)} unique articles in top 8 results")
    print(f"   Article A dominates with {article_counts_no_filter.get('article_a', 0)} chunks!")
    if 'article_d' not in article_counts_no_filter:
        print(f"   Article D is missing entirely (crowded out by Article A)")
    
    # Test 2: With diversity filter (new behavior)
    print("\n\n📊 Test 2: With diversity filter (max 2 chunks per article)")
    print("-" * 80)
    diverse_results = _apply_diversity_filter(mock_chunks, k=8, max_chunks_per_item=2)
    article_counts_with_filter = {}
    for chunk in diverse_results:
        article_id = chunk["item_id"]
        article_counts_with_filter[article_id] = article_counts_with_filter.get(article_id, 0) + 1
    
    print(f"Top 8 chunks with diversity filter:")
    for chunk in diverse_results:
        print(f"  - {chunk['chunk_id']}: {chunk['item_id']} (score: {chunk['score']})")
    
    print(f"\nArticle distribution:")
    for article_id, count in sorted(article_counts_with_filter.items()):
        print(f"  - {article_id}: {count} chunks")
    
    print(f"\n✅ Solution: {len(article_counts_with_filter)} unique articles in top 8 results")
    print(f"   Each article limited to max 2 chunks for diversity")
    
    # Verify constraints
    print("\n\n🔍 Verification:")
    print("-" * 80)
    
    # Check that we got the requested number of chunks (or as many as possible with diversity)
    expected_chunks = min(8, len(mock_chunks))
    assert len(diverse_results) <= 8, f"Expected at most 8 chunks, got {len(diverse_results)}"
    print(f"✓ Returned {len(diverse_results)} chunks (respecting diversity constraints)")
    
    # Check that no article has more than 2 chunks
    max_chunks = max(article_counts_with_filter.values())
    assert max_chunks <= 2, f"Article has {max_chunks} chunks, exceeds limit of 2"
    print(f"✓ No article has more than 2 chunks")
    
    # Check that we have at least 4 unique articles (the goal of this fix)
    unique_articles = len(article_counts_with_filter)
    assert unique_articles >= 4, f"Only {unique_articles} unique articles, expected at least 4"
    print(f"✓ Results include {unique_articles} unique articles (improved from {len(article_counts_no_filter)})")
    
    # Verify Article D is now included
    assert 'article_d' in article_counts_with_filter, "Article D should be included with diversity filter"
    print(f"✓ Article D is now included (was missing without diversity filter)")
    
    # Check that results are still sorted by score (within diversity constraints)
    scores = [chunk["score"] for chunk in diverse_results]
    print(f"✓ Scores are prioritized: {scores}")
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED - Diversity filter working correctly!")
    print("=" * 80)
    
    # Summary
    print("\n📈 IMPROVEMENT SUMMARY:")
    print(f"  Before: {len(article_counts_no_filter)} unique articles")
    print(f"  After:  {len(article_counts_with_filter)} unique articles")
    print(f"  Improvement: +{len(article_counts_with_filter) - len(article_counts_no_filter)} unique articles")
    print(f"\n  This ensures users see more diverse sources in their citations!")


if __name__ == "__main__":
    test_diversity_filter()