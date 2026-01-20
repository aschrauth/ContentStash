from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from bson import ObjectId


class SavedItemBase(BaseModel):
    """Base saved item schema with common fields"""
    url: Optional[str] = None
    title: str = Field(..., max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    image_url: Optional[str] = None
    favicon_url: Optional[str] = None
    notes_markdown: Optional[str] = Field(None, max_length=50000)
    tags: List[str] = Field(default_factory=list, max_length=20)
    archived_text: Optional[str] = None
    extraction_type: Optional[str] = Field(default="fast", pattern="^(fast|complete)$")
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Validate that each tag is between 2-50 characters"""
        if v is None:
            return v
        for tag in v:
            if len(tag) < 2 or len(tag) > 50:
                raise ValueError(f"Tag '{tag}' must be between 2 and 50 characters")
        return v


class SavedItemCreate(SavedItemBase):
    """Schema for creating a new saved item"""
    pass


class SavedItemUpdate(BaseModel):
    """Schema for updating a saved item"""
    url: Optional[str] = None
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    image_url: Optional[str] = None
    favicon_url: Optional[str] = None
    notes_markdown: Optional[str] = Field(None, max_length=50000)
    tags: Optional[List[str]] = Field(None, max_length=20)
    archived_text: Optional[str] = None
    extraction_type: Optional[str] = Field(None, pattern="^(fast|complete)$")
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        """Validate that each tag is between 2-50 characters"""
        if v is None:
            return v
        for tag in v:
            if len(tag) < 2 or len(tag) > 50:
                raise ValueError(f"Tag '{tag}' must be between 2 and 50 characters")
        return v


class SavedItem(SavedItemBase):
    """Saved item schema for API responses"""
    id: str
    owner_id: str
    suggested_tags: Optional[List[str]] = None
    suggested_topic: Optional[str] = None
    ai_summary: Optional[str] = None
    processing_status: str = Field(default="pending", pattern="^(pending|processed|failed)$")
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    archived_at: Optional[datetime] = None

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class SavedItemInDB(SavedItem):
    """Saved item schema as stored in database"""
    pass