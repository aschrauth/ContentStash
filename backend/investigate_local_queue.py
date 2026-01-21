"""
Investigation script for local extraction queue items.
Analyzes items with extraction_type="local" and pending status.
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from datetime import datetime

async def investigate_local_queue():
    """Investigate items in the local extraction queue."""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client.contentstash
    
    try:
        # Query items with local extraction type and pending status
        query = {
            "extraction_type": "local",
            "processing_status": {"$in": ["pending", "pending_local_extraction"]}
        }
        
        cursor = db.saved_items.find(query)
        items = await cursor.to_list(length=None)
        
        print(f"\n{'='*80}")
        print(f"LOCAL EXTRACTION QUEUE INVESTIGATION")
        print(f"{'='*80}\n")
        print(f"Total items in local queue: {len(items)}\n")
        
        if not items:
            print("No items found in local extraction queue.")
            return
        
        # Categorize items
        has_content = []
        no_content = []
        
        for item in items:
            has_text = bool(item.get('archived_text') and len(item.get('archived_text', '').strip()) > 0)
            
            if has_text:
                has_content.append(item)
            else:
                no_content.append(item)
        
        # Report summary
        print(f"SUMMARY:")
        print(f"  Items WITH content (stuck): {len(has_content)}")
        print(f"  Items WITHOUT content (legitimate): {len(no_content)}")
        print(f"\n{'='*80}\n")
        
        # Show items WITH content (these are stuck)
        if has_content:
            print(f"ITEMS WITH CONTENT (STUCK - should be 'processed'):")
            print(f"{'-'*80}")
            for idx, item in enumerate(has_content, 1):
                content_length = len(item.get('archived_text', ''))
                title = item.get('title', 'No title')
                print(f"\n{idx}. ID: {item['_id']}")
                print(f"   URL: {item.get('url', 'N/A')}")
                print(f"   Title: {title[:60]}..." if len(title) > 60 else f"   Title: {title}")
                print(f"   Status: {item.get('processing_status', 'N/A')}")
                print(f"   Extraction Type: {item.get('extraction_type', 'N/A')}")
                print(f"   Content Length: {content_length:,} characters")
                print(f"   Created: {item.get('created_at', 'N/A')}")
                print(f"   Updated: {item.get('updated_at', 'N/A')}")
                
                # Check if it has chunks
                chunk_count = await db.item_chunks.count_documents({"item_id": str(item['_id'])})
                if chunk_count > 0:
                    print(f"   Chunks: {chunk_count} chunks exist")
                
        print(f"\n{'='*80}\n")
        
        # Show items WITHOUT content (legitimate queue items)
        if no_content:
            print(f"ITEMS WITHOUT CONTENT (LEGITIMATE - need local extraction):")
            print(f"{'-'*80}")
            for idx, item in enumerate(no_content, 1):
                title = item.get('title', 'No title')
                print(f"\n{idx}. ID: {item['_id']}")
                print(f"   URL: {item.get('url', 'N/A')}")
                print(f"   Title: {title[:60]}..." if len(title) > 60 else f"   Title: {title}")
                print(f"   Status: {item.get('processing_status', 'N/A')}")
                print(f"   Extraction Type: {item.get('extraction_type', 'N/A')}")
                print(f"   Created: {item.get('created_at', 'N/A')}")
                print(f"   Updated: {item.get('updated_at', 'N/A')}")
        
        print(f"\n{'='*80}\n")
        
        # Recommendations
        print("RECOMMENDATIONS:")
        print(f"{'-'*80}")
        if has_content:
            print(f"\n1. CLEAR STUCK ITEMS ({len(has_content)} items):")
            print(f"   These items have content but are stuck in pending status.")
            print(f"   Run: python3 backend/clear_local_queue.py --clear-stuck")
            print(f"   This will update their status to 'processed'")
        
        if no_content:
            print(f"\n2. LEGITIMATE QUEUE ITEMS ({len(no_content)} items):")
            print(f"   These items need local extraction from the browser extension.")
            print(f"   Options:")
            print(f"   - Keep them in queue and extract via browser extension")
            print(f"   - Change to 'fast' or 'complete' extraction:")
            print(f"     python3 backend/clear_local_queue.py --change-type <item_id> <new_type>")
        
        print(f"\n{'='*80}\n")
        
        # Export item IDs for easy reference
        if has_content:
            print("STUCK ITEM IDs (for reference):")
            print(", ".join(str(item['_id']) for item in has_content))
            print()
        
        if no_content:
            print("LEGITIMATE ITEM IDs (for reference):")
            print(", ".join(str(item['_id']) for item in no_content))
            print()
        
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(investigate_local_queue())