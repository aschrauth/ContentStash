import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

async def fix_stuck_item():
    # Connect to MongoDB
    client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("MONGODB_DB_NAME", "contentstash")]
    
    item_id = "69714fcd34076acd126d2d3f"
    
    # Update the item to mark it as processed since it already has content
    result = await db.saved_items.update_one(
        {"_id": ObjectId(item_id)},
        {
            "$set": {
                "processing_status": "processed",
                "processing_error": None,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    print(f"Updated item {item_id}: matched={result.matched_count}, modified={result.modified_count}")
    
    # Check the result
    item = await db.saved_items.find_one({"_id": ObjectId(item_id)})
    print(f"Item status is now: {item.get('processing_status')}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(fix_stuck_item())