"""
Test script to debug vector search issue for test2@test.com
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.rag import vector_search
from app.database import get_database, connect_to_mongo, close_mongo_connection
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

async def test_vector_search():
    # Connect to database first
    await connect_to_mongo()
    
    """Test vector search for test2@test.com"""
    
    # Get database
    db = get_database()
    
    # Find user
    user = await db.users.find_one({"email": "test2@test.com"})
    if not user:
        print("❌ User test2@test.com not found")
        return
    
    user_id = str(user["_id"])
    print(f"✓ Found user: {user['email']}")
    print(f"  User ID (string): {user_id}")
    print(f"  User _id (ObjectId): {user['_id']}")
    
    # Check saved items
    items_count = await db.saved_items.count_documents({"owner_id": ObjectId(user_id)})
    print(f"\n✓ User has {items_count} saved items")
    
    # Check item_chunks - try both string and ObjectId
    chunks_str = await db.item_chunks.count_documents({"owner_id": user_id})
    chunks_oid = await db.item_chunks.count_documents({"owner_id": ObjectId(user_id)})
    
    print(f"\n📊 Chunks in database:")
    print(f"  With owner_id as string '{user_id}': {chunks_str}")
    print(f"  With owner_id as ObjectId: {chunks_oid}")
    
    # Get a sample chunk to inspect
    sample_chunk = await db.item_chunks.find_one({})
    if sample_chunk:
        print(f"\n🔍 Sample chunk inspection:")
        print(f"  owner_id value: {sample_chunk.get('owner_id')}")
        print(f"  owner_id type: {type(sample_chunk.get('owner_id'))}")
        print(f"  item_id value: {sample_chunk.get('item_id')}")
        print(f"  item_id type: {type(sample_chunk.get('item_id'))}")
    
    # Now test vector search
    print(f"\n🔍 Testing vector search with query 'evals'...")
    print(f"  Calling vector_search(query='evals', owner_id='{user_id}', k=8)")
    
    try:
        results = await vector_search("evals", user_id, k=8)
        print(f"\n✓ Vector search returned {len(results)} results")
        
        if results:
            print("\nResults:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. Score: {result['score']:.4f}")
                print(f"     Text preview: {result['text'][:100]}...")
        else:
            print("\n❌ No results returned - this is the problem!")
            
            # Additional diagnostics
            print("\n🔍 Additional diagnostics:")
            
            # Check if vector index exists
            indexes = await db.item_chunks.list_indexes().to_list(length=None)
            print(f"\n  Indexes on item_chunks collection:")
            for idx in indexes:
                print(f"    - {idx.get('name')}")
            
            # Try a manual aggregation to see what happens
            print(f"\n  Attempting manual aggregation without vectorSearch...")
            manual_chunks = await db.item_chunks.find({"owner_id": user_id}).limit(5).to_list(length=5)
            print(f"  Found {len(manual_chunks)} chunks with owner_id='{user_id}'")
            
    except Exception as e:
        print(f"\n❌ Error during vector search: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(test_vector_search())
    finally:
        # Close connection
        asyncio.run(close_mongo_connection())