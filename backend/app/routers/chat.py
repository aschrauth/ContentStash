from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from datetime import datetime
from bson import ObjectId
from ..database import get_database
from ..models.chat import (
    ChatThread,
    ChatThreadResponse,
    ChatThreadListItem,
    ChatMessage,
    CreateThreadRequest,
    CreateMessageRequest
)
from ..models.user import User
from ..dependencies import get_current_user
from ..services.rag import search_items, generate_answer

router = APIRouter()


@router.post("/threads", response_model=ChatThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_thread(
    request: CreateThreadRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new chat thread with the first user message.
    
    - Creates a new thread
    - Saves the user's message
    - Searches for relevant items using RAG
    - Generates an AI response
    - Saves the assistant's message
    - Returns the complete thread
    """
    db = get_database()
    
    # Search for relevant items
    relevant_items = await search_items(current_user.id, request.message)
    
    # Generate answer using RAG
    rag_result = generate_answer(request.message, relevant_items)
    
    # Create user message
    user_message = ChatMessage(
        role="user",
        content=request.message,
        citations=[],
        created_at=datetime.utcnow()
    )
    
    # Create assistant message
    assistant_message = ChatMessage(
        role="assistant",
        content=rag_result['answer'],
        citations=rag_result['citations'],
        created_at=datetime.utcnow()
    )
    
    # Generate thread title from first message (truncate if needed)
    title = request.message[:100] if len(request.message) <= 100 else request.message[:97] + "..."
    
    # Create thread document
    now = datetime.utcnow()
    thread_doc = {
        "owner_id": ObjectId(current_user.id),
        "title": title,
        "messages": [
            {
                "role": user_message.role,
                "content": user_message.content,
                "citations": [],
                "created_at": user_message.created_at
            },
            {
                "role": assistant_message.role,
                "content": assistant_message.content,
                "citations": [
                    {
                        "id": c.id,
                        "title": c.title,
                        "excerpt": c.excerpt
                    }
                    for c in assistant_message.citations
                ],
                "created_at": assistant_message.created_at
            }
        ],
        "created_at": now,
        "updated_at": now
    }
    
    # Insert into database
    result = await db.chat_threads.insert_one(thread_doc)
    thread_id = str(result.inserted_id)
    
    # Return created thread
    return ChatThreadResponse(
        id=thread_id,
        owner_id=current_user.id,
        title=title,
        messages=[user_message, assistant_message],
        created_at=now,
        updated_at=now
    )


@router.get("/threads", response_model=List[ChatThreadListItem])
async def list_threads(
    current_user: User = Depends(get_current_user)
):
    """
    List all chat threads for the current user.
    
    - Filters by owner_id
    - Sorted by updated_at descending (most recent first)
    - Returns simplified thread info for list view
    """
    db = get_database()
    
    # Fetch threads
    cursor = db.chat_threads.find(
        {"owner_id": ObjectId(current_user.id)}
    ).sort("updated_at", -1)
    
    threads_docs = await cursor.to_list(length=None)
    
    # Convert to ChatThreadListItem models
    threads = []
    for doc in threads_docs:
        # Get preview from first user message
        preview = ""
        message_count = len(doc.get("messages", []))
        
        if doc.get("messages") and len(doc["messages"]) > 0:
            first_message = doc["messages"][0]
            preview = first_message.get("content", "")[:200]
            if len(first_message.get("content", "")) > 200:
                preview += "..."
        
        threads.append(ChatThreadListItem(
            id=str(doc["_id"]),
            title=doc["title"],
            preview=preview,
            message_count=message_count,
            created_at=doc["created_at"],
            updated_at=doc["updated_at"]
        ))
    
    return threads


@router.get("/threads/{thread_id}", response_model=ChatThreadResponse)
async def get_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get a single chat thread by ID.
    
    - Verifies ownership
    - Returns full thread with all messages
    """
    db = get_database()
    
    # Validate ObjectId
    if not ObjectId.is_valid(thread_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid thread ID"
        )
    
    # Fetch thread
    thread_doc = await db.chat_threads.find_one({"_id": ObjectId(thread_id)})
    
    if not thread_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Verify ownership
    if str(thread_doc["owner_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this thread"
        )
    
    # Convert messages
    messages = []
    for msg_doc in thread_doc.get("messages", []):
        citations = []
        for cit_doc in msg_doc.get("citations", []):
            from ..models.chat import Citation
            citations.append(Citation(
                id=cit_doc["id"],
                title=cit_doc["title"],
                excerpt=cit_doc["excerpt"]
            ))
        
        messages.append(ChatMessage(
            role=msg_doc["role"],
            content=msg_doc["content"],
            citations=citations,
            created_at=msg_doc["created_at"]
        ))
    
    # Return thread
    return ChatThreadResponse(
        id=str(thread_doc["_id"]),
        owner_id=str(thread_doc["owner_id"]),
        title=thread_doc["title"],
        messages=messages,
        created_at=thread_doc["created_at"],
        updated_at=thread_doc["updated_at"]
    )


@router.post("/threads/{thread_id}/messages", response_model=ChatThreadResponse)
async def add_message(
    thread_id: str,
    request: CreateMessageRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Add a new message to an existing thread.
    
    - Verifies ownership
    - Saves the user's message
    - Searches for relevant items using RAG
    - Generates an AI response
    - Saves the assistant's message
    - Updates thread's updated_at timestamp
    - Returns the updated thread
    """
    db = get_database()
    
    # Validate ObjectId
    if not ObjectId.is_valid(thread_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid thread ID"
        )
    
    # Fetch thread to verify ownership
    thread_doc = await db.chat_threads.find_one({"_id": ObjectId(thread_id)})
    
    if not thread_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Verify ownership
    if str(thread_doc["owner_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this thread"
        )
    
    # Search for relevant items
    relevant_items = await search_items(current_user.id, request.message)
    
    # Generate answer using RAG
    rag_result = generate_answer(request.message, relevant_items)
    
    # Create user message
    user_message = ChatMessage(
        role="user",
        content=request.message,
        citations=[],
        created_at=datetime.utcnow()
    )
    
    # Create assistant message
    assistant_message = ChatMessage(
        role="assistant",
        content=rag_result['answer'],
        citations=rag_result['citations'],
        created_at=datetime.utcnow()
    )
    
    # Prepare message documents
    user_msg_doc = {
        "role": user_message.role,
        "content": user_message.content,
        "citations": [],
        "created_at": user_message.created_at
    }
    
    assistant_msg_doc = {
        "role": assistant_message.role,
        "content": assistant_message.content,
        "citations": [
            {
                "id": c.id,
                "title": c.title,
                "excerpt": c.excerpt
            }
            for c in assistant_message.citations
        ],
        "created_at": assistant_message.created_at
    }
    
    # Update thread with new messages
    await db.chat_threads.update_one(
        {"_id": ObjectId(thread_id)},
        {
            "$push": {
                "messages": {
                    "$each": [user_msg_doc, assistant_msg_doc]
                }
            },
            "$set": {
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Fetch updated thread
    updated_thread_doc = await db.chat_threads.find_one({"_id": ObjectId(thread_id)})
    
    # Convert messages
    messages = []
    for msg_doc in updated_thread_doc.get("messages", []):
        citations = []
        for cit_doc in msg_doc.get("citations", []):
            from ..models.chat import Citation
            citations.append(Citation(
                id=cit_doc["id"],
                title=cit_doc["title"],
                excerpt=cit_doc["excerpt"]
            ))
        
        messages.append(ChatMessage(
            role=msg_doc["role"],
            content=msg_doc["content"],
            citations=citations,
            created_at=msg_doc["created_at"]
        ))
    
    # Return updated thread
    return ChatThreadResponse(
        id=str(updated_thread_doc["_id"]),
        owner_id=str(updated_thread_doc["owner_id"]),
        title=updated_thread_doc["title"],
        messages=messages,
        created_at=updated_thread_doc["created_at"],
        updated_at=updated_thread_doc["updated_at"]
    )


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a chat thread.
    
    - Verifies ownership
    - Permanently deletes the thread
    - Returns success message
    """
    db = get_database()
    
    # Validate ObjectId
    if not ObjectId.is_valid(thread_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid thread ID"
        )
    
    # Fetch thread to verify ownership
    thread_doc = await db.chat_threads.find_one({"_id": ObjectId(thread_id)})
    
    if not thread_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found"
        )
    
    # Verify ownership
    if str(thread_doc["owner_id"]) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this thread"
        )
    
    # Delete thread
    await db.chat_threads.delete_one({"_id": ObjectId(thread_id)})
    
    return {"message": "Thread deleted"}