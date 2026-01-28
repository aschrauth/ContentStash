"""
Migration script to fix YouTube video sources.
Updates items with source="youtube.com" to have proper "YouTube | [Channel Name]" format.
"""
import asyncio
import sys
import os
import logging

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.services.youtube import is_youtube_url, extract_video_id, get_video_metadata_from_api, get_video_metadata_from_ytdlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_youtube_sources():
    """Fix YouTube video sources in the database."""
    # Connect to database
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client.contentstash
    
    try:
        # Find YouTube items with incorrect source
        query = {
            'url': {'$regex': 'youtube.com|youtu.be'},
            'source': 'youtube.com'
        }
        
        items = await db.saved_items.find(query).to_list(length=None)
        
        logger.info(f"Found {len(items)} YouTube items with source='youtube.com'")
        
        if not items:
            logger.info("No items to fix!")
            return
        
        fixed_count = 0
        failed_count = 0
        
        for item in items:
            item_id = str(item['_id'])
            url = item.get('url')
            
            logger.info(f"Processing item {item_id}: {url}")
            
            # Extract video ID
            video_id = extract_video_id(url)
            if not video_id:
                logger.warning(f"Could not extract video ID from {url}")
                failed_count += 1
                continue
            
            # Try to get metadata
            metadata = get_video_metadata_from_api(video_id, settings.youtube_api_key)
            
            if not metadata:
                logger.info(f"YouTube API failed, trying yt-dlp for {video_id}")
                metadata = get_video_metadata_from_ytdlp(video_id)
            
            if metadata and metadata.get('channel_name'):
                channel_name = metadata['channel_name']
                new_source = f"YouTube | {channel_name}"
                
                # Update the item
                await db.saved_items.update_one(
                    {'_id': item['_id']},
                    {'$set': {'source': new_source}}
                )
                
                logger.info(f"✓ Updated item {item_id}: {new_source}")
                fixed_count += 1
            else:
                logger.warning(f"✗ Could not get metadata for {url}")
                # Set to generic "YouTube" if we can't get channel name
                await db.saved_items.update_one(
                    {'_id': item['_id']},
                    {'$set': {'source': 'YouTube'}}
                )
                logger.info(f"Set generic 'YouTube' source for item {item_id}")
                fixed_count += 1
        
        logger.info(f"\nMigration complete!")
        logger.info(f"Fixed: {fixed_count}")
        logger.info(f"Failed: {failed_count}")
        
    finally:
        client.close()

if __name__ == '__main__':
    asyncio.run(fix_youtube_sources())