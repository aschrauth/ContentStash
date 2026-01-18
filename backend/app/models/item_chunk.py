from pydantic import BaseModel, Field, ConfigDict
from typing import List
from datetime import datetime
from bson import ObjectId


class ItemChunkBase(BaseModel):
    """Base item chunk schema with common fields"""
    item_id: str = Field(..., description="Reference to parent SavedItem")
    owner_id: str = Field(..., description="Owner ID for permissions/filtering")
    chunk_index: int = Field(..., ge=0, description="Order in original text (0-based)")
    text: str = Field(..., min_length=1, max_length=10000, description="Chunk content (~500 tokens)")
    embedding: List[float] = Field(..., description="768-dimensional embedding vector from text-embedding-004")


class ItemChunkCreate(ItemChunkBase):
    """Schema for creating a new item chunk"""
    pass


class ItemChunk(ItemChunkBase):
    """Item chunk schema for API responses"""
    id: str
    created_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class ItemChunkInDB(ItemChunk):
    """Item chunk schema as stored in database"""
    pass