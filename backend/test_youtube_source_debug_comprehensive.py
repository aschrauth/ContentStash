"""
Comprehensive test to debug YouTube source issue with extensive logging.
Tests the complete flow from URL save to final source value.
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import get_database
from app.services.extraction import extract_content_with_metadata
from app.services.background import process_item_background
from bson import ObjectId
from datetime import datetime

async def test_youtube_source_flow():
    """Test the complete YouTube source extraction flow"""
    
    # Test YouTube URL
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print("=" * 80)
    print("YOUTUBE SOURCE DEBUG TEST")
    print("=" * 80)
    print(f"\nTest URL: {test_url}")
    print("\n" + "=" * 80)
    
    # Step 1: Test metadata extraction
    print("\n📋 STEP 1: Testing extract_content_with_metadata()")
    print("-" * 80)
    
    metadata_result = await extract_content_with_metadata(test_url, "fast")
    
    print(f"\n✅ Metadata extraction complete")
    print(f"   - Title: {metadata_result.get('title', 'N/A')}")
    print(f"   - Author: {metadata_result.get('author', 'N/A')}")
    print(f"   - Source: '{metadata_result.get('source', 'N/A')}'")
    print(f"   - Has content: {bool(metadata_result.get('text'))}")
    
    # Step 2: Create a test item in database
    print("\n" + "=" * 80)
    print("📝 STEP 2: Creating test item in database")
    print("-" * 80)
    
    db = get_database()
    
    # Create test item
    test_item = {
        "url": test_url,
        "title": "Test YouTube Video",
        "description": "Test description",
        "owner_id": "test_user_id",
        "tags": [],
        "processing_status": "pending",
        "extraction_type": "fast",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.saved_items.insert_one(test_item)
    item_id = str(result.inserted_id)
    
    print(f"✅ Test item created with ID: {item_id}")
    
    # Step 3: Process the item through background worker
    print("\n" + "=" * 80)
    print("⚙️  STEP 3: Processing item through background worker")
    print("-" * 80)
    
    await process_item_background(item_id, "test_user_id")
    
    # Step 4: Check final source value
    print("\n" + "=" * 80)
    print("🔍 STEP 4: Checking final source value in database")
    print("-" * 80)
    
    final_item = await db.saved_items.find_one({"_id": ObjectId(item_id)})
    
    if final_item:
        final_source = final_item.get("source", "NOT SET")
        processing_status = final_item.get("processing_status", "unknown")
        
        print(f"\n✅ Final item state:")
        print(f"   - Processing Status: {processing_status}")
        print(f"   - Source: '{final_source}'")
        print(f"   - Title: {final_item.get('title', 'N/A')}")
        
        # Determine if source is correct
        if final_source and final_source.startswith("YouTube |"):
            print(f"\n✅ SUCCESS: Source is correctly formatted as '{final_source}'")
        elif final_source == "youtube.com":
            print(f"\n❌ FAILURE: Source is generic 'youtube.com' instead of 'YouTube | [Channel Name]'")
        else:
            print(f"\n⚠️  WARNING: Unexpected source value: '{final_source}'")
    else:
        print("\n❌ ERROR: Could not find item in database")
    
    # Cleanup
    print("\n" + "=" * 80)
    print("🧹 CLEANUP: Removing test item")
    print("-" * 80)
    
    await db.saved_items.delete_one({"_id": ObjectId(item_id)})
    print("✅ Test item removed")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_youtube_source_flow())