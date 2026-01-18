"""
Background processing service for saved items.
"""
import logging
from datetime import datetime
from bson import ObjectId
from typing import Optional

from app.database import get_database
from app.services.metadata import fetch_metadata
from app.services.extraction import extract_content
from app.services.ai import generate_tags_and_topic

logger = logging.getLogger(__name__)


async def process_item_background(item_id: str, user_id: str):
    """
    Background task to process a saved item:
    1. Update status to 'pending'
    2. Fetch metadata (if missing)
    3. Extract content -> save to archivedText
    4. Generate AI suggestions -> save to suggestedTags, suggestedTopic
    5. Update item with results and set status to 'processed'
    6. Handle errors by setting status to 'failed' and saving processingError
    
    Args:
        item_id: The ID of the item to process
        user_id: The ID of the user who owns the item (for verification)
    """
    db = get_database()
    
    try:
        logger.info(f"Starting background processing for item {item_id}")
        
        # Validate ObjectId
        if not ObjectId.is_valid(item_id):
            logger.error(f"Invalid item ID: {item_id}")
            return
        
        # Fetch the item
        item_doc = await db.saved_items.find_one({"_id": ObjectId(item_id)})
        
        if not item_doc:
            logger.error(f"Item not found: {item_id}")
            return
        
        # Verify ownership
        if str(item_doc["owner_id"]) != user_id:
            logger.error(f"Ownership verification failed for item {item_id}")
            return
        
        # Get the URL
        url = item_doc.get("url")
        
        if not url:
            logger.warning(f"No URL provided for item {item_id}, skipping processing")
            await db.saved_items.update_one(
                {"_id": ObjectId(item_id)},
                {
                    "$set": {
                        "processing_status": "processed",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return
        
        # Update status to pending
        await db.saved_items.update_one(
            {"_id": ObjectId(item_id)},
            {
                "$set": {
                    "processing_status": "pending",
                    "processing_error": None,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Step 1: Fetch metadata (if missing)
        metadata = {}
        if not item_doc.get("title") or not item_doc.get("description"):
            logger.info(f"Fetching metadata for {url}")
            metadata = fetch_metadata(url)
        
        # Step 2: Extract content
        logger.info(f"Extracting content from {url}")
        archived_text = extract_content(url)
        
        # Step 3: Generate AI suggestions
        ai_suggestions = {"tags": [], "topic": None}
        
        if archived_text:
            logger.info(f"Generating AI suggestions for item {item_id}")
            # Get existing user tags to help with suggestions
            existing_tags = item_doc.get("tags", [])
            ai_suggestions = generate_tags_and_topic(
                archived_text,
                existing_tags=existing_tags if existing_tags else None
            )
        else:
            logger.warning(f"No content extracted for item {item_id}, skipping AI suggestions")
        
        # Step 4: Update item with results
        update_doc = {
            "processing_status": "processed",
            "updated_at": datetime.utcnow(),
            "archived_text": archived_text,
            "suggested_tags": ai_suggestions.get("tags"),
            "suggested_topic": ai_suggestions.get("topic")
        }
        
        # Add metadata fields if they were fetched and are missing
        if metadata:
            if not item_doc.get("title") and metadata.get("title"):
                update_doc["title"] = metadata["title"]
            
            if not item_doc.get("description") and metadata.get("description"):
                update_doc["description"] = metadata["description"]
            
            if not item_doc.get("image_url") and metadata.get("image_url"):
                update_doc["image_url"] = metadata["image_url"]
            
            if not item_doc.get("favicon_url") and metadata.get("favicon_url"):
                update_doc["favicon_url"] = metadata["favicon_url"]
        
        await db.saved_items.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": update_doc}
        )
        
        logger.info(f"Successfully processed item {item_id}")
        
    except Exception as e:
        logger.error(f"Error processing item {item_id}: {str(e)}", exc_info=True)
        
        # Update status to failed with error message
        try:
            await db.saved_items.update_one(
                {"_id": ObjectId(item_id)},
                {
                    "$set": {
                        "processing_status": "failed",
                        "processing_error": str(e),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        except Exception as update_error:
            logger.error(f"Failed to update error status for item {item_id}: {str(update_error)}")