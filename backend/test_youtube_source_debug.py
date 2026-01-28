"""
Test script to debug YouTube source field issue.
This will save a new YouTube video and check if the source is set correctly.
"""
import asyncio
import sys
from app.database import get_database, connect_to_mongo, close_mongo_connection
from app.services.background import process_item_background
from bson import ObjectId
from datetime import datetime

async def test_youtube_source():
    """Test YouTube source field setting."""
    # Connect to database first
    await connect_to_mongo()
    db = get_database()
    
    # Use a test user ID - replace with your actual user ID
    # You can find this by checking an existing item in the database
    test_user_id = "your_user_id_here"
    
    # First, let's find an existing user
    user = await db.users.find_one({})
    if not user:
        print("❌ No users found in database. Please create a user first.")
        return
    
    test_user_id = str(user["_id"])
    print(f"Using user ID: {test_user_id}")
    
    # Test YouTube URL
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print(f"\n🧪 Testing YouTube source field with URL: {test_url}")
    print("=" * 80)
    
    # Create a test item (simulating what the API does)
    now = datetime.utcnow()
    item_doc = {
        "owner_id": ObjectId(test_user_id),
        "url": test_url,
        "title": "Test YouTube Video",
        "description": None,
        "image_url": None,
        "favicon_url": None,
        "notes_markdown": None,
        "tags": [],
        "archived_text": None,
        "extraction_type": "fast",
        "source": None,  # This is the key - source is None for YouTube URLs
        "suggested_tags": None,
        "suggested_topic": None,
        "processing_status": "pending",
        "processing_error": None,
        "created_at": now,
        "updated_at": now,
        "archived_at": None
    }
    
    print("\n📝 Creating test item with source=None (as per current logic)...")
    result = await db.saved_items.insert_one(item_doc)
    item_id = str(result.inserted_id)
    print(f"✓ Created item with ID: {item_id}")
    
    # Check initial state
    item = await db.saved_items.find_one({"_id": ObjectId(item_id)})
    print(f"\n📊 Initial state:")
    print(f"   source: {item.get('source')}")
    print(f"   processing_status: {item.get('processing_status')}")
    
    # Process the item in background
    print(f"\n⚙️  Running background processing...")
    print("=" * 80)
    await process_item_background(item_id, test_user_id)
    
    # Check final state
    item = await db.saved_items.find_one({"_id": ObjectId(item_id)})
    print("\n" + "=" * 80)
    print(f"📊 Final state:")
    print(f"   source: {item.get('source')}")
    print(f"   processing_status: {item.get('processing_status')}")
    print(f"   processing_error: {item.get('processing_error')}")
    
    # Verify the result
    source = item.get('source')
    if source and source.startswith('YouTube |'):
        print(f"\n✅ SUCCESS! Source is correctly set to: {source}")
    elif source == 'youtube.com':
        print(f"\n❌ FAILURE! Source is incorrectly set to: {source}")
        print("   Expected format: 'YouTube | [Channel Name]'")
    elif source is None:
        print(f"\n❌ FAILURE! Source is None")
        print("   Expected format: 'YouTube | [Channel Name]'")
    else:
        print(f"\n⚠️  UNEXPECTED! Source is: {source}")
    
    # Clean up
    print(f"\n🧹 Cleaning up test item...")
    await db.saved_items.delete_one({"_id": ObjectId(item_id)})
    await db.item_chunks.delete_many({"item_id": item_id})
    print("✓ Test item deleted")
    
    # Close database connection
    await close_mongo_connection()

if __name__ == "__main__":
    print("🔍 YouTube Source Field Debug Test")
    print("=" * 80)
    asyncio.run(test_youtube_source())