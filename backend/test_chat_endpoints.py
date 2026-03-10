"""
Test script for Phase 5 & 6: Semantic search and Chat/ask API endpoints
"""
import asyncio
import sys
from app.services.rag import vector_search, generate_answer
from app.database import get_database
from app.services.gemini import gemini_service

async def test_semantic_search():
    """Test the vector_search function"""
    print("\n" + "="*60)
    print("TEST 1: Semantic Search (vector_search)")
    print("="*60)
    
    # Test with a sample query
    test_query = "machine learning"
    test_user_id = "test_user_123"  # Replace with actual user ID if needed
    
    print(f"\nQuery: '{test_query}'")
    print(f"User ID: {test_user_id}")
    print(f"K: 5")
    
    try:
        results = await vector_search(test_query, test_user_id, k=5)
        
        print(f"\n✅ Vector search completed")
        print(f"Results found: {len(results)}")
        
        if results:
            print("\nTop results:")
            for i, result in enumerate(results[:3], 1):
                print(f"\n  [{i}] Score: {result['score']:.4f}")
                print(f"      Chunk ID: {result['chunk_id']}")
                print(f"      Item ID: {result['item_id']}")
                print(f"      Text preview: {result['text'][:100]}...")
        else:
            print("\n⚠️  No results found (this is expected if no chunks exist yet)")
            
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False
    
    return True


async def test_generate_answer():
    """Test the generate_answer function"""
    print("\n" + "="*60)
    print("TEST 2: Answer Generation with Citations")
    print("="*60)
    
    # Mock chunks for testing
    mock_chunks = [
        {
            'chunk_id': 'chunk1',
            'item_id': 'item1',
            'text': 'Machine learning is a subset of artificial intelligence that focuses on building systems that can learn from data.',
            'score': 0.95,
            'chunk_index': 0
        },
        {
            'chunk_id': 'chunk2',
            'item_id': 'item2',
            'text': 'Deep learning uses neural networks with multiple layers to process complex patterns in data.',
            'score': 0.88,
            'chunk_index': 0
        }
    ]
    
    test_query = "What is machine learning?"
    
    print(f"\nQuery: '{test_query}'")
    print(f"Chunks provided: {len(mock_chunks)}")
    
    try:
        result = await generate_answer(test_query, mock_chunks)
        
        print(f"\n✅ Answer generation completed")
        print(f"\nAnswer:\n{result['answer']}")
        print(f"\nCitations: {len(result['citations'])}")
        
        for i, citation in enumerate(result['citations'], 1):
            print(f"\n  [{i}] ID: {citation.id}")
            print(f"      Title: {citation.title}")
            print(f"      Excerpt: {citation.excerpt[:100]}...")
        
        print(f"\nChunks used: {result['chunks_used']}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False
    
    return True


def test_gemini_availability():
    """Test if Gemini service is available"""
    print("\n" + "="*60)
    print("TEST 0: Gemini Service Availability")
    print("="*60)
    
    is_available = gemini_service.is_available()
    
    if is_available:
        print("\n✅ Gemini service is configured and available")
    else:
        print("\n❌ Gemini service is NOT available")
        print("   Please set GEMINI_API_KEY in your .env file")
        return False
    
    return True


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("TESTING PHASE 5 & 6: Semantic Search & Chat/Ask API")
    print("="*60)
    
    # Test 0: Check Gemini availability
    if not test_gemini_availability():
        print("\n⚠️  Skipping tests - Gemini service not available")
        return
    
    # Test 1: Vector search
    await test_semantic_search()
    
    # Test 2: Answer generation
    await test_generate_answer()
    
    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60)
    print("\nNext steps:")
    print("1. Test the API endpoints using curl or Postman:")
    print("   - GET /api/v1/chat/search?q=your+query&k=5")
    print("   - POST /api/v1/chat/ask with body: {\"question\": \"your question\"}")
    print("\n2. Ensure you have:")
    print("   - MongoDB Atlas Vector Search index created")
    print("   - Some saved items with chunks generated")
    print("   - Valid authentication token")
    print()


if __name__ == "__main__":
    asyncio.run(main())
