"""
Test script to verify the YouTube source race condition fix.

This script tests that the background worker correctly handles the race condition
where it might overwrite a high-quality YouTube source with a generic fallback.
"""
import asyncio
import sys
from datetime import datetime
from bson import ObjectId

from app.database import get_database, connect_to_mongo, close_mongo_connection
from app.services.background import process_item_background


async def test_race_condition_fix():
    """Test the race condition fix for YouTube source field."""
    # Connect to database
    await connect_to_mongo()
    db = get_database()
    
    print("=" * 80)
    print("Testing YouTube Source Race Condition Fix")
    print("=" * 80)
    
    # Test 1: Simulate extension setting high-quality source before background worker
    print("\n[Test 1] Extension sets 'YouTube | Channel Name' before background worker")
    print("-" * 80)
    
    # Create a test item with a YouTube URL
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    test_user_id = "507f1f77bcf86cd799439011"  # Example user ID
    
    # Insert test item
    test_item = {
        "url": test_url,
        "title": "Test Video",
        "owner_id": ObjectId(test_user_id),
        "processing_status": "pending",
        "extraction_type": "fast",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.saved_items.insert_one(test_item)
    item_id = str(result.inserted_id)
    print(f"Created test item: {item_id}")
    
    # Simulate extension setting high-quality source
    high_quality_source = "YouTube | Rick Astley"
    await db.saved_items.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": {"source": high_quality_source}}
    )
    print(f"Extension set source: '{high_quality_source}'")
    
    # Now run background processing (which would normally extract "youtube.com")
    print("Running background processing...")
    await process_item_background(item_id, test_user_id)
    
    # Check final source
    final_item = await db.saved_items.find_one({"_id": ObjectId(item_id)})
    final_source = final_item.get("source")
    
    print(f"Final source: '{final_source}'")
    
    if final_source == high_quality_source:
        print("✅ PASS: High-quality source was preserved!")
    else:
        print(f"❌ FAIL: Source was overwritten to '{final_source}'")
    
    # Cleanup
    await db.saved_items.delete_one({"_id": ObjectId(item_id)})
    print(f"Cleaned up test item: {item_id}")
    
    # Test 2: Background worker sets source when none exists
    print("\n[Test 2] Background worker sets source when none exists")
    print("-" * 80)
    
    # Create another test item without source
    test_item2 = {
        "url": test_url,
        "title": "Test Video 2",
        "owner_id": ObjectId(test_user_id),
        "processing_status": "pending",
        "extraction_type": "fast",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result2 = await db.saved_items.insert_one(test_item2)
    item_id2 = str(result2.inserted_id)
    print(f"Created test item: {item_id2}")
    print("No source set initially")
    
    # Run background processing
    print("Running background processing...")
    await process_item_background(item_id2, test_user_id)
    
    # Check final source
    final_item2 = await db.saved_items.find_one({"_id": ObjectId(item_id2)})
    final_source2 = final_item2.get("source")
    
    print(f"Final source: '{final_source2}'")
    
    if final_source2:
        print("✅ PASS: Source was set by background worker!")
    else:
        print("❌ FAIL: Source was not set")
    
    # Cleanup
    await db.saved_items.delete_one({"_id": ObjectId(item_id2)})
    print(f"Cleaned up test item: {item_id2}")
    
    # Test 3: Upgrade from generic to specific YouTube source
    print("\n[Test 3] Upgrade from 'youtube.com' to 'YouTube | Channel Name'")
    print("-" * 80)
    
    # Create test item with generic source
    test_item3 = {
        "url": test_url,
        "title": "Test Video 3",
        "source": "youtube.com",
        "owner_id": ObjectId(test_user_id),
        "processing_status": "pending",
        "extraction_type": "fast",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result3 = await db.saved_items.insert_one(test_item3)
    item_id3 = str(result3.inserted_id)
    print(f"Created test item: {item_id3}")
    print("Initial source: 'youtube.com'")
    
    # Simulate that metadata extraction found a better source
    # (This would happen if the background worker extracted "YouTube | Channel Name")
    # For this test, we'll manually update to simulate the scenario
    await db.saved_items.update_one(
        {"_id": ObjectId(item_id3)},
        {"$set": {"source": "youtube.com"}}
    )
    
    print("Running background processing (which should upgrade the source)...")
    # Note: In real scenario, the background worker would extract the better source
    # For this test, we're just verifying the logic works
    await process_item_background(item_id3, test_user_id)
    
    # Check final source
    final_item3 = await db.saved_items.find_one({"_id": ObjectId(item_id3)})
    final_source3 = final_item3.get("source")
    
    print(f"Final source: '{final_source3}'")
    print("Note: Actual upgrade depends on metadata extraction finding better source")
    
    # Cleanup
    await db.saved_items.delete_one({"_id": ObjectId(item_id3)})
    print(f"Cleaned up test item: {item_id3}")
    
    print("\n" + "=" * 80)
    print("Test Complete!")
    print("=" * 80)
    
    # Close database connection
    await close_mongo_connection()


if __name__ == "__main__":
    try:
        asyncio.run(test_race_condition_fix())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)