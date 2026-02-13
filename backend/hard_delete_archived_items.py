#!/usr/bin/env python3
"""
Permanently delete legacy archived items and clean related vector chunks.

This script:
1. Finds saved_items where archived_at is not null (legacy archived records)
2. Deletes their associated chunks from item_chunks
3. Deletes the archived items from saved_items
4. Deletes orphaned chunks whose item_id no longer exists in saved_items

Usage:
    # See what would be deleted
    python hard_delete_archived_items.py --dry-run

    # Execute cleanup
    python hard_delete_archived_items.py --execute
"""

import argparse
import asyncio
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Set

from motor.motor_asyncio import AsyncIOMotorClient

# Add backend directory for imports, regardless of current working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.config import settings  # noqa: E402

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@dataclass
class CleanupStats:
    archived_items_found: int = 0
    archived_chunks_found: int = 0
    archived_items_deleted: int = 0
    archived_chunks_deleted: int = 0
    orphaned_chunks_found: int = 0
    orphaned_chunks_deleted: int = 0
    duration_seconds: float = 0.0

    def log_summary(self) -> None:
        logger.info("=" * 60)
        logger.info("HARD DELETE CLEANUP SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Archived items found: {self.archived_items_found}")
        logger.info(f"Chunks linked to archived items: {self.archived_chunks_found}")
        logger.info(f"Archived items deleted: {self.archived_items_deleted}")
        logger.info(f"Chunks deleted for archived items: {self.archived_chunks_deleted}")
        logger.info(f"Orphaned chunks found: {self.orphaned_chunks_found}")
        logger.info(f"Orphaned chunks deleted: {self.orphaned_chunks_deleted}")
        logger.info(f"Duration: {self.duration_seconds:.2f}s")
        logger.info("=" * 60)


async def cleanup(dry_run: bool) -> CleanupStats:
    start = time.time()
    stats = CleanupStats()

    logger.info("Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.mongodb_uri)
    db = client.contentstash

    try:
        await client.admin.command("ping")
        logger.info("Connected to MongoDB")

        # 1) Find legacy archived items
        archived_docs = await db.saved_items.find(
            {"archived_at": {"$ne": None}},
            {"_id": 1},
        ).to_list(length=None)
        archived_item_ids = [str(doc["_id"]) for doc in archived_docs]
        stats.archived_items_found = len(archived_item_ids)

        if archived_item_ids:
            stats.archived_chunks_found = await db.item_chunks.count_documents(
                {"item_id": {"$in": archived_item_ids}}
            )
        else:
            stats.archived_chunks_found = 0

        logger.info(
            "Found %d archived items and %d related chunks",
            stats.archived_items_found,
            stats.archived_chunks_found,
        )

        # 2) Delete chunks + archived items
        if not dry_run and archived_item_ids:
            chunks_result = await db.item_chunks.delete_many(
                {"item_id": {"$in": archived_item_ids}}
            )
            items_result = await db.saved_items.delete_many(
                {"_id": {"$in": [doc["_id"] for doc in archived_docs]}}
            )
            stats.archived_chunks_deleted = chunks_result.deleted_count
            stats.archived_items_deleted = items_result.deleted_count

        # 3) Delete orphaned chunks (chunks with no matching saved item)
        existing_item_ids: Set[str] = set(
            str(doc["_id"])
            for doc in await db.saved_items.find({}, {"_id": 1}).to_list(length=None)
        )
        chunk_item_ids = set(await db.item_chunks.distinct("item_id"))
        orphaned_item_ids = chunk_item_ids - existing_item_ids

        if orphaned_item_ids:
            stats.orphaned_chunks_found = await db.item_chunks.count_documents(
                {"item_id": {"$in": list(orphaned_item_ids)}}
            )
        else:
            stats.orphaned_chunks_found = 0

        logger.info(
            "Found %d orphaned chunk records",
            stats.orphaned_chunks_found,
        )

        if not dry_run and orphaned_item_ids:
            orphaned_result = await db.item_chunks.delete_many(
                {"item_id": {"$in": list(orphaned_item_ids)}}
            )
            stats.orphaned_chunks_deleted = orphaned_result.deleted_count

    finally:
        client.close()

    stats.duration_seconds = time.time() - start
    return stats


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hard-delete archived items and clean related chunks."
    )
    mode = parser.add_mutually_exclusive_group(required=False)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted (default mode).",
    )
    mode.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the deletion.",
    )
    return parser.parse_args()


async def main_async() -> int:
    args = parse_args()
    dry_run = not args.execute

    if dry_run:
        logger.info("Running in DRY RUN mode. No data will be deleted.")
    else:
        logger.info("Running in EXECUTE mode. Deletions will be permanent.")

    stats = await cleanup(dry_run=dry_run)
    stats.log_summary()
    return 0


def main() -> None:
    try:
        raise SystemExit(asyncio.run(main_async()))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        raise SystemExit(130)


if __name__ == "__main__":
    main()
