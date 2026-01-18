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
        print("✅ Text search index created/verified on saved_items collection")
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


async def ping_database() -> bool:
    """Ping the database to check connection"""
    try:
        if mongodb_client is None:
            return False
        await mongodb_client.admin.command('ping')
        return True
    except Exception:
        return False