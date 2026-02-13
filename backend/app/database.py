from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from .config import settings

# Global MongoDB client
mongodb_client: Optional[AsyncIOMotorClient] = None


async def connect_to_mongo():
    """Connect to MongoDB"""
    global mongodb_client
    try:
        mongodb_client = AsyncIOMotorClient(settings.mongodb_uri)
        # Test the connection
        await mongodb_client.admin.command('ping')
        print("✅ Successfully connected to MongoDB")
        
        # Create text index on saved_items collection for full-text search
        db = mongodb_client.contentstash
        await db.saved_items.create_index([
            ("title", "text"),
            ("description", "text"),
            ("notes_markdown", "text"),
            ("tags", "text"),
            ("archived_text", "text")
        ], name="text_search_index")
        
        # Performance index for library listing and pagination.
        # We sort by created_at DESC, _id DESC.
        await db.saved_items.create_index([
            ("owner_id", 1),
            ("created_at", -1),
            ("_id", -1)
        ], name="library_list_index_v3")

        # Remove legacy index from archived-item filtering era.
        try:
            await db.saved_items.drop_index("library_list_index_v2")
        except Exception:
            # Index may not exist in all environments.
            pass
        
        # Index for real-time status stream
        await db.saved_items.create_index([
            ("owner_id", 1),
            ("processing_status", 1)
        ], name="status_stream_index")
        
        # Index for chunk lookups in RAG
        await db.item_chunks.create_index([
            ("item_id", 1)
        ], name="chunk_item_id_index")
        
        print("✅ Database indexes created/verified")
    except Exception as e:
        print(f"⚠️  Warning: Could not connect to MongoDB: {e}")
        print("⚠️  Server will start but database operations will fail")
        # Don't raise - allow server to start without DB connection


async def close_mongo_connection():
    """Close MongoDB connection"""
    global mongodb_client
    if mongodb_client:
        mongodb_client.close()
        print("✅ MongoDB connection closed")


def get_database():
    """Get the database instance"""
    if mongodb_client is None:
        raise Exception("Database not connected")
    return mongodb_client.contentstash


def get_item_chunks_collection():
    """Get the item_chunks collection"""
    db = get_database()
    return db.item_chunks


async def ping_database() -> bool:
    """Ping the database to check connection"""
    try:
        if mongodb_client is None:
            return False
        await mongodb_client.admin.command('ping')
        return True
    except Exception:
        return False
