#!/usr/bin/env python3
"""
Script to manually trigger processing of the stuck item
"""
import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()

async def fix_stuck_item():
    """Manually trigger processing of stuck item by resetting its status"""
    
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        print("ERROR: MONGODB_URI not found in environment")
        return
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client.contentstash
    collection = db.saved_items
    
    try:
        # The stuck item ID from our investigation
        stuck_item_id = "69704561107cdc5e094be409"
        
        print(f"\n{'='*80}")
        print(f"FIXING STUCK ITEM: {stuck_item_id}")
        print(f"{'='*80}\n")
        
        # Get the item
        item = await collection.find_one({"_id": ObjectId(stuck_item_id)})
        
        if not item:
            print(f"ERROR: Item {stuck_item_id} not found!")
            return
        
        print(f"Current status: {item.get('processing_status')}")
        print(f"Current error: {item.get('processing_error')}")
        print(f"Extraction type: {item.get('extraction_type')}")
        print(f"URL: {item.get('url')}")
        
        # Option 1: Reset to pending to trigger Chrome extension processing again
        print(f"\n{'='*80}")
        print("OPTION 1: Reset to 'pending' for Chrome extension retry")
        print(f"{'='*80}\n")
        
        result = await collection.update_one(
            {"_id": ObjectId(stuck_item_id)},
            {
                "$set": {
                    "processing_status": "pending",
                    "processing_error": "Manually reset for retry",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            print("✓ Successfully reset item to 'pending' status")
            print("  The Chrome extension should pick it up on next poll")
            print("  Or click 'Process Now' in the extension popup")
        else:
            print("✗ Failed to update item")
        
        # Show updated item
        updated_item = await collection.find_one({"_id": ObjectId(stuck_item_id)})
        print(f"\nUpdated status: {updated_item.get('processing_status')}")
        print(f"Updated error: {updated_item.get('processing_error')}")
        
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(fix_stuck_item())