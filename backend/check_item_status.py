import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

async def check_item():
    # Connect to MongoDB
    client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
    db = client[os.getenv("MONGODB_DB_NAME", "contentstash")]
    
    item_id = "69714fcd34076acd126d2d3f"
    
    # Fetch the item
    item = await db.saved_items.find_one({"_id": ObjectId(item_id)})
    
    if item:
        print(f"Item ID: {item_id}")
        print(f"Title: {item.get('title')}")
        print(f"URL: {item.get('url')}")
        print(f"Extraction Type: {item.get('extraction_type')}")
        print(f"Processing Status: {item.get('processing_status')}")
        print(f"Processing Error: {item.get('processing_error')}")
        print(f"Has archived_text: {bool(item.get('archived_text'))}")
        if item.get('archived_text'):
            print(f"Archived text length: {len(item.get('archived_text', ''))}")
    else:
        print(f"Item {item_id} not found")
    
    # Check pending-local query
    print("\n--- Checking pending-local query ---")
    pending_items = await db.saved_items.find({
        "extraction_type": "local",
        "processing_status": {"$in": ["pending", "pending_local_extraction"]},
        "archived_at": None
    }).to_list(length=None)
    
    print(f"Total pending local items: {len(pending_items)}")
    for item in pending_items[:5]:  # Show first 5
        print(f"  - {item['_id']}: {item.get('title', 'No title')} - Status: {item.get('processing_status')}")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_item())