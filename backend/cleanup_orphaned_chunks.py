#!/usr/bin/env python3
"""
Cleanup script for orphaned vector chunks.

This script:
1. Finds chunk records in `item_chunks` whose `item_id` no longer exists in `saved_items`
2. Optionally deletes those orphaned chunks
3. Prints a summary

Usage:
    python cleanup_orphaned_chunks.py --dry-run
    python cleanup_orphaned_chunks.py
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Set

from motor.motor_asyncio import AsyncIOMotorClient

# Add backend directory for imports, regardless of current working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.config import settings  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


async def find_orphaned_item_ids(db) -> Set[str]:
    """Return item_ids in item_chunks that do not exist in saved_items."""
    chunk_item_ids = set(await db.item_chunks.distinct("item_id"))
    existing_item_ids = {
        str(doc["_id"])
        for doc in await db.saved_items.find({}, {"_id": 1}).to_list(length=None)
    }
    return chunk_item_ids - existing_item_ids


async def cleanup_orphaned_chunks(dry_run: bool = False) -> None:
    start = time.time()
    logger.info("Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.mongodb_uri)

    try:
        await client.admin.command("ping")
        logger.info("Connected to MongoDB")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return

    db = client.contentstash

    try:
        total_chunks = await db.item_chunks.count_documents({})
        orphaned_item_ids = await find_orphaned_item_ids(db)
        orphaned_count = (
            await db.item_chunks.count_documents({"item_id": {"$in": list(orphaned_item_ids)}})
            if orphaned_item_ids
            else 0
        )

        logger.info(f"Total chunks examined: {total_chunks}")
        logger.info(f"Orphaned item IDs found: {len(orphaned_item_ids)}")
        logger.info(f"Orphaned chunks found: {orphaned_count}")

        deleted_count = 0
        if orphaned_count > 0 and not dry_run:
            result = await db.item_chunks.delete_many({"item_id": {"$in": list(orphaned_item_ids)}})
            deleted_count = result.deleted_count
            logger.info(f"Deleted orphaned chunks: {deleted_count}")
        elif dry_run:
            logger.info("DRY RUN mode enabled. No chunks were deleted.")

        duration = time.time() - start
        logger.info("=" * 60)
        logger.info("CLEANUP SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total chunks examined: {total_chunks}")
        logger.info(f"Orphaned chunks found: {orphaned_count}")
        logger.info(f"Chunks deleted: {deleted_count}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info("=" * 60)
    finally:
        client.close()
        logger.info("MongoDB connection closed")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean up orphaned chunks from item_chunks.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be deleted without making changes",
    )
    args = parser.parse_args()
    asyncio.run(cleanup_orphaned_chunks(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
