#!/usr/bin/env python3
"""
Cleanup script for removing orphaned chunks from previously deleted articles.

This script:
1. Finds all chunks in item_chunks collection where the referenced item_id either:
   - Doesn't exist in the saved_items collection, OR
   - Points to a soft-deleted item (where archived_at is not null)
2. Deletes these orphaned chunks
3. Provides a summary of how many chunks were cleaned up

Usage:
    # Dry run to see what would be deleted
    python cleanup_orphaned_chunks.py --dry-run

    # Actually delete orphaned chunks
    python cleanup_orphaned_chunks.py
"""

import asyncio
import argparse
import logging
import sys
import time
from datetime import datetime
from typing import List, Dict, Any, Set
from bson import ObjectId

# Add parent directory to path for imports
sys.path.insert(0, '.')

from app.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class CleanupStats:
    """Track cleanup statistics"""
    def __init__(self):
        self.total_chunks = 0
        self.orphaned_no_item = 0
        self.orphaned_soft_deleted = 0
        self.deleted = 0
        self.start_time = None
        self.end_time = None
    
    @property
    def total_orphaned(self):
        return self.orphaned_no_item + self.orphaned_soft_deleted
    
    def print_summary(self):
        """Print cleanup summary"""
        duration = (self.end_time - self.start_time) if self.end_time and self.start_time else 0
        
        logger.info("=" * 60)
        logger.info("CLEANUP SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total chunks examined: {self.total_chunks}")
        logger.info(f"Orphaned (item doesn't exist): {self.orphaned_no_item}")
        logger.info(f"Orphaned (item soft-deleted): {self.orphaned_soft_deleted}")
        logger.info(f"Total orphaned chunks: {self.total_orphaned}")
        logger.info(f"Chunks deleted: {self.deleted}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("=" * 60)


async def find_orphaned_chunks(db, dry_run: bool = False) -> CleanupStats:
    """
    Find and optionally delete orphaned chunks.
    
    Args:
        db: Database instance
        dry_run: If True, don't delete anything
    
    Returns:
        CleanupStats object with results
    """
    stats = CleanupStats()
    stats.start_time = time.time()
    
    # Step 1: Get all unique item_ids from chunks
    chunks_collection = db.item_chunks
    logger.info("Finding all unique item_ids in chunks collection...")
    chunk_item_ids = await chunks_collection.distinct("item_id")
    stats.total_chunks = await chunks_collection.count_documents({})
    logger.info(f"Found {len(chunk_item_ids)} unique item_ids across {stats.total_chunks} chunks")
    
    # Step 2: Get all valid (non-deleted) item_ids from saved_items
    logger.info("Finding all valid items in saved_items collection...")
    valid_items = await db.saved_items.find(
        {"archived_at": None},
        {"_id": 1}
    ).to_list(length=None)
    valid_item_ids = {str(item["_id"]) for item in valid_items}
    logger.info(f"Found {len(valid_item_ids)} valid (non-deleted) items")
    
    # Step 3: Get all soft-deleted item_ids from saved_items
    logger.info("Finding all soft-deleted items in saved_items collection...")
    deleted_items = await db.saved_items.find(
        {"archived_at": {"$ne": None}},
        {"_id": 1}
    ).to_list(length=None)
    deleted_item_ids = {str(item["_id"]) for item in deleted_items}
    logger.info(f"Found {len(deleted_item_ids)} soft-deleted items")
    
    # Step 4: Get all existing item_ids (both valid and deleted)
    all_existing_item_ids = valid_item_ids | deleted_item_ids
    
    # Step 5: Identify orphaned chunks
    orphaned_item_ids: Set[str] = set()
    
    # Chunks pointing to non-existent items
    for item_id in chunk_item_ids:
        if item_id not in all_existing_item_ids:
            orphaned_item_ids.add(item_id)
            stats.orphaned_no_item += await chunks_collection.count_documents({"item_id": item_id})
    
    # Chunks pointing to soft-deleted items
    for item_id in chunk_item_ids:
        if item_id in deleted_item_ids:
            orphaned_item_ids.add(item_id)
            stats.orphaned_soft_deleted += await chunks_collection.count_documents({"item_id": item_id})
    
    logger.info(f"\nFound {len(orphaned_item_ids)} item_ids with orphaned chunks:")
    logger.info(f"  - {stats.orphaned_no_item} chunks from non-existent items")
    logger.info(f"  - {stats.orphaned_soft_deleted} chunks from soft-deleted items")
    logger.info(f"  - {stats.total_orphaned} total orphaned chunks")
    
    # Step 6: Delete orphaned chunks (if not dry run)
    if stats.total_orphaned > 0:
        if not dry_run:
            logger.info("\nDeleting orphaned chunks...")
            
            # Delete in batches to avoid memory issues
            batch_size = 100
            orphaned_list = list(orphaned_item_ids)
            
            for i in range(0, len(orphaned_list), batch_size):
                batch = orphaned_list[i:i + batch_size]
                result = await chunks_collection.delete_many({"item_id": {"$in": batch}})
                stats.deleted += result.deleted_count
                logger.info(f"  Deleted {result.deleted_count} chunks (batch {i//batch_size + 1})")
            
            logger.info(f"\n✓ Successfully deleted {stats.deleted} orphaned chunks")
        else:
            logger.info("\n[DRY RUN] Would delete the following:")
            
            # Show sample of what would be deleted
            sample_size = min(10, len(orphaned_item_ids))
            sample_ids = list(orphaned_item_ids)[:sample_size]
            
            for item_id in sample_ids:
                chunk_count = await chunks_collection.count_documents({"item_id": item_id})
                exists = item_id in all_existing_item_ids
                is_deleted = item_id in deleted_item_ids
                
                status = "soft-deleted" if is_deleted else "non-existent"
                logger.info(f"  - item_id: {item_id} ({status}) - {chunk_count} chunks")
            
            if len(orphaned_item_ids) > sample_size:
                logger.info(f"  ... and {len(orphaned_item_ids) - sample_size} more item_ids")
            
            logger.info(f"\n[DRY RUN] Would delete {stats.total_orphaned} total chunks")
    else:
        logger.info("\n✓ No orphaned chunks found - database is clean!")
    
    stats.end_time = time.time()
    return stats


async def cleanup_orphaned_chunks(dry_run: bool = False):
    """
    Main cleanup function.
    
    Args:
        dry_run: If True, don't make any changes
    """
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
    
    if dry_run:
        logger.info("=" * 60)
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info("=" * 60)
    
    try:
        # Find and delete orphaned chunks
        stats = await find_orphaned_chunks(db, dry_run=dry_run)
        stats.print_summary()
        
    except KeyboardInterrupt:
        logger.info("\n\nCleanup interrupted by user")
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}", exc_info=True)
    finally:
        mongodb_client.close()
        logger.info("MongoDB connection closed")


def main():
    """Parse arguments and run cleanup"""
    parser = argparse.ArgumentParser(
        description="Clean up orphaned chunks from deleted items",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be deleted
  python cleanup_orphaned_chunks.py --dry-run

  # Actually delete orphaned chunks
  python cleanup_orphaned_chunks.py
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be deleted without making changes'
    )
    
    args = parser.parse_args()
    
    # Run cleanup
    asyncio.run(cleanup_orphaned_chunks(dry_run=args.dry_run))


if __name__ == "__main__":
    main()