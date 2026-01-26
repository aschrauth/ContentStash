"""
Test to verify the complete extraction cascade including Local extraction.
"""
import asyncio
import logging
from app.services.background import process_item_background
from app.database import get_database, connect_to_mongo, close_mongo_connection
from bson import ObjectId
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_cascade_to_local():
    """
    Test that the cascade properly falls back to local extraction.
    
    We'll create a test item with a URL that will fail both fast and complete extraction,
    and verify it cascades to local extraction.
    """
    # Connect to database first
    await connect_to_mongo()
    
    """
    Test that the cascade properly falls back to local extraction.
    
    We'll create a test item with a URL that will fail both fast and complete extraction,
    and verify it cascades to local extraction.
    """
    db = get_database()
    
    # Create a test user
    test_user = await db.users.find_one({"email": "test@example.com"})
    if not test_user:
        logger.info("Creating test user")
        result = await db.users.insert_one({
            "email": "test@example.com",
            "password_hash": "test_hash",
            "created_at": datetime.utcnow()
        })
        user_id = str(result.inserted_id)
    else:
        user_id = str(test_user["_id"])
    
    # Create a test item with a URL that will fail extraction
    # Using a non-existent domain to trigger extraction failure
    test_url = "https://this-domain-does-not-exist-12345.com/article"
    
    logger.info(f"Creating test item with URL: {test_url}")
    result = await db.saved_items.insert_one({
        "owner_id": user_id,
        "url": test_url,
        "title": "Test Article",
        "extraction_type": "fast",  # Start with fast
        "processing_status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    })
    
    item_id = str(result.inserted_id)
    logger.info(f"Created test item: {item_id}")
    
    # Process the item - this should trigger the cascade
    logger.info("Starting background processing (should cascade: fast → complete → local)")
    await process_item_background(item_id, user_id)
    
    # Check the final state
    item = await db.saved_items.find_one({"_id": ObjectId(item_id)})
    
    logger.info("\n" + "="*80)
    logger.info("FINAL ITEM STATE:")
    logger.info(f"  extraction_type: {item.get('extraction_type')}")
    logger.info(f"  processing_status: {item.get('processing_status')}")
    logger.info(f"  processing_error: {item.get('processing_error')}")
    logger.info(f"  archived_text: {'Present' if item.get('archived_text') else 'None'}")
    logger.info("="*80 + "\n")
    
    # Verify the cascade worked
    assert item.get('extraction_type') == 'local', \
        f"Expected extraction_type='local', got '{item.get('extraction_type')}'"
    
    assert item.get('processing_status') == 'pending_local_extraction', \
        f"Expected processing_status='pending_local_extraction', got '{item.get('processing_status')}'"
    
    logger.info("✓ Cascade to local extraction verified successfully!")
    
    # Cleanup
    await db.saved_items.delete_one({"_id": ObjectId(item_id)})
    logger.info(f"Cleaned up test item: {item_id}")
    
    # Close database connection
    await close_mongo_connection()

if __name__ == "__main__":
    asyncio.run(test_cascade_to_local())