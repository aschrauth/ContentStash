"""
Test script to verify that explicit "local" extraction choice is honored.
This test ensures the system does NOT attempt server-side extraction when
the user explicitly selects "local" extraction type.
"""
import asyncio
import sys
from datetime import datetime
from bson import ObjectId

# Add parent directory to path
sys.path.insert(0, '/Users/anthonyschrauth/Developer/ContentStash/backend')

from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection, get_database
from app.services.background import process_item_background


async def test_local_extraction_honor():
    """Test that explicit 'local' extraction choice is honored."""
    
    # Initialize database connection
    await connect_to_mongo()
    db = get_database()
    
    try:
        print("=" * 80)
        print("TEST: Explicit 'local' extraction choice should be honored")
        print("=" * 80)
        
        # Create a test item with explicit "local" extraction type
        test_url = "https://example.com/test-article"
        test_user_id = "test_user_123"
        
        test_item = {
            "url": test_url,
            "title": "Test Article for Local Extraction",
            "owner_id": test_user_id,
            "extraction_type": "local",  # EXPLICIT choice
            "processing_status": "pending",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "tags": [],
            "is_favorite": False
        }
        
        # Insert test item
        result = await db.saved_items.insert_one(test_item)
        item_id = str(result.inserted_id)
        
        print(f"\n✅ Created test item: {item_id}")
        print(f"   URL: {test_url}")
        print(f"   extraction_type: 'local' (EXPLICIT)")
        print(f"   processing_status: 'pending'")
        
        # Process the item in background
        print(f"\n🔄 Processing item in background...")
        await process_item_background(item_id, test_user_id)
        
        # Fetch the updated item
        updated_item = await db.saved_items.find_one({"_id": ObjectId(item_id)})
        
        print(f"\n📊 Results after background processing:")
        print(f"   processing_status: {updated_item.get('processing_status')}")
        print(f"   processing_error: {updated_item.get('processing_error')}")
        print(f"   extraction_type: {updated_item.get('extraction_type')}")
        print(f"   archived_text: {'Present' if updated_item.get('archived_text') else 'None'}")
        
        # Verify expectations
        print(f"\n🔍 Verification:")
        
        expected_status = "pending_local_extraction"
        actual_status = updated_item.get('processing_status')
        
        if actual_status == expected_status:
            print(f"   ✅ Status is '{expected_status}' (correct)")
        else:
            print(f"   ❌ Status is '{actual_status}' (expected '{expected_status}')")
        
        if updated_item.get('archived_text') is None:
            print(f"   ✅ No archived_text (server-side extraction was skipped)")
        else:
            print(f"   ❌ archived_text is present (server-side extraction was attempted)")
        
        if updated_item.get('extraction_type') == 'local':
            print(f"   ✅ extraction_type remains 'local' (not changed)")
        else:
            print(f"   ❌ extraction_type changed to '{updated_item.get('extraction_type')}'")
        
        # Overall result
        success = (
            actual_status == expected_status and
            updated_item.get('archived_text') is None and
            updated_item.get('extraction_type') == 'local'
        )
        
        print(f"\n{'='*80}")
        if success:
            print("✅ TEST PASSED: Explicit 'local' extraction choice was honored!")
            print("   - No server-side extraction was attempted")
            print("   - Status set to 'pending_local_extraction'")
            print("   - System is waiting for browser extension")
        else:
            print("❌ TEST FAILED: Explicit 'local' extraction choice was NOT honored")
            print("   - System attempted server-side extraction")
        print(f"{'='*80}")
        
        # Cleanup
        await db.saved_items.delete_one({"_id": ObjectId(item_id)})
        print(f"\n🧹 Cleaned up test item: {item_id}")
        
        return success
        
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    success = asyncio.run(test_local_extraction_honor())
    sys.exit(0 if success else 1)