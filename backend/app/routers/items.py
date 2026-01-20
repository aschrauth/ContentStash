from fastapi import APIRouter, HTTPException, status, Depends, Query, BackgroundTasks
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel, HttpUrl
from ..database import get_database
from ..models.saved_item import SavedItem, SavedItemCreate, SavedItemUpdate
from ..models.user import User
from ..dependencies import get_current_user
from ..services.background import process_item_background
from ..services.metadata import fetch_metadata
from ..services.ai import generate_metadata_from_content
from ..services.youtube import is_youtube_url, get_youtube_preview_metadata
from ..config import settings

router = APIRouter()


class PreviewRequest(BaseModel):
    """Request model for URL preview."""
    url: HttpUrl


class PreviewResponse(BaseModel):
    """Response model for URL preview."""
    title: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    favicon_url: Optional[str] = None


class GenerateMetadataRequest(BaseModel):
    """Request model for generating metadata from pasted content."""
    content: str


class GenerateMetadataResponse(BaseModel):
    """Response model for generated metadata."""
    title: str
    description: str
    tags: List[str]


@router.post("/preview", response_model=PreviewResponse)
async def preview_url(
    request: PreviewRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Preview metadata for a URL without saving it.
    
    - For YouTube URLs: Uses YouTube service for reliable metadata extraction
    - For other URLs: Fetches title, description, image, and favicon via web scraping
    - Does not save to database
    - Returns metadata for frontend to display
    """
    try:
        # Convert HttpUrl to string for the metadata service
        url_str = str(request.url)
        
        # Check if this is a YouTube URL and handle it specially
        if is_youtube_url(url_str):
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Preview endpoint detected YouTube URL: {url_str}")
            
            # Use YouTube service for preview metadata
            youtube_metadata = get_youtube_preview_metadata(url_str, settings.youtube_api_key)
            
            if youtube_metadata:
                logger.info(f"✓ Successfully fetched YouTube preview metadata")
                return PreviewResponse(
                    title=youtube_metadata.get('title'),
                    description=youtube_metadata.get('description'),
                    image_url=youtube_metadata.get('thumbnail'),
                    favicon_url='https://www.youtube.com/favicon.ico'
                )
            else:
                logger.warning(f"✗ YouTube preview metadata extraction failed, returning minimal data")
                # Return minimal data if YouTube extraction fails
                return PreviewResponse(
                    title="YouTube Video",
                    description="Unable to fetch video details",
                    image_url=None,
                    favicon_url='https://www.youtube.com/favicon.ico'
                )
        
        # For non-YouTube URLs, use generic metadata fetching
        metadata = fetch_metadata(url_str)
        
        return PreviewResponse(
            title=metadata.get('title'),
            description=metadata.get('description'),
            image_url=metadata.get('image_url'),
            favicon_url=metadata.get('favicon_url')
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metadata: {str(e)}"
        )


@router.post("/generate-metadata", response_model=GenerateMetadataResponse)
async def generate_metadata(
    request: GenerateMetadataRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate metadata (title, description, tags) from pasted content.
    
    - Uses AI if OpenAI key is configured
    - Falls back to basic text processing if not
    - Does not save to database
    - Returns generated metadata for frontend to populate form
    """
    try:
        # Validate content
        if not request.content or len(request.content.strip()) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content must be at least 10 characters long"
            )
        
        # Generate metadata using AI service
        metadata = generate_metadata_from_content(request.content)
        
        return GenerateMetadataResponse(
            title=metadata['title'],
            description=metadata['description'],
            tags=metadata['tags']
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate metadata: {str(e)}"
        )


@router.post("", response_model=SavedItem, status_code=status.HTTP_201_CREATED)
async def create_item(
    item_data: SavedItemCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new saved item.
    
    - Validates that either URL or content is provided
    - Sets processing_status to "pending"
    - Sets owner_id from current user
    - Schedules background processing if URL is provided
    - For URLs: archived_text is ignored and will be extracted by background task
    - For pasted content: archived_text is saved directly
    - Returns created item
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Log the incoming request data for debugging
    logger.info(f"=== CREATE ITEM REQUEST ===")
    logger.info(f"URL: {item_data.url}")
    logger.info(f"Title: {item_data.title}")
    logger.info(f"Description: {item_data.description}")
    logger.info(f"Image URL: {item_data.image_url}")
    logger.info(f"Favicon URL: {item_data.favicon_url}")
    logger.info(f"Tags: {item_data.tags}")
    logger.info(f"Extraction Type: {item_data.extraction_type}")
    logger.info(f"Has archived_text: {bool(item_data.archived_text)}")
    logger.info(f"Has notes_markdown: {bool(item_data.notes_markdown)}")
    logger.info(f"=========================")
    
    db = get_database()
    
    # Validate that either URL or content (title) is provided
    if not item_data.url and not item_data.title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either URL or title must be provided"
        )
    
    # Create item document
    now = datetime.utcnow()
    
    # For URLs, ignore any archived_text sent by client - it will be extracted by background task
    # For pasted content (no URL), use the provided archived_text
    archived_text = None if item_data.url else item_data.archived_text
    
    # Set extraction_type, defaulting to "fast" if not provided
    extraction_type = item_data.extraction_type or "fast"
    
    item_doc = {
        "owner_id": ObjectId(current_user.id),
        "url": item_data.url,
        "title": item_data.title,
        "description": item_data.description,
        "image_url": item_data.image_url,
        "favicon_url": item_data.favicon_url,
        "notes_markdown": item_data.notes_markdown,
        "tags": item_data.tags,
        "archived_text": archived_text,
        "extraction_type": extraction_type,
        "suggested_tags": None,
        "suggested_topic": None,
        "processing_status": "pending",
        "processing_error": None,
        "created_at": now,
        "updated_at": now,
        "archived_at": None
    }
    
    # Insert into database
    result = await db.saved_items.insert_one(item_doc)
    item_id = str(result.inserted_id)
    
    # Schedule background processing for all items
    # - For URLs: extracts content and generates metadata
    # - For pasted content: generates metadata and creates embeddings
    background_tasks.add_task(
        process_item_background,
        item_id,
        current_user.id
    )
    
    # Return created item
    return SavedItem(
        id=item_id,
        owner_id=current_user.id,
        url=item_data.url,
        title=item_data.title,
        description=item_data.description,
        image_url=item_data.image_url,
        favicon_url=item_data.favicon_url,
        notes_markdown=item_data.notes_markdown,
        tags=item_data.tags,
        archived_text=archived_text,
        extraction_type=extraction_type,
        suggested_tags=None,
        suggested_topic=None,
        processing_status="pending",
        processing_error=None,
        created_at=now,
        updated_at=now,
        archived_at=None
    )


@router.get("", response_model=List[SavedItem])
async def list_items(
    current_user: User = Depends(get_current_user),
    tags: Optional[str] = Query(None, description="Comma-separated list of tags to filter by"),
    search: Optional[str] = Query(None, description="Search query for full-text search"),
    sort: Optional[str] = Query("newest", description="Sort order: newest, oldest, title")
):
    """
    List user's saved items.
    
    - Filters by owner_id (from JWT)
    - Excludes soft-deleted items
    - Supports full-text search using MongoDB text index
    - Supports tag filtering with AND logic
    """
    db = get_database()
    
    # Build query
    query = {
        "owner_id": ObjectId(current_user.id),
        "archived_at": None  # Exclude soft-deleted items
    }
    
    # Add tag filtering (AND logic)
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
        query["tags"] = {"$all": tag_list}
    
    # Add full-text search using MongoDB text index
    if search:
        query["$text"] = {"$search": search}
    
    # Determine sort order
    sort_criteria = []
    
    if search:
        # When searching, sort by text relevance score first
        sort_criteria.append(("score", {"$meta": "textScore"}))
    
    # Add secondary sort
    if sort == "oldest":
        sort_criteria.append(("created_at", 1))
    elif sort == "title":
        sort_criteria.append(("title", 1))
    else:  # newest (default)
        sort_criteria.append(("created_at", -1))
    
    # Build projection to include text score when searching
    projection = None
    if search:
        projection = {"score": {"$meta": "textScore"}}
    
    # Fetch items
    cursor = db.saved_items.find(query, projection)
    
    # Apply sorting
    for field, direction in sort_criteria:
        cursor = cursor.sort(field, direction)
    
    items_docs = await cursor.to_list(length=None)
    
    # Convert to SavedItem models
    items = []
    for doc in items_docs:
        items.append(SavedItem(
            id=str(doc["_id"]),
            owner_id=str(doc["owner_id"]),
            url=doc.get("url"),
            title=doc["title"],
            description=doc.get("description"),
            image_url=doc.get("image_url"),
            favicon_url=doc.get("favicon_url"),
            notes_markdown=doc.get("notes_markdown"),
            tags=doc.get("tags", []),
            archived_text=doc.get("archived_text"),
            extraction_type=doc.get("extraction_type", "fast"),
            suggested_tags=doc.get("suggested_tags"),
            suggested_topic=doc.get("suggested_topic"),
            processing_status=doc.get("processing_status", "pending"),
            processing_error=doc.get("processing_error"),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
            archived_at=doc.get("archived_at")
        ))
    
    return items


@router.get("/{item_id}", response_model=SavedItem)
async def get_item(
    item_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get a single saved item by ID.
    
    - Verifies ownership
    - Returns full item details
    """
    db = get_database()
    
    # Validate ObjectId
    if not ObjectId.is_valid(item_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID"
        )
    
    # Fetch item
    item_doc = await db.saved_items.find_one({"_id": ObjectId(item_id)})
    
    if not item_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Verify ownership
    if str(item_doc["owner_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this item"
        )
    
    # Return item
    return SavedItem(
        id=str(item_doc["_id"]),
        owner_id=str(item_doc["owner_id"]),
        url=item_doc.get("url"),
        title=item_doc["title"],
        description=item_doc.get("description"),
        image_url=item_doc.get("image_url"),
        favicon_url=item_doc.get("favicon_url"),
        notes_markdown=item_doc.get("notes_markdown"),
        tags=item_doc.get("tags", []),
        archived_text=item_doc.get("archived_text"),
        extraction_type=item_doc.get("extraction_type", "fast"),
        suggested_tags=item_doc.get("suggested_tags"),
        suggested_topic=item_doc.get("suggested_topic"),
        processing_status=item_doc.get("processing_status", "pending"),
        processing_error=item_doc.get("processing_error"),
        created_at=item_doc["created_at"],
        updated_at=item_doc["updated_at"],
        archived_at=item_doc.get("archived_at")
    )


@router.patch("/{item_id}", response_model=SavedItem)
async def update_item(
    item_id: str,
    updates: SavedItemUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Update a saved item.
    
    - Allows updating: title, description, notes_markdown, tags, url, image_url, favicon_url, archived_text, extraction_type
    - If extraction_type is changed, automatically triggers reprocessing
    - Verifies ownership
    - Returns updated item
    """
    db = get_database()
    
    # Validate ObjectId
    if not ObjectId.is_valid(item_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID"
        )
    
    # Fetch item to verify ownership
    item_doc = await db.saved_items.find_one({"_id": ObjectId(item_id)})
    
    if not item_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Verify ownership
    if str(item_doc["owner_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this item"
        )
    
    # Build update document (only include fields that were provided)
    update_doc = {"updated_at": datetime.utcnow()}
    
    # Track if extraction_type is being changed to trigger reprocessing
    extraction_type_changed = False
    
    if updates.title is not None:
        update_doc["title"] = updates.title
    
    if updates.description is not None:
        update_doc["description"] = updates.description
    
    if updates.url is not None:
        update_doc["url"] = updates.url
    
    if updates.image_url is not None:
        update_doc["image_url"] = updates.image_url
    
    if updates.favicon_url is not None:
        update_doc["favicon_url"] = updates.favicon_url
    
    if updates.notes_markdown is not None:
        update_doc["notes_markdown"] = updates.notes_markdown
    
    if updates.tags is not None:
        update_doc["tags"] = updates.tags
    
    if updates.archived_text is not None:
        update_doc["archived_text"] = updates.archived_text
    
    if updates.extraction_type is not None:
        # Check if extraction_type is actually changing
        if item_doc.get("extraction_type", "fast") != updates.extraction_type:
            extraction_type_changed = True
            update_doc["extraction_type"] = updates.extraction_type
            # Reset processing status to trigger reprocessing
            update_doc["processing_status"] = "pending"
            update_doc["processing_error"] = None
    
    # Update item in database
    await db.saved_items.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": update_doc}
    )
    
    # If extraction_type changed and item has a URL, trigger reprocessing
    if extraction_type_changed and item_doc.get("url"):
        background_tasks.add_task(
            process_item_background,
            item_id,
            current_user.id
        )
    
    # Fetch updated item
    updated_item_doc = await db.saved_items.find_one({"_id": ObjectId(item_id)})
    
    # Return updated item
    return SavedItem(
        id=str(updated_item_doc["_id"]),
        owner_id=str(updated_item_doc["owner_id"]),
        url=updated_item_doc.get("url"),
        title=updated_item_doc["title"],
        description=updated_item_doc.get("description"),
        image_url=updated_item_doc.get("image_url"),
        favicon_url=updated_item_doc.get("favicon_url"),
        notes_markdown=updated_item_doc.get("notes_markdown"),
        tags=updated_item_doc.get("tags", []),
        archived_text=updated_item_doc.get("archived_text"),
        extraction_type=updated_item_doc.get("extraction_type", "fast"),
        suggested_tags=updated_item_doc.get("suggested_tags"),
        suggested_topic=updated_item_doc.get("suggested_topic"),
        processing_status=updated_item_doc.get("processing_status", "pending"),
        processing_error=updated_item_doc.get("processing_error"),
        created_at=updated_item_doc["created_at"],
        updated_at=updated_item_doc["updated_at"],
        archived_at=updated_item_doc.get("archived_at")
    )


@router.delete("/{item_id}")
async def delete_item(
    item_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Soft delete a saved item and remove its chunks from vector search.
    
    - Sets archived_at to current timestamp
    - Deletes all associated chunks from item_chunks collection
    - Verifies ownership
    - Returns success message
    """
    db = get_database()
    
    # Validate ObjectId
    if not ObjectId.is_valid(item_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID"
        )
    
    # Fetch item to verify ownership
    item_doc = await db.saved_items.find_one({"_id": ObjectId(item_id)})
    
    if not item_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Verify ownership
    if str(item_doc["owner_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this item"
        )
    
    # Soft delete: set archived_at to current time
    await db.saved_items.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": {"archived_at": datetime.utcnow()}}
    )
    
    # Delete all associated chunks from vector search index
    # This ensures deleted items don't appear in AI search results
    chunks_deleted = await db.item_chunks.delete_many({"item_id": item_id})
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        f"Deleted item {item_id} and removed {chunks_deleted.deleted_count} "
        f"associated chunks from vector search index"
    )
    
    return {"message": "Item archived"}


@router.post("/{item_id}/reprocess", response_model=SavedItem)
async def reprocess_item(
    item_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Reprocess a saved item.
    
    - Verifies ownership
    - Resets processing status to 'pending'
    - Triggers background processing again
    - Returns updated item
    """
    db = get_database()
    
    # Validate ObjectId
    if not ObjectId.is_valid(item_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid item ID"
        )
    
    # Fetch item to verify ownership
    item_doc = await db.saved_items.find_one({"_id": ObjectId(item_id)})
    
    if not item_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    # Verify ownership
    if str(item_doc["owner_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to reprocess this item"
        )
    
    # Check if item has a URL
    if not item_doc.get("url"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reprocess item without URL"
        )
    
    # Reset processing status to pending
    await db.saved_items.update_one(
        {"_id": ObjectId(item_id)},
        {
            "$set": {
                "processing_status": "pending",
                "processing_error": None,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Schedule background processing
    background_tasks.add_task(
        process_item_background,
        item_id,
        current_user.id
    )
    
    # Fetch and return updated item
    updated_item_doc = await db.saved_items.find_one({"_id": ObjectId(item_id)})
    
    return SavedItem(
        id=str(updated_item_doc["_id"]),
        owner_id=str(updated_item_doc["owner_id"]),
        url=updated_item_doc.get("url"),
        title=updated_item_doc["title"],
        description=updated_item_doc.get("description"),
        image_url=updated_item_doc.get("image_url"),
        favicon_url=updated_item_doc.get("favicon_url"),
        notes_markdown=updated_item_doc.get("notes_markdown"),
        tags=updated_item_doc.get("tags", []),
        archived_text=updated_item_doc.get("archived_text"),
        extraction_type=updated_item_doc.get("extraction_type", "fast"),
        suggested_tags=updated_item_doc.get("suggested_tags"),
        suggested_topic=updated_item_doc.get("suggested_topic"),
        processing_status=updated_item_doc.get("processing_status", "pending"),
        processing_error=updated_item_doc.get("processing_error"),
        created_at=updated_item_doc["created_at"],
        updated_at=updated_item_doc["updated_at"],
        archived_at=updated_item_doc.get("archived_at")
    )