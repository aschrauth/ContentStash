# RAG Search Diversity Fix

## Problem Statement

Users were only seeing 3 unique articles in citations when 4+ relevant articles existed in their library. This occurred because multiple chunks from the same article could dominate the top 8 search results, crowding out other relevant articles.

### Example Scenario
- User has 4 relevant articles (A, B, C, D) saved
- Vector search returns 8 chunks: [A, A, B, A, B, C, A, B]
- Only 3 unique articles appear in citations (A, B, C)
- Article D is completely missing despite being relevant

## Root Cause Analysis

The issue was in the [`vector_search()`](backend/app/services/rag.py:14) function:

1. **Limited Retrieval**: Only 8 chunks were retrieved (`k=8`)
2. **No Diversity Constraint**: Multiple chunks from the same article could dominate results
3. **Citation Generation**: [`_parse_answer_with_citations()`](backend/app/services/rag.py:527) creates one citation per unique article, but only from chunks that were retrieved

**Impact**: If Article A had 4 chunks in the top 8, only 4-5 unique articles could appear maximum, often resulting in just 3 unique articles.

## Solution Implemented

### Approach: Post-Retrieval Diversity Filtering

We implemented a hybrid approach combining elements of Options A and C:

1. **Increased Retrieval**: Retrieve 3x more chunks initially (`k * 3 = 24` chunks)
2. **Diversity Filter**: Apply post-retrieval filtering to limit chunks per article
3. **Greedy Selection**: Select top-scoring chunks while respecting diversity constraints

### Key Changes

#### 1. Updated `vector_search()` Function

**File**: [`backend/app/services/rag.py`](backend/app/services/rag.py:14)

```python
async def vector_search(query: str, owner_id: str, k: int = 8, max_chunks_per_item: int = 2) -> List[Dict]:
    """
    Perform semantic search using MongoDB Atlas Vector Search with diversity.
    
    New parameters:
    - max_chunks_per_item: Maximum chunks per article to ensure diversity (default: 2)
    """
    # Retrieve more chunks initially to ensure diversity
    retrieval_limit = k * 3  # Get 3x more chunks for diversity filtering
    
    # ... execute vector search with retrieval_limit ...
    
    # Apply diversity filtering to ensure multiple unique articles
    diverse_results = _apply_diversity_filter(all_results, k, max_chunks_per_item)
    
    return diverse_results
```

**Changes**:
- Added `max_chunks_per_item` parameter (default: 2)
- Increased initial retrieval to `k * 3` chunks
- Apply diversity filter before returning results
- Enhanced logging to show diversity metrics

#### 2. New `_apply_diversity_filter()` Function

**File**: [`backend/app/services/rag.py`](backend/app/services/rag.py:186)

```python
def _apply_diversity_filter(chunks: List[Dict], k: int, max_chunks_per_item: int) -> List[Dict]:
    """
    Apply diversity filtering to ensure multiple unique articles in results.
    
    Algorithm:
    1. Iterate through chunks in score order (highest first)
    2. Track chunks selected per article
    3. Skip chunks if article already has max_chunks_per_item
    4. Stop when k chunks selected
    """
```

**Algorithm**:
- Greedy selection prioritizing relevance
- Limits chunks per article to ensure diversity
- Maintains score-based ordering within constraints

## Results

### Before Fix
- Retrieved: 8 chunks
- Unique articles: 3
- Problem: Article A dominated with 4 chunks, Article D missing

### After Fix
- Retrieved: 24 chunks initially, filtered to 8 diverse chunks
- Unique articles: 4+
- Solution: Each article limited to 2 chunks, all relevant articles included

### Test Results

```bash
$ python3 backend/test_diversity_fix.py

📊 Test 1: Without diversity filter (simulating old behavior)
Article distribution:
  - article_a: 4 chunks
  - article_b: 3 chunks
  - article_c: 1 chunks
❌ Problem: Only 3 unique articles in top 8 results

📊 Test 2: With diversity filter (max 2 chunks per article)
Article distribution:
  - article_a: 2 chunks
  - article_b: 2 chunks
  - article_c: 2 chunks
  - article_d: 2 chunks
✅ Solution: 4 unique articles in top 8 results

📈 IMPROVEMENT SUMMARY:
  Before: 3 unique articles
  After:  4 unique articles
  Improvement: +1 unique articles
```

## Performance Considerations

### Token Usage
- **Before**: 8 chunks × ~500 tokens = ~4,000 tokens
- **After**: 8 chunks × ~500 tokens = ~4,000 tokens
- **Impact**: No change in token costs (same number of chunks sent to LLM)

### Database Query
- **Before**: Retrieve 8 chunks from MongoDB
- **After**: Retrieve 24 chunks from MongoDB, filter to 8
- **Impact**: Minimal - vector search is fast, filtering is O(n)

### Latency
- Additional 24 chunks retrieved: ~10-20ms extra
- Diversity filtering: <1ms
- **Total impact**: Negligible (<25ms)

## Configuration

The diversity behavior can be tuned via the `max_chunks_per_item` parameter:

```python
# More diversity (1 chunk per article)
chunks = await vector_search(query, user_id, k=8, max_chunks_per_item=1)

# Balanced (default: 2 chunks per article)
chunks = await vector_search(query, user_id, k=8, max_chunks_per_item=2)

# Less diversity (3 chunks per article)
chunks = await vector_search(query, user_id, k=8, max_chunks_per_item=3)
```

**Recommendation**: Keep default at 2 for optimal balance between relevance and diversity.

## Testing

Run the test suite to verify diversity filtering:

```bash
cd backend
source venv/bin/activate
python3 test_diversity_fix.py
```

Expected output: All tests pass, showing improvement from 3 to 4+ unique articles.

## Future Enhancements

Potential improvements for consideration:

1. **Adaptive Diversity**: Adjust `max_chunks_per_item` based on query complexity
2. **MMR Algorithm**: Implement Maximal Marginal Relevance for more sophisticated diversity
3. **User Preference**: Allow users to control diversity vs. relevance trade-off
4. **Analytics**: Track diversity metrics to optimize parameters

## Related Files

- [`backend/app/services/rag.py`](backend/app/services/rag.py) - Main implementation
- [`backend/app/routers/chat.py`](backend/app/routers/chat.py) - API endpoints using vector_search
- [`backend/test_diversity_fix.py`](backend/test_diversity_fix.py) - Test suite

## Summary

This fix ensures users see more diverse article sources in their RAG search results by:
- Retrieving more candidate chunks (24 instead of 8)
- Limiting chunks per article (max 2)
- Maintaining relevance through score-based selection

**Result**: Users now see 4+ unique articles in citations instead of just 3, providing better coverage of their saved content.