"""
Debug script to check YouTube source values in the database.
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.services.youtube import is_youtube_url

async def check_youtube_sources():
    # Connect to database
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client.contentstash
    
    try:
        # Find YouTube items
        items = await db.saved_items.find({'url': {'$regex': 'youtube.com|youtu.be'}}).limit(5).to_list(length=5)
        
        print('YouTube items in database:')
        print('=' * 80)
        for item in items:
            url = item.get('url', 'N/A')
            source = item.get('source', 'N/A')
            title = item.get('title', 'N/A')[:50] if item.get('title') else 'N/A'
            extraction_type = item.get('extraction_type', 'N/A')
            print(f'URL: {url}')
            print(f'Source: {source}')
            print(f'Title: {title}...')
            print(f'Extraction Type: {extraction_type}')
            print(f'Is YouTube URL: {is_youtube_url(url)}')
            print('-' * 80)
        
        if not items:
            print('No YouTube items found in database')
    finally:
        client.close()

if __name__ == '__main__':
    asyncio.run(check_youtube_sources())