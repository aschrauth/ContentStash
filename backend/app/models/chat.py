from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from bson import ObjectId


class Citation(BaseModel):
    """Citation reference to a saved item"""
    id: str
    title: str
    excerpt: str = Field(..., max_length=500)


class ChatMessage(BaseModel):
    """Individual chat message in a thread"""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., max_length=10000)
    citations: Optional[List[Citation]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatThread(BaseModel):
    """Chat thread containing multiple messages"""
    id: str
    owner_id: str
    title: str = Field(..., max_length=200)
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class ChatThreadInDB(ChatThread):
    """Chat thread schema as stored in database"""
    pass


class CreateThreadRequest(BaseModel):
    """Request to create a new chat thread"""
    message: str = Field(..., min_length=1, max_length=10000)


class CreateMessageRequest(BaseModel):
    """Request to add a message to an existing thread"""
    message: str = Field(..., min_length=1, max_length=10000)


class ChatThreadResponse(BaseModel):
    """Response containing a chat thread"""
    id: str
    owner_id: str
    title: str
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime


class ChatThreadListItem(BaseModel):
    """Simplified thread info for list view"""
    id: str
    title: str
    preview: str = Field(..., max_length=200)
    message_count: int
    created_at: datetime
    updated_at: datetime