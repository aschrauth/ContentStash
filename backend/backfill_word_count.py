
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

# Hardcoded for verification
MONGODB_URI = ""

async def backfill_word_counts():
    """
    Iterate over all SavedItems and populate word_count if missing.
    """
    print("Connecting to database...")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.contentstash # Explicitly use 'contentstash' db
    
    print(f"Connected to database: {db.name}")
    print("Starting backfill of word counts...")
    
    # Find items without word_count
    cursor = db.saved_items.find({"word_count": {"$exists": False}})
    
    count = 0
    updated_count = 0
    
    async for item in cursor:
        count += 1
        word_count = 0
        
        # Calculate word count based on available fields
        if item.get("archived_text"):
            word_count = len(item["archived_text"].split())
        elif item.get("notes_markdown"):
            word_count = len(item["notes_markdown"].split())
        elif item.get("description"):
            # Fallback to description
            word_count = len(item["description"].split())
            
        # Update item
        await db.saved_items.update_one(
            {"_id": item["_id"]},
            {"$set": {"word_count": word_count}}
        )
        updated_count += 1
        
        if count % 100 == 0:
            print(f"Processed {count} items...")
            
    print(f"Backfill complete. Processed {count} items. Updated {updated_count} items.")

if __name__ == "__main__":
    try:
        asyncio.run(backfill_word_counts())
    except ImportError:
        print("Error: 'motor' module not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
