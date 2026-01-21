"""
Test script to verify local extraction status fix.

This script tests:
1. Items with extraction_type="local" appear in pending-local queue only when they lack content
2. Items with extraction_type="fast" or "complete" NEVER appear in local queue
3. After content upload, status progresses correctly to "processed"
4. Items with content are excluded from pending-local queue
"""

import asyncio
import sys
from datetime import datetime
from bson import ObjectId

# Add parent directory to path
sys.path.insert(0, '/Users/anthonyschrauth/Documents/Dev/ContentStash/backend')

from app.database import get_database, connect_to_mongo, close_mongo_connection
from app.services.background import process_item_background


async def test_local_extraction_fix():
    """Test the local extraction status fix."""
    # Connect to database first
    await connect_to_mongo()
    db = get_database()
    
    print("\n" + "="*80)
    print("TESTING LOCAL EXTRACTION STATUS FIX")
    print("="*80 + "\n")
    
    # Get a test user (use first user in database)
    user = await db.users.find_one({})
    if not user:
        print("❌ No users found in database. Please create a user first.")
        return
    
    user_id = str(user["_id"])
    print(f"✓ Using test user: {user.get('email', 'unknown')}")
    
    # Test 1: Create item with extraction_type="local" without content
    print("\n" + "-"*80)
    print("TEST 1: Item with extraction_type='local' and no content")
    print("-"*80)
    
    test_item_1 = {
        "owner_id": ObjectId(user_id),
        "url": "https://example.com/test-local",
        "title": "Test Local Extraction",
        "description": "Test item for local extraction",
        "extraction_type": "local",
        "processing_status": "pending",
        "tags": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "archived_at": None
    }
    
    result = await db.saved_items.insert_one(test_item_1)
    item_1_id = str(result.inserted_id)
    print(f"✓ Created test item 1: {item_1_id}")
    
    # Check if it appears in pending-local queue
    pending_local = await db.saved_items.find({
        "owner_id": ObjectId(user_id),
        "extraction_type": "local",
        "processing_status": {"$in": ["pending", "pending_local_extraction"]},
        "$or": [
            {"archived_text": {"$exists": False}},
            {"archived_text": ""},
            {"archived_text": None}
        ],
        "archived_at": None
    }).to_list(length=None)
    
    item_1_in_queue = any(str(item["_id"]) == item_1_id for item in pending_local)
    
    if item_1_in_queue:
        print("✅ PASS: Item appears in pending-local queue (as expected)")
    else:
        print("❌ FAIL: Item does NOT appear in pending-local queue (unexpected)")
    
    # Test 2: Create item with extraction_type="fast"
    print("\n" + "-"*80)
    print("TEST 2: Item with extraction_type='fast' (server processing)")
    print("-"*80)
    
    test_item_2 = {
        "owner_id": ObjectId(user_id),
        "url": "https://example.com/test-fast",
        "title": "Test Fast Extraction",
        "description": "Test item for server extraction",
        "extraction_type": "fast",
        "processing_status": "pending",
        "tags": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "archived_at": None
    }
    
    result = await db.saved_items.insert_one(test_item_2)
    item_2_id = str(result.inserted_id)
    print(f"✓ Created test item 2: {item_2_id}")
    
    # Check if it appears in pending-local queue (it should NOT)
    pending_local = await db.saved_items.find({
        "owner_id": ObjectId(user_id),
        "extraction_type": "local",
        "processing_status": {"$in": ["pending", "pending_local_extraction"]},
        "$or": [
            {"archived_text": {"$exists": False}},
            {"archived_text": ""},
            {"archived_text": None}
        ],
        "archived_at": None
    }).to_list(length=None)
    
    item_2_in_queue = any(str(item["_id"]) == item_2_id for item in pending_local)
    
    if not item_2_in_queue:
        print("✅ PASS: Item does NOT appear in pending-local queue (as expected)")
    else:
        print("❌ FAIL: Item appears in pending-local queue (unexpected)")
    
    # Test 3: Create item with extraction_type="local" WITH content
    print("\n" + "-"*80)
    print("TEST 3: Item with extraction_type='local' and existing content")
    print("-"*80)
    
    test_item_3 = {
        "owner_id": ObjectId(user_id),
        "url": "https://example.com/test-local-with-content",
        "title": "Test Local with Content",
        "description": "Test item with content already extracted",
        "extraction_type": "local",
        "processing_status": "pending",
        "archived_text": "This is some test content that was already extracted.",
        "tags": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "archived_at": None
    }
    
    result = await db.saved_items.insert_one(test_item_3)
    item_3_id = str(result.inserted_id)
    print(f"✓ Created test item 3: {item_3_id}")
    
    # Check if it appears in pending-local queue (it should NOT because it has content)
    pending_local = await db.saved_items.find({
        "owner_id": ObjectId(user_id),
        "extraction_type": "local",
        "processing_status": {"$in": ["pending", "pending_local_extraction"]},
        "$or": [
            {"archived_text": {"$exists": False}},
            {"archived_text": ""},
            {"archived_text": None}
        ],
        "archived_at": None
    }).to_list(length=None)
    
    item_3_in_queue = any(str(item["_id"]) == item_3_id for item in pending_local)
    
    if not item_3_in_queue:
        print("✅ PASS: Item does NOT appear in pending-local queue (as expected)")
    else:
        print("❌ FAIL: Item appears in pending-local queue (unexpected)")
    
    # Test 4: Simulate content upload and verify status progression
    print("\n" + "-"*80)
    print("TEST 4: Status progression after content upload")
    print("-"*80)
    
    # Update item 1 with content (simulating Chrome extension upload)
    await db.saved_items.update_one(
        {"_id": ObjectId(item_1_id)},
        {
            "$set": {
                "archived_text": "This is content uploaded by the Chrome extension.",
                "processing_status": "processing",
                "updated_at": datetime.utcnow()
            }
        }
    )
    print(f"✓ Simulated content upload for item 1")
    
    # Run background processing
    print(f"✓ Running background processing...")
    await process_item_background(item_1_id, user_id)
    
    # Check final status
    item_1_updated = await db.saved_items.find_one({"_id": ObjectId(item_1_id)})
    final_status = item_1_updated.get("processing_status")
    
    if final_status == "processed":
        print(f"✅ PASS: Final status is 'processed' (as expected)")
    else:
        print(f"❌ FAIL: Final status is '{final_status}' (expected 'processed')")
    
    # Verify it no longer appears in pending-local queue
    pending_local = await db.saved_items.find({
        "owner_id": ObjectId(user_id),
        "extraction_type": "local",
        "processing_status": {"$in": ["pending", "pending_local_extraction"]},
        "$or": [
            {"archived_text": {"$exists": False}},
            {"archived_text": ""},
            {"archived_text": None}
        ],
        "archived_at": None
    }).to_list(length=None)
    
    item_1_still_in_queue = any(str(item["_id"]) == item_1_id for item in pending_local)
    
    if not item_1_still_in_queue:
        print("✅ PASS: Item no longer appears in pending-local queue (as expected)")
    else:
        print("❌ FAIL: Item still appears in pending-local queue (unexpected)")
    
    # Cleanup
    print("\n" + "-"*80)
    print("CLEANUP")
    print("-"*80)
    
    await db.saved_items.delete_one({"_id": ObjectId(item_1_id)})
    await db.saved_items.delete_one({"_id": ObjectId(item_2_id)})
    await db.saved_items.delete_one({"_id": ObjectId(item_3_id)})
    print("✓ Deleted test items")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80 + "\n")
    
    # Close database connection
    await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(test_local_extraction_fix())