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
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        raise


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