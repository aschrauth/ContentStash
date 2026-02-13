from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Dict, Any
from bson import ObjectId
from ..database import get_database
from ..models.user import User
from ..dependencies import get_current_user

router = APIRouter()


@router.get("", response_model=List[Dict[str, Any]])
async def get_tags(
    current_user: User = Depends(get_current_user)
):
    """
    Get all unique tags from the current user's items with usage counts.
    
    Returns tags sorted by frequency (descending).
    Example: [{"name": "design", "count": 5}, {"name": "python", "count": 3}]
    """
    db = get_database()
    
    # Aggregate tags from the current user's items
    pipeline = [
        {
            "$match": {
                "owner_id": ObjectId(current_user.id)
            }
        },
        {
            "$unwind": "$tags"
        },
        {
            "$group": {
                "_id": "$tags",
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {"count": -1}
        },
        {
            "$project": {
                "_id": 0,
                "name": "$_id",
                "count": 1
            }
        }
    ]
    
    cursor = db.saved_items.aggregate(pipeline)
    tags = await cursor.to_list(length=None)
    
    return tags


@router.get("/autocomplete", response_model=List[str])
async def autocomplete_tags(
    q: str = Query(..., min_length=1, description="Query string for tag autocomplete"),
    current_user: User = Depends(get_current_user)
):
    """
    Get tag suggestions based on query string.
    
    Returns max 10 tag suggestions from the user's existing tags
    that match the query (case-insensitive).
    """
    db = get_database()
    
    # Aggregate unique tags from user's items that match the query
    pipeline = [
        {
            "$match": {
                "owner_id": ObjectId(current_user.id)
            }
        },
        {
            "$unwind": "$tags"
        },
        {
            "$match": {
                "tags": {"$regex": f"^{q}", "$options": "i"}
            }
        },
        {
            "$group": {
                "_id": "$tags",
                "count": {"$sum": 1}
            }
        },
        {
            "$sort": {"count": -1}
        },
        {
            "$limit": 10
        },
        {
            "$project": {
                "_id": 0,
                "tag": "$_id"
            }
        }
    ]
    
    cursor = db.saved_items.aggregate(pipeline)
    results = await cursor.to_list(length=None)
    
    # Extract just the tag names
    suggestions = [result["tag"] for result in results]
    
    return suggestions
