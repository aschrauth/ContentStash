"""
Test script for vector_search functionality.
Run this after creating the MongoDB Atlas Vector Search index.
"""
import asyncio
import sys
from app.services.rag import vector_search
from app.database import connect_to_mongo, close_mongo_connection


async def test_vector_search():
    """Test the vector_search function"""
    print("=" * 60)
    print("Vector Search Test")
    print("=" * 60)
    
    # Connect to database
    print("\n1. Connecting to MongoDB...")
    await connect_to_mongo()
    print("✅ Connected")
    
    # Test query
    test_query = "machine learning and AI"
    test_owner_id = "test_user_123"  # Replace with actual user ID
    
    print(f"\n2. Testing vector search...")
    print(f"   Query: '{test_query}'")
    print(f"   Owner ID: {test_owner_id}")
    print(f"   K: 8")
    
    try:
        results = await vector_search(
            query=test_query,
            owner_id=test_owner_id,
            k=8
        )
        
        print(f"\n3. Results:")
        print(f"   Found {len(results)} chunks")
        
        if results:
            print("\n   Top results:")
            for i, result in enumerate(results[:3], 1):
                print(f"\n   [{i}] Score: {result['score']:.4f}")
                print(f"       Item ID: {result['item_id']}")
                print(f"       Chunk: {result['chunk_index']}")
                print(f"       Text preview: {result['text'][:100]}...")
        else:
            print("\n   ⚠️  No results found. This could mean:")
            print("      - No chunks exist for this user")
            print("      - Vector search index not created yet")
            print("      - Gemini API key not configured")
            print("\n   Check the logs above for specific error messages.")
        
    except Exception as e:
        print(f"\n❌ Error during vector search: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Cleanup
    print("\n4. Closing connection...")
    await close_mongo_connection()
    print("✅ Done")
    print("=" * 60)


if __name__ == "__main__":
    print("\n⚠️  IMPORTANT: Before running this test:")
    print("   1. Create the MongoDB Atlas Vector Search index")
    print("   2. See VECTOR_SEARCH_SETUP.md for instructions")
    print("   3. Ensure GEMINI_API_KEY is set in .env")
    print("   4. Save some items to generate chunks")
    print()
    
    response = input("Have you completed the setup? (y/n): ")
    if response.lower() != 'y':
        print("\nPlease complete the setup first. Exiting...")
        sys.exit(0)
    
    asyncio.run(test_vector_search())