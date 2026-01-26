"""
Test script to verify that locally-extracted content is NOT overwritten by server extraction.

This test simulates the browser extension uploading content via the /content endpoint
and verifies that the system:
1. Accepts the uploaded content
2. Does NOT trigger server-side extraction
3. Only runs post-extraction processing (chunking, embedding, etc.)
4. Preserves the locally-extracted content
"""
import asyncio
import sys
from datetime import datetime
from bson import ObjectId

# Add parent directory to path to import app modules
sys.path.insert(0, '/Users/anthonyschrauth/Documents/Dev/ContentStash/backend')

from app.database import get_database, connect_to_mongo, close_mongo_connection
from app.services.background import process_item_background


async def test_local_content_upload():
    """Test that local content upload doesn't trigger server extraction."""
    db = get_database()
    
    print("\n" + "="*80)
    print("TEST: Local Content Upload - Skip Server Extraction")
    print("="*80)
    
    # Create a test item with extraction_type="local" and some content
    test_url = "https://example.com/test-article"
    local_content = "This is locally-extracted content from the browser extension. It should NOT be overwritten by server extraction."
    
    print(f"\n1. Creating test item with extraction_type='local'...")
    item_doc = {
        "owner_id": ObjectId("507f1f77bcf86cd799439011"),  # Test user ID
        "url": test_url,
        "title": "Test Article - Local Extraction",
        "description": "Testing local content preservation",
        "archived_text": local_content,
        "extraction_type": "local",
        "processing_status": "processing",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.saved_items.insert_one(item_doc)
    item_id = str(result.inserted_id)
    print(f"✓ Created item: {item_id}")
    print(f"  - URL: {test_url}")
    print(f"  - extraction_type: local")
    print(f"  - archived_text length: {len(local_content)} chars")
    
    # Simulate the /content endpoint calling process_item_background with skip_extraction=True
    print(f"\n2. Calling process_item_background(skip_extraction=True)...")
    print("   This simulates the /content endpoint after receiving local content")
    
    try:
        await process_item_background(
            item_id=item_id,
            user_id="507f1f77bcf86cd799439011",
            skip_extraction=True  # KEY: This should prevent server extraction
        )
        print("✓ Background processing completed")
    except Exception as e:
        print(f"✗ Background processing failed: {str(e)}")
        # Clean up
        await db.saved_items.delete_one({"_id": ObjectId(item_id)})
        return False
    
    # Verify the content was NOT overwritten
    print(f"\n3. Verifying content was preserved...")
    updated_item = await db.saved_items.find_one({"_id": ObjectId(item_id)})
    
    if not updated_item:
        print("✗ Item not found after processing")
        return False
    
    final_content = updated_item.get("archived_text", "")
    final_status = updated_item.get("processing_status")
    
    print(f"  - Final status: {final_status}")
    print(f"  - Final content length: {len(final_content)} chars")
    print(f"  - Content matches original: {final_content == local_content}")
    
    # Check if content was preserved
    if final_content == local_content:
        print("\n✅ SUCCESS: Local content was preserved!")
        print("   Server extraction was correctly skipped.")
    else:
        print("\n❌ FAILURE: Local content was overwritten!")
        print(f"   Original: {local_content[:100]}...")
        print(f"   Final: {final_content[:100]}...")
    
    # Clean up
    print(f"\n4. Cleaning up test item...")
    await db.saved_items.delete_one({"_id": ObjectId(item_id)})
    print("✓ Test item deleted")
    
    print("\n" + "="*80)
    return final_content == local_content


async def main():
    """Run the test."""
    try:
        # Connect to database
        print("Connecting to MongoDB...")
        await connect_to_mongo()
        print("✓ Connected to MongoDB\n")
        
        success = await test_local_content_upload()
        
        # Close database connection
        await close_mongo_connection()
        
        if success:
            print("\n🎉 All tests passed!")
            sys.exit(0)
        else:
            print("\n💥 Test failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Try to close connection
        try:
            await close_mongo_connection()
        except:
            pass
        
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())