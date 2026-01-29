"""
Test script for optional title feature in POST /api/v1/items endpoint.
Tests automatic metadata fetching when title is not provided.
"""
import asyncio
import sys
from datetime import datetime, timedelta
from bson import ObjectId
from app.database import get_database, connect_to_mongo, close_mongo_connection
from app.models.saved_item import SavedItemCreate
from app.routers.items import create_item
from app.models.user import User, UserPreferences
from app.utils.auth import create_access_token
from fastapi import BackgroundTasks
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_optional_title():
    """Test creating an item without a title - should auto-fetch metadata."""
    
    # Connect to database
    await connect_to_mongo()
    db = get_database()
    
    # Create a test user
    test_user_email = f"test_optional_title_{datetime.utcnow().timestamp()}@example.com"
    user_doc = {
        "email": test_user_email,
        "name": "Test User",
        "hashed_password": "test_hash",
        "preferences": {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    logger.info(f"✓ Created test user: {user_id}")
    
    # Create user object
    current_user = User(
        id=user_id,
        email=test_user_email,
        name="Test User",
        preferences=UserPreferences(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Test 1: Create item with URL but no title (should auto-fetch)
    logger.info("\n=== Test 1: URL without title (should auto-fetch metadata) ===")
    
    item_data = SavedItemCreate(
        url="https://example.com",
        extraction_type="fast"
    )
    
    background_tasks = BackgroundTasks()
    
    try:
        created_item = await create_item(
            item_data=item_data,
            background_tasks=background_tasks,
            current_user=current_user
        )
        
        logger.info(f"✓ Item created successfully!")
        logger.info(f"  ID: {created_item.id}")
        logger.info(f"  URL: {created_item.url}")
        logger.info(f"  Title: {created_item.title}")
        logger.info(f"  Description: {created_item.description}")
        logger.info(f"  Image URL: {created_item.image_url}")
        logger.info(f"  Favicon URL: {created_item.favicon_url}")
        
        # Verify title was auto-fetched
        if created_item.title and created_item.title != "https://example.com":
            logger.info(f"✓ Title was automatically fetched from URL!")
        elif created_item.title == "https://example.com":
            logger.info(f"⚠ Title fallback to URL (metadata fetch may have failed)")
        else:
            logger.error(f"✗ Title is None - this should not happen!")
            
    except Exception as e:
        logger.error(f"✗ Failed to create item: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Create item with URL and explicit title (should use provided title)
    logger.info("\n=== Test 2: URL with explicit title (should use provided title) ===")
    
    item_data2 = SavedItemCreate(
        url="https://example.com",
        title="My Custom Title",
        extraction_type="fast"
    )
    
    try:
        created_item2 = await create_item(
            item_data=item_data2,
            background_tasks=background_tasks,
            current_user=current_user
        )
        
        logger.info(f"✓ Item created successfully!")
        logger.info(f"  ID: {created_item2.id}")
        logger.info(f"  Title: {created_item2.title}")
        
        if created_item2.title == "My Custom Title":
            logger.info(f"✓ Custom title was preserved!")
        else:
            logger.error(f"✗ Custom title was not preserved: {created_item2.title}")
            
    except Exception as e:
        logger.error(f"✗ Failed to create item: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test 3: YouTube URL without title (should auto-fetch from YouTube)
    logger.info("\n=== Test 3: YouTube URL without title (should auto-fetch from YouTube) ===")
    
    item_data3 = SavedItemCreate(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        extraction_type="fast"
    )
    
    try:
        created_item3 = await create_item(
            item_data=item_data3,
            background_tasks=background_tasks,
            current_user=current_user
        )
        
        logger.info(f"✓ Item created successfully!")
        logger.info(f"  ID: {created_item3.id}")
        logger.info(f"  Title: {created_item3.title}")
        logger.info(f"  Description: {created_item3.description[:100] if created_item3.description else None}...")
        logger.info(f"  Image URL: {created_item3.image_url}")
        
        if created_item3.title and "youtube.com" not in created_item3.title.lower():
            logger.info(f"✓ YouTube title was automatically fetched!")
        else:
            logger.info(f"⚠ YouTube metadata fetch may have failed (using fallback)")
            
    except Exception as e:
        logger.error(f"✗ Failed to create item: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Cleanup: Delete test user and items
    logger.info("\n=== Cleanup ===")
    await db.saved_items.delete_many({"owner_id": ObjectId(user_id)})
    await db.users.delete_one({"_id": ObjectId(user_id)})
    logger.info("✓ Cleaned up test data")
    
    # Close database connection
    await close_mongo_connection()
    
    logger.info("\n=== Test Complete ===")


if __name__ == "__main__":
    asyncio.run(test_optional_title())