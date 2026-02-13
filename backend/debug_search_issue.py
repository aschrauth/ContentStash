"""
Debug script to investigate AI search issue for test2@test.com
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

async def debug_search_issue():
    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.contentstash
    
    print("=" * 80)
    print("DEBUGGING AI SEARCH ISSUE FOR test2@test.com")
    print("=" * 80)
    
    # Step 1: Find the user
    print("\n1. Finding user test2@test.com...")
    user = await db.users.find_one({"email": "test2@test.com"})
    if not user:
        print("❌ User not found!")
        return
    
    user_id = str(user["_id"])
    print(f"✓ Found user: {user['email']}")
    print(f"  User ID: {user_id}")
    print(f"  User _id type: {type(user['_id'])}")
    
    # Step 2: Check saved items
    print("\n2. Checking saved items for this user...")
    items_cursor = db.saved_items.find({"owner_id": ObjectId(user_id)})
    items = await items_cursor.to_list(length=None)
    print(f"✓ Found {len(items)} saved items")
    
    if items:
        print("\nSample items:")
        for i, item in enumerate(items[:3], 1):
            print(f"  {i}. {item.get('title', 'Untitled')}")
            print(f"     ID: {item['_id']}")
            print(f"     owner_id: {item.get('owner_id')} (type: {type(item.get('owner_id'))})")
    
    # Step 3: Check item_chunks collection
    print("\n3. Checking item_chunks collection...")
    
    # First, check total chunks in collection
    total_chunks = await db.item_chunks.count_documents({})
    print(f"  Total chunks in collection: {total_chunks}")
    
    # Check chunks with owner_id as string
    chunks_str = await db.item_chunks.count_documents({"owner_id": user_id})
    print(f"  Chunks with owner_id as string '{user_id}': {chunks_str}")
    
    # Check chunks with owner_id as ObjectId
    chunks_oid = await db.item_chunks.count_documents({"owner_id": ObjectId(user_id)})
    print(f"  Chunks with owner_id as ObjectId: {chunks_oid}")
    
    # Get sample chunks to inspect
    print("\n4. Inspecting sample chunks...")
    sample_chunks_cursor = db.item_chunks.find({}).limit(5)
    sample_chunks = await sample_chunks_cursor.to_list(length=5)
    
    if sample_chunks:
        print(f"  Found {len(sample_chunks)} sample chunks:")
        for i, chunk in enumerate(sample_chunks, 1):
            print(f"\n  Chunk {i}:")
            print(f"    _id: {chunk['_id']}")
            print(f"    item_id: {chunk.get('item_id')} (type: {type(chunk.get('item_id'))})")
            print(f"    owner_id: {chunk.get('owner_id')} (type: {type(chunk.get('owner_id'))})")
            print(f"    chunk_index: {chunk.get('chunk_index')}")
            print(f"    text preview: {chunk.get('text', '')[:100]}...")
            print(f"    has embedding: {bool(chunk.get('embedding'))}")
            if chunk.get('embedding'):
                print(f"    embedding dimension: {len(chunk.get('embedding'))}")
    else:
        print("  ❌ No chunks found in collection!")
    
    # Step 5: Check if chunks exist for user's items
    print("\n5. Checking chunks for user's specific items...")
    if items:
        item_ids = [str(item['_id']) for item in items]
        
        # Try both string and ObjectId formats
        chunks_for_items_str = await db.item_chunks.count_documents({"item_id": {"$in": item_ids}})
        print(f"  Chunks with item_id as string: {chunks_for_items_str}")
        
        chunks_for_items_oid = await db.item_chunks.count_documents({"item_id": {"$in": [ObjectId(id) for id in item_ids]}})
        print(f"  Chunks with item_id as ObjectId: {chunks_for_items_oid}")
    
    # Step 6: Check vector search index
    print("\n6. Checking vector search index...")
    try:
        indexes = await db.item_chunks.list_indexes().to_list(length=None)
        print(f"  Found {len(indexes)} indexes on item_chunks:")
        for idx in indexes:
            print(f"    - {idx.get('name')}: {idx.get('key', {})}")
    except Exception as e:
        print(f"  Error listing indexes: {e}")
    
    print("\n" + "=" * 80)
    print("DIAGNOSIS SUMMARY")
    print("=" * 80)
    
    # Determine the issue
    if not items:
        print("❌ ISSUE: User has no saved items")
    elif total_chunks == 0:
        print("❌ ISSUE: No chunks exist in the database at all")
    elif chunks_str == 0 and chunks_oid == 0:
        print("❌ ISSUE: No chunks found for this user (owner_id mismatch)")
        print("   This suggests chunks were not created or owner_id format is wrong")
    elif chunks_str > 0:
        print(f"✓ Found {chunks_str} chunks with owner_id as string")
        print("   Vector search should work if index is configured correctly")
    elif chunks_oid > 0:
        print(f"⚠️  ISSUE FOUND: Chunks have owner_id as ObjectId, but vector_search filters by string!")
        print(f"   Found {chunks_oid} chunks with owner_id as ObjectId")
        print("   The filter in vector_search uses string, but chunks store ObjectId")
        print("   This is the root cause of the search failure!")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(debug_search_issue())
