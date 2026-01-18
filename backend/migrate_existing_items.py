#!/usr/bin/env python3
"""
Migration script for processing existing items that don't have chunks/embeddings yet.

This script:
1. Finds all SavedItems that don't have chunks in the item_chunks collection
2. For each item with archived_text:
   - Chunks the text
   - Generates embeddings
   - Stores chunks in item_chunks collection
   - Generates auto-categorization (tags, topic, summary)
   - Updates the SavedItem with new fields
3. Handles errors gracefully and provides progress reporting

Usage:
    # Dry run to see what would be processed
    python migrate_existing_items.py --dry-run

    # Process all items
    python migrate_existing_items.py

    # Process first 50 items only
    python migrate_existing_items.py --limit 50

    # Process in batches of 5
    python migrate_existing_items.py --batch-size 5

    # Skip AI categorization (only chunk and embed)
    python migrate_existing_items.py --skip-categorization
"""

import asyncio
import argparse
import logging
import sys
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId

# Add parent directory to path for imports
sys.path.insert(0, '.')

from app.database import get_database, get_item_chunks_collection
from app.services.chunking import chunk_text
from app.services.gemini import gemini_service, GeminiServiceError, GeminiRateLimitError
from app.services.background import generate_auto_categorization
from app.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class MigrationStats:
    """Track migration statistics"""
    def __init__(self):
        self.total_items = 0
        self.processed = 0
        self.skipped_no_text = 0
        self.skipped_has_chunks = 0
        self.failed = 0
        self.start_time = None
        self.end_time = None
    
    def print_summary(self):
        """Print migration summary"""
        duration = (self.end_time - self.start_time) if self.end_time and self.start_time else 0
        
        logger.info("=" * 60)
        logger.info("MIGRATION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total items found: {self.total_items}")
        logger.info(f"Successfully processed: {self.processed}")
        logger.info(f"Skipped (no archived_text): {self.skipped_no_text}")
        logger.info(f"Skipped (already has chunks): {self.skipped_has_chunks}")
        logger.info(f"Failed: {self.failed}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("=" * 60)


async def find_items_without_chunks(db, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Find all SavedItems that don't have chunks in item_chunks collection.
    
    Args:
        db: Database instance
        limit: Optional limit on number of items to return
    
    Returns:
        List of item documents that need processing
    """
    logger.info("Finding items without chunks...")
    
    # Get all item IDs that have chunks
    chunks_collection = get_item_chunks_collection()
    items_with_chunks = await chunks_collection.distinct("item_id")
    items_with_chunks_set = set(items_with_chunks)
    
    logger.info(f"Found {len(items_with_chunks_set)} items that already have chunks")
    
    # Find items that don't have chunks
    query = {
        "_id": {"$nin": [ObjectId(item_id) if ObjectId.is_valid(item_id) else item_id 
                         for item_id in items_with_chunks_set]}
    }
    
    cursor = db.saved_items.find(query)
    if limit:
        cursor = cursor.limit(limit)
    
    items = await cursor.to_list(length=None)
    logger.info(f"Found {len(items)} items without chunks")
    
    return items


async def process_single_item(
    db,
    item: Dict[str, Any],
    dry_run: bool = False,
    skip_categorization: bool = False
) -> bool:
    """
    Process a single item: chunk, embed, and categorize.
    
    Args:
        db: Database instance
        item: Item document to process
        dry_run: If True, don't make any changes
        skip_categorization: If True, skip AI categorization
    
    Returns:
        True if successful, False otherwise
    """
    item_id = str(item["_id"])
    owner_id = str(item["owner_id"])
    archived_text = item.get("archived_text")
    
    # Check if item has archived_text
    if not archived_text or len(archived_text.strip()) < 50:
        logger.warning(f"Item {item_id} has no archived_text or text too short, skipping")
        return False
    
    try:
        logger.info(f"Processing item {item_id} ({len(archived_text)} chars)")
        
        # Step 1: Chunk the text
        logger.info(f"  Chunking text...")
        chunks = chunk_text(archived_text, chunk_size=500, overlap=75)
        logger.info(f"  Created {len(chunks)} chunks")
        
        if not chunks:
            logger.warning(f"  No chunks created for item {item_id}")
            return False
        
        # Step 2: Generate embeddings
        if not gemini_service.is_available():
            logger.error("  Gemini service not available, cannot generate embeddings")
            return False
        
        logger.info(f"  Generating embeddings for {len(chunks)} chunks...")
        try:
            embeddings = gemini_service.embed_batch(chunks)
        except GeminiRateLimitError as e:
            logger.error(f"  Rate limit exceeded: {str(e)}")
            logger.info("  Waiting 60 seconds before retrying...")
            await asyncio.sleep(60)
            # Retry once
            embeddings = gemini_service.embed_batch(chunks)
        
        if len(embeddings) != len(chunks):
            logger.error(
                f"  Embedding count mismatch: {len(embeddings)} embeddings "
                f"for {len(chunks)} chunks"
            )
            return False
        
        logger.info(f"  Successfully generated {len(embeddings)} embeddings")
        
        # Step 3: Store chunks (if not dry run)
        if not dry_run:
            chunks_collection = get_item_chunks_collection()
            
            # Prepare chunk documents
            chunk_docs = []
            for idx, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_doc = {
                    "item_id": item_id,
                    "owner_id": owner_id,
                    "chunk_index": idx,
                    "text": chunk_text,
                    "embedding": embedding,
                    "created_at": datetime.utcnow()
                }
                chunk_docs.append(chunk_doc)
            
            # Delete any existing chunks for this item (safety check)
            await chunks_collection.delete_many({"item_id": item_id})
            
            # Insert new chunks
            result = await chunks_collection.insert_many(chunk_docs)
            logger.info(f"  Stored {len(result.inserted_ids)} chunks in database")
        else:
            logger.info(f"  [DRY RUN] Would store {len(chunks)} chunks")
        
        # Step 4: Generate auto-categorization (if not skipped)
        auto_categorization = None
        if not skip_categorization:
            logger.info(f"  Generating auto-categorization...")
            try:
                auto_categorization = generate_auto_categorization(archived_text)
                if auto_categorization:
                    logger.info(
                        f"  Generated: {len(auto_categorization.get('suggested_tags', []))} tags, "
                        f"topic='{auto_categorization.get('topic', '')[:30]}...'"
                    )
                else:
                    logger.warning(f"  Auto-categorization returned None")
            except GeminiRateLimitError as e:
                logger.error(f"  Rate limit during categorization: {str(e)}")
                logger.info("  Waiting 60 seconds before retrying...")
                await asyncio.sleep(60)
                # Retry once
                auto_categorization = generate_auto_categorization(archived_text)
            except Exception as e:
                logger.error(f"  Error during auto-categorization: {str(e)}")
        else:
            logger.info(f"  Skipping auto-categorization (--skip-categorization flag)")
        
        # Step 5: Update SavedItem (if not dry run)
        if not dry_run:
            update_doc = {
                "processing_status": "processed",
                "updated_at": datetime.utcnow()
            }
            
            # Add auto-categorization results if available
            if auto_categorization:
                if auto_categorization.get("suggested_tags"):
                    update_doc["suggested_tags"] = auto_categorization["suggested_tags"]
                if auto_categorization.get("topic"):
                    update_doc["suggested_topic"] = auto_categorization["topic"]
                if auto_categorization.get("summary"):
                    update_doc["ai_summary"] = auto_categorization["summary"]
            
            await db.saved_items.update_one(
                {"_id": ObjectId(item_id)},
                {"$set": update_doc}
            )
            logger.info(f"  Updated SavedItem with categorization results")
        else:
            logger.info(f"  [DRY RUN] Would update SavedItem with categorization")
        
        logger.info(f"✓ Successfully processed item {item_id}")
        return True
        
    except GeminiServiceError as e:
        logger.error(f"✗ Gemini service error for item {item_id}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"✗ Unexpected error processing item {item_id}: {str(e)}", exc_info=True)
        return False


async def migrate_items(
    batch_size: int = 10,
    limit: Optional[int] = None,
    dry_run: bool = False,
    skip_categorization: bool = False
):
    """
    Main migration function.
    
    Args:
        batch_size: Number of items to process in each batch
        limit: Maximum number of items to process (None = all)
        dry_run: If True, don't make any changes
        skip_categorization: If True, skip AI categorization
    """
    stats = MigrationStats()
    stats.start_time = time.time()
    
    # Connect to MongoDB
    logger.info("Connecting to MongoDB...")
    mongodb_client = AsyncIOMotorClient(settings.mongodb_uri)
    
    try:
        # Test connection
        await mongodb_client.admin.command('ping')
        logger.info("✓ Connected to MongoDB")
    except Exception as e:
        logger.error(f"✗ Failed to connect to MongoDB: {str(e)}")
        return
    
    db = mongodb_client.contentstash
    
    # Check Gemini service
    if not gemini_service.is_available():
        logger.error("✗ Gemini service is not available. Please configure GEMINI_API_KEY.")
        mongodb_client.close()
        return
    
    logger.info("✓ Gemini service is available")
    
    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info("=" * 60)
    
    try:
        # Find items without chunks
        items = await find_items_without_chunks(db, limit=limit)
        stats.total_items = len(items)
        
        if stats.total_items == 0:
            logger.info("No items to process!")
            return
        
        logger.info(f"Starting migration of {stats.total_items} items...")
        logger.info(f"Batch size: {batch_size}")
        if limit:
            logger.info(f"Limit: {limit}")
        
        # Process items in batches
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(items) + batch_size - 1) // batch_size
            
            logger.info(f"\n--- Batch {batch_num}/{total_batches} ({len(batch)} items) ---")
            
            for item in batch:
                # Check if item has archived_text
                if not item.get("archived_text") or len(item.get("archived_text", "").strip()) < 50:
                    stats.skipped_no_text += 1
                    logger.info(f"Skipping item {item['_id']} (no archived_text)")
                    continue
                
                # Process the item
                success = await process_single_item(
                    db,
                    item,
                    dry_run=dry_run,
                    skip_categorization=skip_categorization
                )
                
                if success:
                    stats.processed += 1
                else:
                    stats.failed += 1
                
                # Progress update every 10 items
                total_done = stats.processed + stats.skipped_no_text + stats.failed
                if total_done % 10 == 0:
                    logger.info(
                        f"Progress: {total_done}/{stats.total_items} items "
                        f"({stats.processed} processed, {stats.failed} failed)"
                    )
            
            # Small delay between batches to avoid rate limits
            if i + batch_size < len(items):
                logger.info("Waiting 2 seconds before next batch...")
                await asyncio.sleep(2)
        
    except KeyboardInterrupt:
        logger.info("\n\nMigration interrupted by user")
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}", exc_info=True)
    finally:
        stats.end_time = time.time()
        stats.print_summary()
        mongodb_client.close()
        logger.info("MongoDB connection closed")


def main():
    """Parse arguments and run migration"""
    parser = argparse.ArgumentParser(
        description="Migrate existing items to add chunks and embeddings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be processed
  python migrate_existing_items.py --dry-run

  # Process all items
  python migrate_existing_items.py

  # Process first 50 items only
  python migrate_existing_items.py --limit 50

  # Process in batches of 5
  python migrate_existing_items.py --batch-size 5

  # Skip AI categorization (only chunk and embed)
  python migrate_existing_items.py --skip-categorization
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be processed without making changes'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=10,
        help='Number of items to process in each batch (default: 10)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Only process first N items (for testing)'
    )
    
    parser.add_argument(
        '--skip-categorization',
        action='store_true',
        help='Skip AI categorization (only chunk and embed)'
    )
    
    args = parser.parse_args()
    
    # Validate batch size
    if args.batch_size < 1:
        logger.error("Batch size must be at least 1")
        sys.exit(1)
    
    # Run migration
    asyncio.run(migrate_items(
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run,
        skip_categorization=args.skip_categorization
    ))


if __name__ == "__main__":
    main()