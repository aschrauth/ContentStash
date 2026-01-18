from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, _):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, _schema_generator):
        return {"type": "string"}


class UserPreferences(BaseModel):
    """User preferences schema"""
    view_mode: str = Field(default="list", pattern="^(grid|list)$")
    sort_order: str = Field(default="newest", pattern="^(newest|oldest|title)$")


class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    name: str = Field(..., min_length=2)


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8)


class User(UserBase):
    """User schema for API responses (without password)"""
    id: str
    preferences: UserPreferences = Field(default_factory=UserPreferences)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str}
    )


class UserInDB(User):
    """User schema as stored in database (with password hash)"""
    password_hash: str


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    name: Optional[str] = Field(None, min_length=2)
    email: Optional[EmailStr] = None
    preferences: Optional[UserPreferences] = None


class AuthResponse(BaseModel):
    """Schema for authentication responses"""
    user: User
    token: str