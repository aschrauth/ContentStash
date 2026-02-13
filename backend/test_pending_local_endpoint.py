"""
Test script for the /api/v1/items/pending-local endpoint
"""
import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_pending_local_endpoint():
    """Test the pending-local endpoint logic"""
    
    # Connect to MongoDB
    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    client = AsyncIOMotorClient(mongodb_url)
    db = client.contentstash
    
    print("=" * 60)
    print("Testing /api/v1/items/pending-local endpoint logic")
    print("=" * 60)
    
    # Get a test user (first user in database)
    user = await db.users.find_one()
    if not user:
        print("❌ No users found in database")
        return
    
    user_id = user["_id"]
    print(f"\n✓ Using test user: {user.get('email', 'unknown')}")
    print(f"  User ID: {user_id}")
    
    # Query for pending local extraction items
    query = {
        "owner_id": user_id,
        "extraction_type": "local",
        "processing_status": "pending",
    }
    
    print(f"\n📋 Query: {query}")
    
    # Fetch items
    cursor = db.saved_items.find(query).sort("created_at", -1)
    items = await cursor.to_list(length=None)
    
    print(f"\n✓ Found {len(items)} pending local extraction items")
    
    if items:
        print("\n📦 Items:")
        for item in items:
            print(f"  - ID: {item['_id']}")
            print(f"    Title: {item.get('title', 'N/A')}")
            print(f"    URL: {item.get('url', 'N/A')}")
            print(f"    Extraction Type: {item.get('extraction_type', 'N/A')}")
            print(f"    Status: {item.get('processing_status', 'N/A')}")
            print()
    else:
        print("\n✓ No pending local extraction items (this is expected if none exist)")
        print("  The endpoint will return an empty list, not an error")
    
    # Also check for any items with the old status
    old_query = {
        "owner_id": user_id,
        "processing_status": "pending_local_extraction",
    }
    
    old_cursor = db.saved_items.find(old_query)
    old_items = await old_cursor.to_list(length=None)
    
    if old_items:
        print(f"\n⚠️  Found {len(old_items)} items with old status 'pending_local_extraction'")
        print("   These will NOT be returned by the new endpoint")
    
    print("\n" + "=" * 60)
    print("✅ Endpoint logic test complete!")
    print("=" * 60)
    
    # Close connection
    client.close()

if __name__ == "__main__":
    asyncio.run(test_pending_local_endpoint())