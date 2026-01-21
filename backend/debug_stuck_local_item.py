#!/usr/bin/env python3
"""
Diagnostic script to investigate stuck local extraction item
"""
import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import os
from dotenv import load_dotenv
import json

load_dotenv()

async def investigate_stuck_item():
    """Query and display details of stuck local extraction item"""
    
    # Connect to MongoDB
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        print("ERROR: MONGODB_URI not found in environment")
        return
    
    client = AsyncIOMotorClient(mongo_uri)
    db = client.contentstash
    collection = db.saved_items
    
    try:
        # Get the stuck item(s)
        print("\n" + "="*80)
        print("STUCK LOCAL EXTRACTION ITEMS")
        print("="*80 + "\n")
        
        query = {
            "extraction_type": "local",
            "processing_status": {"$in": ["pending", "pending_local_extraction"]},
            "archived_at": None
        }
        
        cursor = collection.find(query).sort("created_at", -1)
        items = await cursor.to_list(length=None)
        
        print(f"Found {len(items)} stuck item(s)\n")
        
        for idx, item in enumerate(items, 1):
            print(f"\n{'='*80}")
            print(f"STUCK ITEM #{idx}")
            print(f"{'='*80}\n")
            
            print(f"ID: {item.get('_id')}")
            print(f"URL: {item.get('url')}")
            print(f"Title: {item.get('title')}")
            print(f"Processing Status: {item.get('processing_status')}")
            print(f"Processing Error: {item.get('processing_error')}")
            print(f"Extraction Type: {item.get('extraction_type')}")
            print(f"Created At: {item.get('created_at')}")
            print(f"Updated At: {item.get('updated_at')}")
            print(f"Has Content (archived_text): {bool(item.get('archived_text'))}")
            print(f"Content Length: {len(item.get('archived_text', ''))}")
            
            if item.get('archived_text'):
                print(f"\nContent Preview (first 300 chars):")
                print(f"{item.get('archived_text')[:300]}...")
            
            print(f"\n{'='*80}")
            print("FULL DOCUMENT")
            print(f"{'='*80}\n")
            print(json.dumps({k: str(v) if not isinstance(v, (str, int, bool, list, dict, type(None))) else v 
                            for k, v in item.items()}, indent=2))
    
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(investigate_stuck_item())