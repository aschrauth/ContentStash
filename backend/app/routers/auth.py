from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from datetime import datetime
from bson import ObjectId
from ..database import get_database
from ..models.user import UserCreate, User, UserInDB, AuthResponse, UserUpdate, UserPreferences
from ..utils.auth import hash_password, verify_password, create_access_token
from ..dependencies import get_current_user

router = APIRouter()


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate):
    """
    Register a new user.
    
    - Validates email uniqueness
    - Validates password length (min 8 chars)
    - Validates name length (min 2 chars)
    - Hashes password with Argon2
    - Returns user object and JWT token
    """
    db = get_database()
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    password_hash = hash_password(user_data.password)
    
    # Create user document
    now = datetime.utcnow()
    user_doc = {
        "email": user_data.email,
        "name": user_data.name,
        "password_hash": password_hash,
        "preferences": {
            "view_mode": "list",
            "sort_order": "newest"
        },
        "created_at": now,
        "updated_at": now
    }
    
    # Insert into database
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    # Create JWT token
    token = create_access_token(user_id)
    
    # Create response user object
    user = User(
        id=user_id,
        email=user_data.email,
        name=user_data.name,
        preferences=UserPreferences(**user_doc["preferences"]),
        created_at=now,
        updated_at=now
    )
    
    return AuthResponse(user=user, token=token)


class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr
    password: str


@router.post("/login", response_model=AuthResponse)
async def login(login_data: LoginRequest):
    """
    Authenticate a user.
    
    - Validates credentials
    - Returns user object and JWT token
    """
    email = login_data.email
    password = login_data.password
    db = get_database()
    
    # Find user by email
    user_doc = await db.users.find_one({"email": email})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Verify password
    if not verify_password(password, user_doc["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Create JWT token
    user_id = str(user_doc["_id"])
    token = create_access_token(user_id)
    
    # Create response user object
    user = User(
        id=user_id,
        email=user_doc["email"],
        name=user_doc["name"],
        preferences=UserPreferences(**user_doc.get("preferences", {})),
        created_at=user_doc["created_at"],
        updated_at=user_doc["updated_at"]
    )
    
    return AuthResponse(user=user, token=token)


@router.post("/logout")
async def logout():
    """
    Logout endpoint (client-side token removal).
    
    Returns success message. The client should remove the token from storage.
    """
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=User)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user profile.
    
    Requires valid JWT token in Authorization header.
    """
    return current_user


@router.patch("/me", response_model=User)
async def update_user_profile(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update current user profile.
    
    Allows updating: name, email, preferences
    """
    db = get_database()
    
    # Build update document
    update_doc = {"updated_at": datetime.utcnow()}
    
    if updates.name is not None:
        update_doc["name"] = updates.name
    
    if updates.email is not None:
        # Check if email is already taken by another user
        existing_user = await db.users.find_one({
            "email": updates.email,
            "_id": {"$ne": ObjectId(current_user.id)}
        })
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        update_doc["email"] = updates.email
    
    if updates.preferences is not None:
        update_doc["preferences"] = updates.preferences.model_dump()
    
    # Update user in database
    await db.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": update_doc}
    )
    
    # Fetch updated user
    updated_user_doc = await db.users.find_one({"_id": ObjectId(current_user.id)})
    
    # Return updated user
    return User(
        id=str(updated_user_doc["_id"]),
        email=updated_user_doc["email"],
        name=updated_user_doc["name"],
        preferences=UserPreferences(**updated_user_doc.get("preferences", {})),
        created_at=updated_user_doc["created_at"],
        updated_at=updated_user_doc["updated_at"]
    )