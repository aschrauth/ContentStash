"""
Background processing service for saved items.
"""
import logging
import json
from datetime import datetime
from bson import ObjectId
from typing import Optional, Dict, Any

from app.database import get_database, get_item_chunks_collection
from app.services.metadata import fetch_metadata
from app.services.extraction import extract_content
from app.services.ai import generate_tags_and_topic
from app.services.chunking import chunk_text
from app.services.gemini import gemini_service, GeminiServiceError

logger = logging.getLogger(__name__)


def generate_auto_categorization(archived_text: str) -> Optional[Dict[str, Any]]:
    """
    Generate auto-categorization using Gemini 2.0 Flash-Lite.
    
    Uses a concise prompt to generate:
    - suggested_tags: List of 3-5 relevant tags
    - topic: Main topic/category
    - summary: 2-3 sentence summary
    
    Args:
        archived_text: The extracted text content to categorize
    
    Returns:
        Dictionary with suggested_tags, topic, and summary, or None if categorization fails
    """
    if not archived_text or len(archived_text.strip()) < 50:
        logger.info("Text too short for auto-categorization, skipping")
        return None
    
    if not gemini_service.is_available():
        logger.info("Gemini service not available, skipping auto-categorization")
        return None
    
    try:
        # Use first 1500 chars for cost optimization
        content_sample = archived_text[:1500].strip()
        
        # Construct concise prompt for structured JSON output
        prompt = f"""Analyze this content and provide categorization in JSON format.

Content: {content_sample}

Respond with JSON only:
{{
  "suggested_tags": ["tag1", "tag2", "tag3"],
  "topic": "main topic",
  "summary": "2-3 sentence summary"
}}"""
        
        logger.info("Generating auto-categorization with Gemini")
        
        # Call Gemini with Flash-Lite model
        response = gemini_service.generate_content(
            prompt=prompt,
            model="gemini-2.0-flash-lite-preview-02-05"
        )
        
        if not response:
            logger.warning("Empty response from Gemini for auto-categorization")
            return None
        
        # Parse JSON response
        # Remove markdown code blocks if present
        response_text = response.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        try:
            categorization = json.loads(response_text)
            
            # Validate structure
            if not isinstance(categorization, dict):
                logger.error("Categorization response is not a dictionary")
                return None
            
            # Extract and validate fields
            suggested_tags = categorization.get("suggested_tags", [])
            topic = categorization.get("topic", "")
            summary = categorization.get("summary", "")
            
            # Ensure suggested_tags is a list and limit to 5 tags
            if not isinstance(suggested_tags, list):
                suggested_tags = []
            suggested_tags = suggested_tags[:5]
            
            # Ensure topic and summary are strings
            if not isinstance(topic, str):
                topic = ""
            if not isinstance(summary, str):
                summary = ""
            
            result = {
                "suggested_tags": suggested_tags,
                "topic": topic,
                "summary": summary
            }
            
            logger.info(
                f"Successfully generated auto-categorization: "
                f"{len(suggested_tags)} tags, topic='{topic[:50]}...', "
                f"summary length={len(summary)}"
            )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Gemini: {str(e)}")
            logger.debug(f"Response text: {response_text[:500]}")
            return None
            
    except GeminiServiceError as e:
        logger.error(f"Gemini service error during auto-categorization: {str(e)}")
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error during auto-categorization: {str(e)}",
            exc_info=True
        )
        return None


async def process_item_background(item_id: str, user_id: str):
    """
    Background task to process a saved item:
    1. Update status to 'pending'
    2. Fetch metadata (if missing)
    3. Extract content -> save to archivedText
    4. Generate AI suggestions -> save to suggestedTags, suggestedTopic
    5. Update item with results and set status to 'processed'
    6. Handle errors by setting status to 'failed' and saving processingError
    
    Args:
        item_id: The ID of the item to process
        user_id: The ID of the user who owns the item (for verification)
    """
    db = get_database()
    
    try:
        logger.info(f"Starting background processing for item {item_id}")
        
        # Validate ObjectId
        if not ObjectId.is_valid(item_id):
            logger.error(f"Invalid item ID: {item_id}")
            return
        
        # Fetch the item
        item_doc = await db.saved_items.find_one({"_id": ObjectId(item_id)})
        
        if not item_doc:
            logger.error(f"Item not found: {item_id}")
            return
        
        # Verify ownership
        if str(item_doc["owner_id"]) != user_id:
            logger.error(f"Ownership verification failed for item {item_id}")
            return
        
        # Get the URL
        url = item_doc.get("url")
        
        if not url:
            logger.warning(f"No URL provided for item {item_id}, skipping processing")
            await db.saved_items.update_one(
                {"_id": ObjectId(item_id)},
                {
                    "$set": {
                        "processing_status": "processed",
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            return
        
        # Update status to pending
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
        
        # Step 1: Fetch metadata (if missing)
        metadata = {}
        if not item_doc.get("title") or not item_doc.get("description"):
            logger.info(f"Fetching metadata for {url}")
            metadata = fetch_metadata(url)
        
        # Step 2: Extract content
        logger.info(f"Extracting content from {url}")
        archived_text = extract_content(url)
        
        # Step 3: Generate AI suggestions (legacy)
        ai_suggestions = {"tags": [], "topic": None}
        
        if archived_text:
            logger.info(f"Generating AI suggestions for item {item_id}")
            # Get existing user tags to help with suggestions
            existing_tags = item_doc.get("tags", [])
            ai_suggestions = generate_tags_and_topic(
                archived_text,
                existing_tags=existing_tags if existing_tags else None
            )
        else:
            logger.warning(f"No content extracted for item {item_id}, skipping AI suggestions")
        
        # Step 3.5: Generate auto-categorization with Gemini
        auto_categorization = None
        if archived_text:
            logger.info(f"Generating auto-categorization for item {item_id}")
            auto_categorization = generate_auto_categorization(archived_text)
            
            if auto_categorization:
                logger.info(
                    f"Auto-categorization successful for item {item_id}: "
                    f"{len(auto_categorization.get('suggested_tags', []))} tags, "
                    f"topic='{auto_categorization.get('topic', '')[:30]}...'"
                )
            else:
                logger.info(f"Auto-categorization skipped or failed for item {item_id}")
        
        # Step 4: Chunk and embed archived_text (if available and Gemini is configured)
        if archived_text and gemini_service.is_available():
            try:
                logger.info(f"Starting chunking and embedding for item {item_id}")
                
                # Chunk the archived text
                chunks = chunk_text(archived_text, chunk_size=500, overlap=75)
                logger.info(f"Created {len(chunks)} chunks for item {item_id}")
                
                if chunks:
                    # Embed all chunks in batch for efficiency
                    logger.info(f"Generating embeddings for {len(chunks)} chunks")
                    try:
                        embeddings = gemini_service.embed_batch(chunks)
                        
                        if len(embeddings) != len(chunks):
                            logger.error(
                                f"Embedding count mismatch: {len(embeddings)} embeddings "
                                f"for {len(chunks)} chunks. Skipping chunk storage."
                            )
                        else:
                            # Store chunks with embeddings in item_chunks collection
                            chunks_collection = get_item_chunks_collection()
                            
                            # Prepare chunk documents
                            chunk_docs = []
                            for idx, (chunk_content, embedding) in enumerate(zip(chunks, embeddings)):
                                chunk_doc = {
                                    "item_id": item_id,
                                    "owner_id": user_id,
                                    "chunk_index": idx,
                                    "text": chunk_content,
                                    "embedding": embedding,
                                    "created_at": datetime.utcnow()
                                }
                                chunk_docs.append(chunk_doc)
                            
                            # Delete any existing chunks for this item (in case of reprocessing)
                            await chunks_collection.delete_many({"item_id": item_id})
                            
                            # Insert new chunks
                            if chunk_docs:
                                result = await chunks_collection.insert_many(chunk_docs)
                                logger.info(
                                    f"Successfully stored {len(result.inserted_ids)} chunks "
                                    f"with embeddings for item {item_id}"
                                )
                    except GeminiServiceError as e:
                        # Handle rate limits and other Gemini errors gracefully
                        error_msg = str(e).lower()
                        if "quota" in error_msg or "rate limit" in error_msg or "429" in error_msg:
                            logger.warning(
                                f"Gemini API rate limit/quota exceeded for item {item_id}. "
                                f"Chunks created but not embedded. Item will be processed without vector search capability. "
                                f"Error: {str(e)}"
                            )
                        else:
                            logger.error(
                                f"Gemini service error during embedding for item {item_id}: {str(e)}. "
                                f"Chunks created but not embedded."
                            )
                        # Continue processing - the item will still be saved with metadata and categorization
                        
            except GeminiServiceError as e:
                logger.error(
                    f"Gemini service error during chunking for item {item_id}: {str(e)}. "
                    f"Skipping chunking/embedding."
                )
                # Don't fail the entire processing - just log the error
            except Exception as e:
                logger.error(
                    f"Unexpected error during chunking/embedding for item {item_id}: {str(e)}",
                    exc_info=True
                )
                # Don't fail the entire processing - just log the error
        elif archived_text and not gemini_service.is_available():
            logger.info(
                f"Gemini service not available, skipping chunking/embedding for item {item_id}. "
                f"Item will be processed without vector search capability."
            )
        
        # Step 5: Update item with results
        update_doc = {
            "processing_status": "processed",
            "updated_at": datetime.utcnow(),
            "archived_text": archived_text,
            "suggested_tags": ai_suggestions.get("tags"),
            "suggested_topic": ai_suggestions.get("topic")
        }
        
        # Add auto-categorization results if available
        if auto_categorization:
            # Override suggested_tags and topic with Gemini results if available
            if auto_categorization.get("suggested_tags"):
                update_doc["suggested_tags"] = auto_categorization["suggested_tags"]
            if auto_categorization.get("topic"):
                update_doc["suggested_topic"] = auto_categorization["topic"]
            if auto_categorization.get("summary"):
                update_doc["ai_summary"] = auto_categorization["summary"]
        
        # Add metadata fields if they were fetched and are missing
        if metadata:
            if not item_doc.get("title") and metadata.get("title"):
                update_doc["title"] = metadata["title"]
            
            if not item_doc.get("description") and metadata.get("description"):
                update_doc["description"] = metadata["description"]
            
            if not item_doc.get("image_url") and metadata.get("image_url"):
                update_doc["image_url"] = metadata["image_url"]
            
            if not item_doc.get("favicon_url") and metadata.get("favicon_url"):
                update_doc["favicon_url"] = metadata["favicon_url"]
        
        await db.saved_items.update_one(
            {"_id": ObjectId(item_id)},
            {"$set": update_doc}
        )
        
        logger.info(f"Successfully processed item {item_id}")
        
    except Exception as e:
        logger.error(f"Error processing item {item_id}: {str(e)}", exc_info=True)
        
        # Update status to failed with error message
        try:
            await db.saved_items.update_one(
                {"_id": ObjectId(item_id)},
                {
                    "$set": {
                        "processing_status": "failed",
                        "processing_error": str(e),
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        except Exception as update_error:
            logger.error(f"Failed to update error status for item {item_id}: {str(update_error)}")