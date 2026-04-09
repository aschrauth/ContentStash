from fastapi import APIRouter, HTTPException, status, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional, AsyncGenerator
from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel, HttpUrl, Field
import asyncio
import json
from ..database import get_database
from ..models.saved_item import SavedItem, SavedItemCreate, SavedItemUpdate
from ..models.user import User
from ..dependencies import get_current_user
from ..services.background import process_item_background
from ..services.metadata import fetch_metadata
from ..services.ai import generate_metadata_from_content
from ..services.youtube import is_youtube_url, get_youtube_preview_metadata
from ..services.extraction import extract_source_from_url
from ..config import settings
from ..utils.auth import verify_token

router = APIRouter()


async def get_current_user_from_query(
    token: str = Query(...),
) -> User:
    """
    Get current user from query parameter token (for SSE).
    EventSource doesn't support custom headers, so we pass token as query param.
    """
    # Verify token and extract user ID
    user_id = verify_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    
    # Get user from database
    db = get_database()
    user_doc = await db.users.find_one({"_id": ObjectId(user_id)})
    
    if user_doc is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Convert MongoDB document to User model
    from ..models.user import UserPreferences
    user = User(
        id=str(user_doc["_id"]),
        email=user_doc["email"],
        name=user_doc["name"],
        preferences=UserPreferences(**user_doc.get("preferences", {})),
        created_at=user_doc["created_at"],
        updated_at=user_doc["updated_at"]
    )
    
    return user


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


class PendingLocalHintResponse(BaseModel):
    """Lightweight response for local extraction queue polling hints."""
    pending_count: int
    queue_version: str
    recommended_poll_seconds: int


@router.get("/status-stream")
async def stream_item_status(
    current_user: User = Depends(get_current_user_from_query),
    db = Depends(get_database)
):
    """
    Server-Sent Events endpoint for real-time item status updates.
    Streams updates when items change from pending to completed/failed.
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                # Check for pending items
                pending_count = await db.saved_items.count_documents({
                    "owner_id": ObjectId(current_user.id),
                    "processing_status": {"$in": ["pending", "processing"]}
                })
                
                # Send update
                data = json.dumps({"pending_count": pending_count})
                yield f"data: {data}\n\n"
                
                # Wait before next check (every 5 seconds)
                await asyncio.sleep(5)
                
        except asyncio.CancelledError:
            # Client disconnected
            pass
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


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
    
    - Uses Gemini when configured
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
    - If URL is provided without title, automatically fetches metadata (title, description, image)
    - Sets processing_status to "pending"
    - Sets owner_id from current user
    - Schedules background processing if URL is provided
    - For URLs: archived_text is ignored and will be extracted by background task
    - For pasted content: archived_text is saved directly
    - Returns created item
    """
    db = get_database()
    
    # Validate that either URL or content (title) is provided
    if not item_data.url and not item_data.title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either URL or title must be provided"
        )
    
    # If URL is provided but title is missing, fetch metadata
    if item_data.url and not item_data.title:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Title not provided for URL {item_data.url}, fetching metadata...")
        
        try:
            # Check if this is a YouTube URL and handle it specially
            if is_youtube_url(item_data.url):
                logger.info(f"Fetching YouTube metadata for: {item_data.url}")
                youtube_metadata = get_youtube_preview_metadata(item_data.url, settings.youtube_api_key)
                
                if youtube_metadata:
                    item_data.title = youtube_metadata.get('title') or item_data.url
                    if not item_data.description:
                        item_data.description = youtube_metadata.get('description')
                    if not item_data.image_url:
                        item_data.image_url = youtube_metadata.get('thumbnail')
                    if not item_data.favicon_url:
                        item_data.favicon_url = 'https://www.youtube.com/favicon.ico'
                    logger.info(f"✓ Successfully fetched YouTube metadata: {item_data.title}")
                else:
                    logger.warning(f"✗ YouTube metadata extraction failed, using URL as title")
                    item_data.title = item_data.url
            else:
                # For non-YouTube URLs, use generic metadata fetching
                logger.info(f"Fetching generic metadata for: {item_data.url}")
                metadata = fetch_metadata(item_data.url)
                
                item_data.title = metadata.get('title') or item_data.url
                if not item_data.description:
                    item_data.description = metadata.get('description')
                if not item_data.image_url:
                    item_data.image_url = metadata.get('image_url')
                if not item_data.favicon_url:
                    item_data.favicon_url = metadata.get('favicon_url')
                logger.info(f"✓ Successfully fetched metadata: {item_data.title}")
        except Exception as e:
            logger.error(f"Error fetching metadata for {item_data.url}: {str(e)}")
            # Fallback to using URL as title if metadata fetch fails
            item_data.title = item_data.url
    
    # Create item document
    now = datetime.utcnow()
    
    # For URLs, ignore any archived_text sent by client - it will be extracted by background task
    # For pasted content (no URL), use the provided archived_text
    archived_text = None if item_data.url else item_data.archived_text
    
    # Set extraction_type, defaulting to "fast" if not provided
    extraction_type = item_data.extraction_type or "fast"
    
    # Handle source field
    source = None
    if item_data.url:
        # For YouTube URLs, don't set source here - let background processing set it with channel name
        # For other URLs, extract source from URL immediately for API response
        if not is_youtube_url(item_data.url):
            source = extract_source_from_url(item_data.url)
        # For YouTube, source will be set by background processing as "YouTube | [Channel Name]"
    elif item_data.source:
        # For pasted content, use provided source if available
        source = item_data.source
    elif not item_data.url:
        # For pasted content without source, default to "Pasted Content"
        source = "Pasted Content"
    
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
        "source": source,
        "suggested_tags": None,
        "suggested_topic": None,
        "processing_status": "pending",
        "processing_error": None,
        "is_read": False,
        "created_at": now,
        "updated_at": now
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
        source=source,
        suggested_tags=None,
        suggested_topic=None,
        ai_summary=None,
        word_count=len(archived_text.split()) if archived_text else 0,
        processing_status="pending",
        processing_error=None,
        is_read=False,
        created_at=now,
        updated_at=now
    )


@router.get("", response_model=dict)
async def list_items(
    current_user: User = Depends(get_current_user),
    tags: Optional[str] = Query(None, description="Comma-separated list of tags to filter by"),
    search: Optional[str] = Query(None, description="Search query for full-text search"),
    sort: Optional[str] = Query("newest", description="Sort order: newest, oldest, title"),
    limit: int = Query(default=50, ge=1, le=100, description="Number of items to return"),
    cursor: Optional[str] = Query(None, description="Cursor for pagination (item _id)")
):
    """
    List user's saved items with cursor-based pagination.
    
    - Filters by owner_id (from JWT)
    - Supports full-text search using MongoDB text index
    - Supports tag filtering with AND logic
    - Returns paginated results with next_cursor, has_more, and total count
    """
    db = get_database()
    
    # Build query
    query = {
        "owner_id": ObjectId(current_user.id)
    }
    
    # Add tag filtering (AND logic)
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
        query["tags"] = {"$all": tag_list}
    
    # Add full-text search using MongoDB text index
    if search:
        query["$text"] = {"$search": search}
    
    # Add cursor-based pagination
    pagination_query = query.copy()
    if cursor:
        try:
            pagination_query["_id"] = {"$lt": ObjectId(cursor)}
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cursor"
            )
    
    # Determine sort order
    sort_criteria = []
    
    if search:
        # When searching, sort by text relevance score first
        sort_criteria.append(("score", {"$meta": "textScore"}))
    
    # Add secondary sort - always include _id for consistent pagination
    if sort == "oldest":
        sort_criteria.append(("created_at", 1))
        sort_criteria.append(("_id", 1))
    elif sort == "title":
        sort_criteria.append(("title", 1))
        sort_criteria.append(("_id", -1))
    else:  # newest (default)
        sort_criteria.append(("created_at", -1))
        sort_criteria.append(("_id", -1))
    
    # Build projection - only exclude archived_text to reduce payload size
    # MongoDB doesn't allow mixing inclusion and exclusion, so we only exclude
    projection = {"archived_text": 0}
    
    if search:
        projection["score"] = {"$meta": "textScore"}
    
    # Fetch limit + 1 items to determine if there are more
    find_cursor = db.saved_items.find(pagination_query, projection)
    
    # Apply sorting
    for field, direction in sort_criteria:
        find_cursor = find_cursor.sort(field, direction)
    
    # Limit to one more than requested to check for more items
    items_docs = await find_cursor.limit(limit + 1).to_list(length=limit + 1)
    
    # Check if there are more items
    has_more = len(items_docs) > limit
    if has_more:
        items_docs = items_docs[:limit]  # Remove the extra item
    
    # Get next cursor from last item
    next_cursor = None
    if has_more and items_docs:
        next_cursor = str(items_docs[-1]["_id"])
    
    # Convert to SavedItem models (without archived_text)
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
            archived_text=None,  # Excluded from list endpoint
            extraction_type=doc.get("extraction_type", "fast"),
            source=doc.get("source"),
            suggested_tags=doc.get("suggested_tags"),
            suggested_topic=doc.get("suggested_topic"),
            ai_summary=doc.get("ai_summary"),
            word_count=doc.get("word_count"),
            processing_status=doc.get("processing_status", "pending"),
            processing_error=doc.get("processing_error"),
            is_read=doc.get("is_read", False),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        ))
    
    # Get total count for the query (without cursor pagination)
    total_count = await db.saved_items.count_documents(query)
    unread_count = await db.saved_items.count_documents({
        "owner_id": ObjectId(current_user.id),
        "is_read": {"$ne": True}
    })
    
    # Return paginated response with total count
    return {
        "items": items,
        "pagination": {
            "next_cursor": next_cursor,
            "has_more": has_more,
            "limit": limit,
            "total": total_count,
            "unread": unread_count
        }
    }


@router.get("/pending-local", response_model=List[SavedItem])
async def get_pending_local_extraction(
    current_user: User = Depends(get_current_user)
):
    """
    Get items that are pending local extraction.
    
    - Returns items with extraction_type='local' and status='pending' or 'pending_local_extraction'
    - Allows re-extraction even if archived_text already exists (user can manually change extraction_type)
    - Used by Chrome Extension to poll for items needing local processing
    - Filters by owner_id (from JWT)
    - Returns empty list if no pending items (not an error)
    """
    db = get_database()
    
    # Build query for pending local extraction items
    # Items appear in queue when:
    # 1. extraction_type="local" (explicitly marked for local extraction)
    # 2. processing_status in ["pending", "pending_local_extraction"]
    # 3. Item belongs to current user
    # Note: archived_text filter removed to allow re-extraction when user changes extraction_type
    query = {
        "owner_id": ObjectId(current_user.id),
        "extraction_type": "local",
        "processing_status": {"$in": ["pending", "pending_local_extraction"]}
    }
    
    # Fetch items
    cursor = db.saved_items.find(query).sort("created_at", -1)
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
            source=doc.get("source"),
            suggested_tags=doc.get("suggested_tags"),
            suggested_topic=doc.get("suggested_topic"),
            ai_summary=doc.get("ai_summary"),
            word_count=doc.get("word_count"),
            processing_status=doc.get("processing_status", "pending"),
            processing_error=doc.get("processing_error"),
            is_read=doc.get("is_read", False),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        ))
    
    return items


@router.get("/pending-local/hint", response_model=PendingLocalHintResponse)
async def get_pending_local_extraction_hint(
    current_user: User = Depends(get_current_user)
):
    """
    Get a lightweight hint for local extraction queue state.

    Returns only count + queue version metadata so extensions can poll cheaply,
    then fetch full queue payload only when needed.
    """
    db = get_database()

    query = {
        "owner_id": ObjectId(current_user.id),
        "extraction_type": "local",
        "processing_status": {"$in": ["pending", "pending_local_extraction"]}
    }

    pending_count = await db.saved_items.count_documents(query)

    latest_item = await db.saved_items.find_one(
        query,
        sort=[("updated_at", -1)],
        projection={"updated_at": 1}
    )

    latest_updated_at = latest_item.get("updated_at") if latest_item else None
    timestamp_part = latest_updated_at.isoformat() if latest_updated_at else "none"
    queue_version = f"{pending_count}:{timestamp_part}"

    # Server guidance for extension polling cadence.
    # Keep this conservative: fast checks only while queue has work.
    recommended_poll_seconds = 10 if pending_count > 0 else 900

    return PendingLocalHintResponse(
        pending_count=pending_count,
        queue_version=queue_version,
        recommended_poll_seconds=recommended_poll_seconds
    )


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
    import logging
    logger = logging.getLogger(__name__)
    
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
    saved_item = SavedItem(
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
        source=item_doc.get("source"),
        suggested_tags=item_doc.get("suggested_tags"),
        suggested_topic=item_doc.get("suggested_topic"),
        ai_summary=item_doc.get("ai_summary"),
        word_count=item_doc.get("word_count"),
        processing_status=item_doc.get("processing_status", "pending"),
        processing_error=item_doc.get("processing_error"),
        is_read=item_doc.get("is_read", False),
        created_at=item_doc["created_at"],
        updated_at=item_doc["updated_at"]
    )
    
    return saved_item


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
    
    if updates.source is not None:
        update_doc["source"] = updates.source

    if updates.is_read is not None:
        update_doc["is_read"] = updates.is_read
    
    if updates.extraction_type is not None:
        # Check if extraction_type is actually changing
        if item_doc.get("extraction_type", "fast") != updates.extraction_type:
            extraction_type_changed = True
            update_doc["extraction_type"] = updates.extraction_type
            
            # If changing to "local", clear existing content and mark for local extraction
            # BUT only if we're not simultaneously uploading new content (archived_text update)
            if updates.extraction_type == "local":
                # Only clear archived_text if we're not uploading new content in this same request
                if updates.archived_text is None:
                    # User is changing to local without providing content - clear and wait for extension
                    update_doc["archived_text"] = None
                    update_doc["processing_status"] = "pending"
                    update_doc["processing_error"] = "Waiting for local extraction by browser extension"
                else:
                    # User is uploading content with local extraction type - keep the content
                    update_doc["processing_status"] = "processing"
                    update_doc["processing_error"] = None
            else:
                # For other extraction types, reset to pending for backend reprocessing
                update_doc["processing_status"] = "pending"
                update_doc["processing_error"] = None
    
    # Update item in database
    await db.saved_items.update_one(
        {"_id": ObjectId(item_id)},
        {"$set": update_doc}
    )
    
    # If extraction_type changed to something other than "local" and item has a URL, trigger reprocessing
    # For "local" extraction type, don't trigger backend processing - let Chrome extension handle it
    if extraction_type_changed and item_doc.get("url") and updates.extraction_type != "local":
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
        source=updated_item_doc.get("source"),
        suggested_tags=updated_item_doc.get("suggested_tags"),
        suggested_topic=updated_item_doc.get("suggested_topic"),
        ai_summary=updated_item_doc.get("ai_summary"),
        word_count=updated_item_doc.get("word_count"),
        processing_status=updated_item_doc.get("processing_status", "pending"),
        processing_error=updated_item_doc.get("processing_error"),
        is_read=updated_item_doc.get("is_read", False),
        created_at=updated_item_doc["created_at"],
        updated_at=updated_item_doc["updated_at"]
    )


@router.delete("/{item_id}")
async def delete_item(
    item_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Permanently delete a saved item and remove its chunks from vector search.

    - Deletes item from saved_items collection
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
    
    # Delete all associated chunks from vector search index
    # This ensures deleted items don't appear in AI search results.
    chunks_deleted = await db.item_chunks.delete_many({"item_id": item_id})

    # Hard delete: permanently remove item from database
    delete_result = await db.saved_items.delete_one({"_id": ObjectId(item_id)})
    if delete_result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete item"
        )
    
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        f"Deleted item {item_id} and removed {chunks_deleted.deleted_count} "
        f"associated chunks from vector search index"
    )

    return {"message": "Item deleted"}


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
        source=updated_item_doc.get("source"),
        suggested_tags=updated_item_doc.get("suggested_tags"),
        suggested_topic=updated_item_doc.get("suggested_topic"),
        ai_summary=updated_item_doc.get("ai_summary"),
        word_count=updated_item_doc.get("word_count"),
        processing_status=updated_item_doc.get("processing_status", "pending"),
        processing_error=updated_item_doc.get("processing_error"),
        is_read=updated_item_doc.get("is_read", False),
        created_at=updated_item_doc["created_at"],
        updated_at=updated_item_doc["updated_at"]
    )


class UploadContentRequest(BaseModel):
    """Request model for uploading extracted content from local agent."""
    content: str = Field(..., min_length=1, max_length=10000000)
    extraction_source: str = Field(default="local_extension", max_length=50)
    source: Optional[str] = Field(default=None, max_length=200)


@router.patch("/{item_id}/content", response_model=SavedItem)
async def upload_extracted_content(
    item_id: str,
    request: UploadContentRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Upload extracted content from a local agent (Chrome Extension).
    
    - Accepts extracted content from browser extension
    - Updates archived_text
    - Triggers post-processing (embeddings, AI tags)
    - Verifies ownership
    - Returns updated item
    """
    import logging
    logger = logging.getLogger(__name__)
    
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
    
    logger.info(
        f"Received local extraction content for item {item_id} "
        f"from {request.extraction_source} ({len(request.content)} chars)"
    )
    
    # Check if this is an error report from the extension
    is_error_report = request.extraction_source in ['chrome_extension_failed', 'chrome_extension_error']
    is_extraction_failure = request.content.startswith('[Extraction Failed]') or request.content.startswith('[Extraction Error]')
    
    if is_error_report or is_extraction_failure:
        logger.warning(
            f"Local extraction failed for item {item_id}: {request.content[:200]}"
        )
        
        # Try to fall back to server-side extraction
        current_extraction_type = item_doc.get("extraction_type", "local")
        
        if current_extraction_type == "local":
            logger.info(f"Falling back to server 'complete' extraction for item {item_id}")
            await db.saved_items.update_one(
                {"_id": ObjectId(item_id)},
                {
                    "$set": {
                        "extraction_type": "complete",
                        "processing_status": "pending",
                        "processing_error": f"Local extraction failed, retrying with server: {request.content[:200]}",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Trigger background processing with server extraction
            background_tasks.add_task(
                process_item_background,
                item_id,
                current_user.id
            )
        else:
            # Already tried server extraction, mark as failed
            logger.error(f"All extraction methods failed for item {item_id}")
            await db.saved_items.update_one(
                {"_id": ObjectId(item_id)},
                {
                    "$set": {
                        "processing_status": "failed",
                        "processing_error": f"All extraction methods failed: {request.content[:500]}",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
    else:
        # Normal successful extraction
        # Check if content is actually different from what we already have
        existing_content = item_doc.get("archived_text", "")
        content_changed = existing_content != request.content
        
        if not content_changed and existing_content:
            logger.info(
                f"Content for item {item_id} unchanged, skipping reprocessing"
            )
            # Just update the timestamp and clear any error
            await db.saved_items.update_one(
                {"_id": ObjectId(item_id)},
                {
                    "$set": {
                        "processing_error": None,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        else:
            # Clean the content before storing it
            from ..services.extraction import _clean_extracted_content
            cleaned_content = _clean_extracted_content(request.content)
            
            # Update item with extracted content and mark as processing
            # Use "processing" instead of "pending" to avoid infinite loop in local extraction queue
            word_count = len(cleaned_content.split()) if cleaned_content else 0
            
            update_fields = {
                "archived_text": cleaned_content,
                "word_count": word_count,
                "processing_status": "processing",
                "processing_error": None,
                "updated_at": datetime.utcnow()
            }
            
            # If source is provided (e.g., "YouTube | Channel Name" from extension), update it
            if request.source:
                logger.info(f"Updating source from extension for item {item_id}: {request.source}")
                update_fields["source"] = request.source
            
            await db.saved_items.update_one(
                {"_id": ObjectId(item_id)},
                {"$set": update_fields}
            )
            
            # Trigger background processing for embeddings and AI categorization
            # Pass skip_extraction=True since content was already provided by local extraction
            background_tasks.add_task(
                process_item_background,
                item_id,
                current_user.id,
                skip_extraction=True
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
        source=updated_item_doc.get("source"),
        suggested_tags=updated_item_doc.get("suggested_tags"),
        suggested_topic=updated_item_doc.get("suggested_topic"),
        ai_summary=updated_item_doc.get("ai_summary"),
        word_count=updated_item_doc.get("word_count"),
        processing_status=updated_item_doc.get("processing_status", "pending"),
        processing_error=updated_item_doc.get("processing_error"),
        is_read=updated_item_doc.get("is_read", False),
        created_at=updated_item_doc["created_at"],
        updated_at=updated_item_doc["updated_at"]
    )
