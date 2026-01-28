"""
Migration script to populate the source field for existing saved items.

This script:
1. Iterates through all items in the saved_items collection
2. For items with URLs, extracts and sets the source
3. For items without URLs, sets source to "Pasted Content"
4. Includes dry-run mode and progress reporting
"""
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.services.extraction import extract_source_from_url
from app.services.youtube import is_youtube_url, extract_video_id, get_video_metadata_from_api, get_video_metadata_from_ytdlp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def migrate_source_field(dry_run: bool = True):
    """
    Migrate existing items to add source field.
    
    Args:
        dry_run: If True, only report what would be changed without making changes
    """
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client.contentstash
    
    try:
        logger.info("Starting source field migration...")
        logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        
        # Get all items without a source field
        query = {"source": {"$exists": False}}
        total_items = await db.saved_items.count_documents(query)
        
        logger.info(f"Found {total_items} items without source field")
        
        if total_items == 0:
            logger.info("No items to migrate")
            return
        
        # Process items in batches
        batch_size = 100
        processed = 0
        updated = 0
        errors = 0
        
        cursor = db.saved_items.find(query)
        
        async for item in cursor:
            try:
                item_id = str(item["_id"])
                url = item.get("url")
                source = None
                
                if url:
                    # Check if it's a YouTube URL
                    if is_youtube_url(url):
                        logger.info(f"Processing YouTube URL for item {item_id}")
                        video_id = extract_video_id(url)
                        
                        if video_id:
                            # Try to get channel name from YouTube API
                            youtube_metadata = get_video_metadata_from_api(video_id, settings.youtube_api_key)
                            
                            # If API failed, try yt-dlp
                            if not youtube_metadata:
                                youtube_metadata = get_video_metadata_from_ytdlp(video_id)
                            
                            if youtube_metadata and youtube_metadata.get('channel_name'):
                                channel_name = youtube_metadata['channel_name']
                                source = f"YouTube | {channel_name}"
                                logger.info(f"  Set source to: {source}")
                            else:
                                source = "YouTube"
                                logger.info(f"  Set source to: YouTube (no channel name)")
                        else:
                            source = "YouTube"
                            logger.info(f"  Set source to: YouTube (no video ID)")
                    else:
                        # Extract domain from URL
                        source = extract_source_from_url(url)
                        logger.info(f"  Extracted source from URL: {source}")
                else:
                    # No URL, set to "Pasted Content"
                    source = "Pasted Content"
                    logger.info(f"  Set source to: Pasted Content (no URL)")
                
                # Update the item
                if not dry_run:
                    await db.saved_items.update_one(
                        {"_id": item["_id"]},
                        {"$set": {"source": source}}
                    )
                    updated += 1
                else:
                    logger.info(f"  [DRY RUN] Would set source to: {source}")
                    updated += 1
                
                processed += 1
                
                # Progress report every 100 items
                if processed % 100 == 0:
                    logger.info(f"Progress: {processed}/{total_items} items processed")
                
            except Exception as e:
                logger.error(f"Error processing item {item_id}: {str(e)}")
                errors += 1
        
        # Final report
        logger.info("=" * 60)
        logger.info("Migration complete!")
        logger.info(f"Total items processed: {processed}")
        logger.info(f"Items updated: {updated}")
        logger.info(f"Errors: {errors}")
        logger.info(f"Mode: {'DRY RUN - No changes made' if dry_run else 'LIVE - Changes committed'}")
        logger.info("=" * 60)
        
    finally:
        client.close()


async def main():
    """Main entry point for the migration script."""
    import sys
    
    # Check for dry-run flag
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == "--live":
        dry_run = False
        logger.warning("=" * 60)
        logger.warning("RUNNING IN LIVE MODE - CHANGES WILL BE COMMITTED")
        logger.warning("=" * 60)
        
        # Confirm before proceeding
        response = input("Are you sure you want to proceed? (yes/no): ")
        if response.lower() != "yes":
            logger.info("Migration cancelled")
            return
    else:
        logger.info("=" * 60)
        logger.info("RUNNING IN DRY RUN MODE - No changes will be made")
        logger.info("Use --live flag to commit changes")
        logger.info("=" * 60)
    
    await migrate_source_field(dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())