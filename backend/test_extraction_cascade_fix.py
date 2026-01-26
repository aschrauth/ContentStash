"""
Test script to verify extraction cascade logic updates extraction_type correctly.

This test verifies that when extraction cascades from one method to another
(e.g., Fast → Complete), the extraction_type field is updated to reflect
the actual method that successfully extracted the content.
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

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.background import process_item_background
from app.database import get_database, connect_to_mongo, close_mongo_connection

async def test_extraction_cascade():
    """
    Test that extraction_type is updated when cascade occurs.
    
    We'll use a URL that's known to require Playwright (JavaScript-heavy site)
    and request "fast" extraction. The system should:
    1. Try Readability (fast) first
    2. Fail or get insufficient content
    3. Fall back to Playwright (complete)
    4. Update extraction_type to "complete" in the database
    """
    # Connect to database first
    await connect_to_mongo()
    
    try:
        await _run_test()
    finally:
        # Always close database connection
        await close_mongo_connection()

async def _run_test():
    """
    Test that extraction_type is updated when cascade occurs.
    
    We'll use a URL that's known to require Playwright (JavaScript-heavy site)
    and request "fast" extraction. The system should:
    1. Try Readability (fast) first
    2. Fail or get insufficient content
    3. Fall back to Playwright (complete)
    4. Update extraction_type to "complete" in the database
    """
    print("=" * 80)
    print("Testing Extraction Cascade Logic - extraction_type Update")
    print("=" * 80)
    
    # Get database connection
    db = get_database()
    
    # Test URL - using the one from the terminal logs that triggered the cascade
    test_url = "https://www.bitesizelearning.co.uk/resources/scarf-model-david-rock-explained"
    
    # Create a test user (or use existing one)
    # For this test, we'll assume a user exists - you may need to adjust this
    user_doc = await db.users.find_one({})
    if not user_doc:
        print("❌ No users found in database. Please create a user first.")
        return
    
    user_id = str(user_doc["_id"])
    print(f"✓ Using test user: {user_doc.get('email', 'unknown')}")
    
    # Create a test item with "fast" extraction type
    print(f"\n📝 Creating test item with URL: {test_url}")
    print(f"   Initial extraction_type: 'fast'")
    
    now = datetime.utcnow()
    item_doc = {
        "owner_id": ObjectId(user_id),
        "url": test_url,
        "title": "Test: SCARF Model - Extraction Cascade",
        "description": "Testing extraction cascade from fast to complete",
        "image_url": None,
        "favicon_url": None,
        "notes_markdown": None,
        "tags": ["test"],
        "archived_text": None,
        "extraction_type": "fast",  # Start with fast
        "suggested_tags": None,
        "suggested_topic": None,
        "processing_status": "pending",
        "processing_error": None,
        "created_at": now,
        "updated_at": now,
        "archived_at": None
    }
    
    result = await db.saved_items.insert_one(item_doc)
    item_id = str(result.inserted_id)
    print(f"✓ Created test item with ID: {item_id}")
    
    # Process the item
    print(f"\n🔄 Processing item (this may take 30-60 seconds)...")
    print(f"   Expected behavior:")
    print(f"   1. Try Readability (fast) - should get insufficient content")
    print(f"   2. Fall back to Playwright (complete) - should succeed")
    print(f"   3. Update extraction_type to 'complete'")
    
    try:
        await process_item_background(item_id, user_id)
        
        # Fetch the updated item
        updated_item = await db.saved_items.find_one({"_id": ObjectId(item_id)})
        
        print(f"\n📊 Results:")
        print(f"   Processing Status: {updated_item.get('processing_status')}")
        print(f"   Extraction Type: {updated_item.get('extraction_type')}")
        print(f"   Content Length: {len(updated_item.get('archived_text', '')) if updated_item.get('archived_text') else 0} chars")
        print(f"   Processing Error: {updated_item.get('processing_error', 'None')}")
        
        # Verify the fix
        if updated_item.get('extraction_type') == 'complete':
            print(f"\n✅ SUCCESS! extraction_type was correctly updated to 'complete'")
            print(f"   The cascade logic is working as expected.")
        elif updated_item.get('extraction_type') == 'fast':
            if updated_item.get('archived_text') and len(updated_item.get('archived_text', '')) > 1000:
                print(f"\n✅ extraction_type is 'fast' but content was extracted successfully")
                print(f"   This means Readability worked without needing to cascade.")
            else:
                print(f"\n❌ ISSUE: extraction_type is still 'fast' but content is insufficient")
                print(f"   Expected: 'complete' (after cascade)")
        else:
            print(f"\n⚠️  Unexpected extraction_type: {updated_item.get('extraction_type')}")
        
        # Cleanup - delete test item
        print(f"\n🧹 Cleaning up test item...")
        await db.saved_items.delete_one({"_id": ObjectId(item_id)})
        await db.item_chunks.delete_many({"item_id": item_id})
        print(f"✓ Test item deleted")
        
    except Exception as e:
        print(f"\n❌ Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Cleanup even on error
        print(f"\n🧹 Cleaning up test item...")
        await db.saved_items.delete_one({"_id": ObjectId(item_id)})
        await db.item_chunks.delete_many({"item_id": item_id})
        print(f"✓ Test item deleted")

if __name__ == "__main__":
    print("\n🧪 Starting Extraction Cascade Test\n")
    asyncio.run(test_extraction_cascade())
    print("\n✅ Test completed\n")