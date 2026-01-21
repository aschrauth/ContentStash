"""
Cleanup script for local extraction queue items.
Clears stuck items that have content but are in pending status.
"""
import asyncio
import sys
import os
from datetime import datetime

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from bson import ObjectId

async def clear_stuck_items(dry_run=True):
    """Clear items that have content but are stuck in pending status."""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client.contentstash
    
    try:
        # Query items with local extraction type and pending status that have content
        query = {
            "extraction_type": "local",
            "processing_status": {"$in": ["pending", "pending_local_extraction"]},
            "archived_text": {"$exists": True, "$ne": "", "$ne": None}
        }
        
        cursor = db.saved_items.find(query)
        items = await cursor.to_list(length=None)
        
        # Filter to only items with actual content (not just whitespace)
        stuck_items = [
            item for item in items 
            if item.get('archived_text') and len(item.get('archived_text', '').strip()) > 0
        ]
        
        print(f"\n{'='*80}")
        print(f"CLEAR STUCK LOCAL EXTRACTION ITEMS")
        print(f"{'='*80}\n")
        
        if not stuck_items:
            print("No stuck items found. All items in queue are legitimate.")
            return
        
        print(f"Found {len(stuck_items)} stuck items with content.\n")
        
        if dry_run:
            print("DRY RUN MODE - No changes will be made")
            print("Run with --execute to actually clear the items\n")
        else:
            print("EXECUTE MODE - Items will be updated\n")
        
        # Show what will be updated
        print(f"Items to update:")
        print(f"{'-'*80}")
        for idx, item in enumerate(stuck_items, 1):
            title = item.get('title', 'No title')
            content_length = len(item.get('archived_text', ''))
            print(f"{idx}. {item['_id']} - {title[:50]}... ({content_length:,} chars)")
        
        print(f"\n{'-'*80}\n")
        
        if not dry_run:
            # Update all stuck items to "processed" status
            item_ids = [item['_id'] for item in stuck_items]
            
            result = await db.saved_items.update_many(
                {"_id": {"$in": item_ids}},
                {
                    "$set": {
                        "processing_status": "processed",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            print(f"✅ Updated {result.modified_count} items to 'processed' status")
            print(f"   These items are now removed from the local extraction queue.\n")
        else:
            print(f"Would update {len(stuck_items)} items to 'processed' status")
            print(f"Run: python3 backend/clear_local_queue.py --execute\n")
        
    finally:
        client.close()


async def change_extraction_type(item_id: str, new_type: str):
    """Change the extraction type for a specific item."""
    
    if new_type not in ["fast", "complete", "local"]:
        print(f"❌ Invalid extraction type: {new_type}")
        print(f"   Valid types: fast, complete, local")
        return
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client.contentstash
    
    try:
        # Convert string ID to ObjectId
        try:
            obj_id = ObjectId(item_id)
        except Exception as e:
            print(f"❌ Invalid item ID format: {item_id}")
            return
        
        # Find the item
        item = await db.saved_items.find_one({"_id": obj_id})
        
        if not item:
            print(f"❌ Item not found: {item_id}")
            return
        
        print(f"\n{'='*80}")
        print(f"CHANGE EXTRACTION TYPE")
        print(f"{'='*80}\n")
        print(f"Item: {item.get('title', 'No title')}")
        print(f"URL: {item.get('url', 'N/A')}")
        print(f"Current extraction type: {item.get('extraction_type', 'N/A')}")
        print(f"Current status: {item.get('processing_status', 'N/A')}")
        print(f"\nChanging to: {new_type}")
        
        # Update the item
        update_data = {
            "extraction_type": new_type,
            "updated_at": datetime.utcnow()
        }
        
        # If changing from local to fast/complete, also update status
        if new_type in ["fast", "complete"] and item.get('processing_status') in ["pending", "pending_local_extraction"]:
            update_data["processing_status"] = "pending"
        
        result = await db.saved_items.update_one(
            {"_id": obj_id},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            print(f"\n✅ Successfully updated extraction type to '{new_type}'")
            if new_type in ["fast", "complete"]:
                print(f"   Item will be processed by the backend extraction service.")
        else:
            print(f"\n⚠️  No changes made (item may already have this extraction type)")
        
    finally:
        client.close()


async def clear_specific_items(item_ids: list[str], dry_run=True):
    """Clear specific items by ID."""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client.contentstash
    
    try:
        # Convert string IDs to ObjectIds
        obj_ids = []
        for item_id in item_ids:
            try:
                obj_ids.append(ObjectId(item_id))
            except Exception as e:
                print(f"⚠️  Invalid item ID format: {item_id}")
        
        if not obj_ids:
            print("❌ No valid item IDs provided")
            return
        
        # Find the items
        cursor = db.saved_items.find({"_id": {"$in": obj_ids}})
        items = await cursor.to_list(length=None)
        
        print(f"\n{'='*80}")
        print(f"CLEAR SPECIFIC ITEMS")
        print(f"{'='*80}\n")
        
        if not items:
            print("❌ No items found with the provided IDs")
            return
        
        print(f"Found {len(items)} items:\n")
        
        for idx, item in enumerate(items, 1):
            title = item.get('title', 'No title')
            print(f"{idx}. {item['_id']} - {title[:50]}...")
            print(f"   Status: {item.get('processing_status', 'N/A')}")
            print(f"   Extraction type: {item.get('extraction_type', 'N/A')}")
        
        print()
        
        if dry_run:
            print("DRY RUN MODE - No changes will be made")
            print("Add --execute to actually clear these items\n")
        else:
            result = await db.saved_items.update_many(
                {"_id": {"$in": obj_ids}},
                {
                    "$set": {
                        "processing_status": "processed",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            print(f"✅ Updated {result.modified_count} items to 'processed' status\n")
        
    finally:
        client.close()


def print_usage():
    """Print usage instructions."""
    print(f"\n{'='*80}")
    print(f"LOCAL QUEUE CLEANUP SCRIPT")
    print(f"{'='*80}\n")
    print("Usage:")
    print("  1. Clear all stuck items (items with content but pending status):")
    print("     python3 backend/clear_local_queue.py --clear-stuck [--execute]")
    print()
    print("  2. Change extraction type for a specific item:")
    print("     python3 backend/clear_local_queue.py --change-type <item_id> <new_type>")
    print("     Example: python3 backend/clear_local_queue.py --change-type 69704561107cdc5e094be409 fast")
    print()
    print("  3. Clear specific items by ID:")
    print("     python3 backend/clear_local_queue.py --clear-ids <id1> <id2> ... [--execute]")
    print()
    print("Options:")
    print("  --execute    Actually perform the changes (default is dry-run)")
    print()
    print("Valid extraction types: fast, complete, local")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "--clear-stuck":
        dry_run = "--execute" not in sys.argv
        asyncio.run(clear_stuck_items(dry_run=dry_run))
    
    elif command == "--change-type":
        if len(sys.argv) < 4:
            print("❌ Missing arguments for --change-type")
            print("Usage: python3 backend/clear_local_queue.py --change-type <item_id> <new_type>")
            sys.exit(1)
        
        item_id = sys.argv[2]
        new_type = sys.argv[3]
        asyncio.run(change_extraction_type(item_id, new_type))
    
    elif command == "--clear-ids":
        if len(sys.argv) < 3:
            print("❌ Missing item IDs")
            print("Usage: python3 backend/clear_local_queue.py --clear-ids <id1> <id2> ... [--execute]")
            sys.exit(1)
        
        # Get all IDs (everything except --execute flag)
        item_ids = [arg for arg in sys.argv[2:] if arg != "--execute"]
        dry_run = "--execute" not in sys.argv
        asyncio.run(clear_specific_items(item_ids, dry_run=dry_run))
    
    else:
        print(f"❌ Unknown command: {command}")
        print_usage()
        sys.exit(1)