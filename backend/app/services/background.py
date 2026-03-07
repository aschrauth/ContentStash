"""
Background processing service for saved items.
"""
import logging
import json
import re
from datetime import datetime
from bson import ObjectId
from typing import Optional, Dict, Any

from app.database import get_database, get_item_chunks_collection
from app.services.metadata import fetch_metadata
from app.services.extraction import extract_content, extract_content_with_metadata, extract_source_from_url
from app.services.exceptions import ExtractionBlockError
from app.services.ai import generate_tags_and_topic
from app.services.chunking import chunk_text
from app.services.gemini import gemini_service, GeminiServiceError
from app.services.youtube import is_youtube_url, extract_video_id, get_youtube_channel_name_only
from app.config import settings

logger = logging.getLogger(__name__)


def _normalize_summary_value(value: Any) -> str:
    """
    Normalize summary values from Gemini into bullet-point markdown text.
    Handles string, list, and nested dictionary shapes.
    """
    if isinstance(value, str):
        summary = value.strip()
        return summary

    if isinstance(value, list):
        bullets = []
        for item in value:
            if not isinstance(item, str):
                continue
            text = item.strip()
            if not text:
                continue
            text = text.lstrip("-* ").strip()
            bullets.append(f"- {text}")
        return "\n".join(bullets)

    if isinstance(value, dict):
        for key in ("bullets", "points", "items", "summary"):
            normalized = _normalize_summary_value(value.get(key))
            if normalized:
                return normalized

    return ""


def _extract_summary(categorization: Dict[str, Any]) -> str:
    """Extract summary from multiple possible Gemini key formats."""
    summary_keys = (
        "summary",
        "key_points",
        "keyPoints",
        "highlights",
        "bullet_points",
        "bullets",
    )

    for key in summary_keys:
        normalized = _normalize_summary_value(categorization.get(key))
        if normalized:
            return normalized
    return ""


def _extractive_summary_fallback(content: str, max_points: int = 5) -> str:
    """
    Deterministic fallback summary when AI output is unavailable or malformed.
    Extracts the first few substantial sentences from the cleaned article text.
    """
    if not content:
        return ""

    text = content
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*_`>|]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return ""

    bullet_lines = []
    seen = set()

    sentences = re.split(r"(?<=[.!?])\s+", text)
    for sentence in sentences:
        cleaned = sentence.strip(" -•\t\r\n")
        if len(cleaned) < 45 or len(cleaned) > 280:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        if cleaned.startswith("http://") or cleaned.startswith("https://"):
            continue
        seen.add(lowered)
        bullet_lines.append(f"- {cleaned}")
        if len(bullet_lines) >= max_points:
            break

    return "\n".join(bullet_lines)


def _coerce_text_to_bullets(text: str, max_points: int = 5) -> str:
    """
    Convert freeform text or loosely formatted bullets into normalized bullet markdown.
    """
    if not text:
        return ""

    bullet_lines = []
    seen = set()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        line = re.sub(r"^(summary|key points|highlights)\s*:\s*", "", line, flags=re.IGNORECASE)
        line = re.sub(r"^[-*•\d\.\)\s]+", "", line).strip()
        if len(line) < 20:
            continue
        lowered = line.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        bullet_lines.append(f"- {line}")
        if len(bullet_lines) >= max_points:
            break

    if bullet_lines:
        return "\n".join(bullet_lines)

    return _extractive_summary_fallback(text, max_points=max_points)


def _parse_categorization_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse Gemini categorization output, tolerating wrapper prose around the JSON object.
    """
    candidates = [response_text]

    first_brace = response_text.find("{")
    last_brace = response_text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidates.append(response_text[first_brace:last_brace + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    return None


def _generate_summary_fallback(content_sample: str) -> str:
    """
    Fallback summary generation when Gemini omits summary in structured output.
    Returns 3-5 bullet lines or empty string on failure.
    """
    if not content_sample or not gemini_service.is_available():
        return ""

    try:
        prompt = f"""Write 3 to 5 concise bullet points capturing the key points of this content.

Content:
{content_sample}

Rules:
- Start each line with "- "
- Return bullet lines only
- No intro or conclusion text"""

        response = gemini_service.generate_content(
            prompt=prompt,
            model="gemini-2.5-flash-lite"
        )

        if not response:
            return ""

        lines = []
        for raw_line in response.strip().splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = line.lstrip("-* ").strip()
            if not line:
                continue
            lines.append(f"- {line}")
            if len(lines) >= 5:
                break

        return "\n".join(lines)
    except Exception as e:
        logger.warning(f"Fallback summary generation failed: {str(e)}")
        return ""


def generate_auto_categorization(archived_text: str) -> Optional[Dict[str, Any]]:
    """
    Generate auto-categorization using Gemini 2.5 Flash-Lite.
    
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
        logger.info("Gemini service not available, using extractive summary fallback")
        summary = _extractive_summary_fallback(archived_text)
        if summary:
            return {
                "suggested_tags": [],
                "topic": "",
                "summary": summary
            }
        return None
    
    try:
        # Use first 3000 chars for better bullet-point context
        content_sample = archived_text[:3000].strip()

        # Construct concise prompt for structured JSON output
        prompt = f"""Analyze this content and provide categorization in JSON format.

Content: {content_sample}

Respond with JSON only:
{{
  "suggested_tags": ["tag1", "tag2", "tag3"],
  "topic": "main topic",
  "summary": "- Key point one\\n- Key point two\\n- Key point three"
}}

For "summary": write 3 to 5 bullet points covering the key points of the article. Each bullet must start with "- ". Use fewer bullets for shorter or simpler content. Do not repeat the title."""

# Call Gemini with Flash-Lite model
        response = gemini_service.generate_content(
            prompt=prompt,
            model="gemini-2.5-flash-lite"
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
        
        categorization = _parse_categorization_response(response_text)

        # Validate structure
        if not isinstance(categorization, dict):
            logger.warning("Categorization response was not valid JSON; using summary fallback")
            summary = _coerce_text_to_bullets(response_text) or _extractive_summary_fallback(archived_text)
            if summary:
                return {
                    "suggested_tags": [],
                    "topic": "",
                    "summary": summary
                }
            return None

        # Extract and validate fields
        suggested_tags = categorization.get("suggested_tags", [])
        topic = categorization.get("topic", "")
        summary = _extract_summary(categorization)

        # If Gemini omitted summary in structured output, do a summary-only fallback call.
        if not summary:
            summary = _generate_summary_fallback(content_sample) or _extractive_summary_fallback(archived_text)

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
            
    except GeminiServiceError as e:
        logger.error(f"Gemini service error during auto-categorization: {str(e)}")
        summary = _extractive_summary_fallback(archived_text)
        if summary:
            return {
                "suggested_tags": [],
                "topic": "",
                "summary": summary
            }
        return None
    except Exception as e:
        logger.error(
            f"Unexpected error during auto-categorization: {str(e)}",
            exc_info=True
        )
        summary = _extractive_summary_fallback(archived_text)
        if summary:
            return {
                "suggested_tags": [],
                "topic": "",
                "summary": summary
            }
        return None


async def process_item_background(item_id: str, user_id: str, skip_extraction: bool = False):
    """
    Background task to process a saved item:
    1. Update status to 'pending'
    2. Fetch metadata (if missing)
    3. Extract content -> save to archivedText (unless skip_extraction=True)
    4. Generate AI suggestions -> save to suggestedTags, suggestedTopic
    5. Update item with results and set status to 'processed'
    6. Handle errors by setting status to 'failed' and saving processingError
    
    Args:
        item_id: The ID of the item to process
        user_id: The ID of the user who owns the item (for verification)
        skip_extraction: If True, skip content extraction (content already provided)
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
        
        # Get the URL, archived_text, and extraction_type
        url = item_doc.get("url")
        archived_text = item_doc.get("archived_text")
        extraction_type = item_doc.get("extraction_type", "fast")
        
        # Check if it's a YouTube URL
        is_youtube = is_youtube_url(url) if url else False
        
        # CRITICAL: Honor explicit "local" extraction choice
        # If user explicitly chose "local" extraction, handle based on whether content exists
        if url and extraction_type == "local" and not is_youtube:
            logger.info(f"Item {item_id} has extraction_type='local'")
            
            # If archived_text already exists, this is likely a direct save from extension
            # Don't clear it - just process it for embeddings and categorization
            if archived_text and len(archived_text.strip()) > 100:
                logger.info(f"Item {item_id} already has content from local extraction, proceeding with processing")
                # Continue to processing below (embeddings, categorization)
            else:
                # No content yet - mark as pending local extraction and wait for extension
                logger.info(f"Item {item_id} has no content yet, waiting for local extraction by browser extension")
                await db.saved_items.update_one(
                    {"_id": ObjectId(item_id)},
                    {
                        "$set": {
                            "processing_status": "pending_local_extraction",
                            "processing_error": "Waiting for local extraction by browser extension",
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                return
        
        # Update status to processing (not pending, to avoid infinite loop in local extraction)
        # Only update if not already processing to avoid race conditions
        current_status = item_doc.get("processing_status")
        if current_status != "processing":
            await db.saved_items.update_one(
                {"_id": ObjectId(item_id)},
                {
                    "$set": {
                        "processing_status": "processing",
                        "processing_error": None,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        
        # Step 1: Fetch metadata (if missing and URL exists)
        # For YouTube URLs, we handle source separately with a lightweight function
        metadata = {}
        should_fetch_metadata = url and (
            not item_doc.get("title") or
            not item_doc.get("description")
        )
        
        if should_fetch_metadata:
            logger.info(f"📋 [METADATA] Fetching metadata for {url} (is_youtube={is_youtube})")
            # Use extract_content_with_metadata to get source along with other metadata
            metadata_result = await extract_content_with_metadata(url, extraction_type)
            if metadata_result:
                logger.info(f"📋 [METADATA] Received metadata with source: '{metadata_result.get('source')}'")
                metadata = {
                    'title': metadata_result.get('title'),
                    'description': metadata_result.get('description'),
                    'image_url': metadata_result.get('image_url'),
                    'source': metadata_result.get('source')
                }
                # If we got content from metadata extraction, use it
                if metadata_result.get('text') and not archived_text:
                    archived_text = metadata_result['text']
                    logger.info(f"📋 [METADATA] Using content from metadata extraction for {url}")
        
        # Step 2: Extract content
        # - If skip_extraction=True: Content already provided, skip extraction entirely
        # - For YouTube URLs: Always try backend extraction first
        #   - If blocked (ExtractionBlockError), mark as pending_local_extraction
        #   - If successful, process normally
        # - For non-YouTube URLs with extraction_type="local": Already handled above (early return)
        # - If URL exists, extract content (to support reprocessing with different extraction_type)
        # - If no URL but archived_text exists, use existing text (pasted content or local extraction completed)
        
        # Extract content from URL with cascade fallback
        # extract_content now returns (content, actual_extraction_method)
        actual_extraction_method = extraction_type  # Default to requested type
        
        # Skip extraction if content was already provided (e.g., from local extraction upload)
        if skip_extraction:
            logger.info(f"Skipping extraction for item {item_id} - content already provided")
            if not archived_text:
                logger.error(f"skip_extraction=True but no archived_text for item {item_id}")
                raise Exception("Content extraction skipped but no archived_text available")
        elif url:
            logger.info(f"Extracting content from {url} using extraction_type={extraction_type}")
            try:
                archived_text, actual_extraction_method = await extract_content(url, extraction_type=extraction_type)
                
                # Check if extraction returned None - implement cascade fallback
                if archived_text is None:
                    logger.warning(f"Extraction returned no content for {url} with extraction_type={extraction_type}")
                    
                    # Cascade: fast → complete → local
                    if extraction_type == "fast":
                        # Try "complete" next
                        logger.info(f"Falling back from 'fast' to 'complete' extraction for {url}")
                        await db.saved_items.update_one(
                            {"_id": ObjectId(item_id)},
                            {
                                "$set": {
                                    "extraction_type": "complete",
                                    "processing_status": "pending",
                                    "processing_error": "Fast extraction returned no content, retrying with complete mode",
                                    "updated_at": datetime.utcnow()
                                }
                            }
                        )
                        # Re-trigger background processing with new extraction_type
                        from app.services.background import process_item_background
                        await process_item_background(item_id, user_id)
                        return
                    elif extraction_type == "complete":
                        # Fall back to "local"
                        logger.info(f"Falling back from 'complete' to 'local' extraction for {url}")
                        await db.saved_items.update_one(
                            {"_id": ObjectId(item_id)},
                            {
                                "$set": {
                                    "extraction_type": "local",
                                    "processing_status": "pending_local_extraction",
                                    "processing_error": "Server extraction failed, waiting for local extraction by browser extension",
                                    "updated_at": datetime.utcnow()
                                }
                            }
                        )
                        return
                    else:
                        # Already on "local" - this shouldn't happen as local extraction is client-side
                        # Mark as failed
                        logger.error(f"Local extraction type but no content for {url}")
                        raise Exception("Local extraction type but no archived_text provided")
                        
            except ExtractionBlockError as e:
                # Server-side extraction was blocked - fall back to local extraction
                logger.warning(f"Extraction blocked for {url}: {str(e)}")
                await db.saved_items.update_one(
                    {"_id": ObjectId(item_id)},
                    {
                        "$set": {
                            "extraction_type": "local",
                            "processing_status": "pending_local_extraction",
                            "processing_error": f"Server blocked, falling back to local extraction: {str(e)}",
                            "updated_at": datetime.utcnow()
                        }
                    }
                )
                return
            except Exception as e:
                # Generic extraction error - implement cascade fallback
                logger.error(f"Extraction failed for {url} with extraction_type={extraction_type}: {str(e)}")
                
                # Cascade: fast → complete → local
                if extraction_type == "fast":
                    # Try "complete" next
                    logger.info(f"Falling back from 'fast' to 'complete' extraction for {url}")
                    await db.saved_items.update_one(
                        {"_id": ObjectId(item_id)},
                        {
                            "$set": {
                                "extraction_type": "complete",
                                "processing_status": "pending",
                                "processing_error": f"Fast extraction failed, retrying with complete mode: {str(e)}",
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    # Re-trigger background processing with new extraction_type
                    from app.services.background import process_item_background
                    await process_item_background(item_id, user_id)
                    return
                elif extraction_type == "complete":
                    # Fall back to "local"
                    logger.info(f"Falling back from 'complete' to 'local' extraction for {url}")
                    await db.saved_items.update_one(
                        {"_id": ObjectId(item_id)},
                        {
                            "$set": {
                                "extraction_type": "local",
                                "processing_status": "pending_local_extraction",
                                "processing_error": f"Server extraction failed, falling back to local extraction: {str(e)}",
                                "updated_at": datetime.utcnow()
                            }
                        }
                    )
                    return
                else:
                    # Already on "local" or unknown type - mark as failed
                    raise
        elif archived_text:
            logger.info(f"Using existing archived_text for item {item_id} (pasted content)")
        else:
            logger.warning(f"No URL or archived_text for item {item_id}, skipping processing")
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

            if not auto_categorization:
                fallback_summary = _generate_summary_fallback(archived_text[:3000].strip()) or _extractive_summary_fallback(archived_text)
                if fallback_summary:
                    auto_categorization = {
                        "suggested_tags": [],
                        "topic": "",
                        "summary": fallback_summary
                    }
                    logger.info(f"Recovered fallback summary for item {item_id}")
            elif not auto_categorization.get("summary"):
                fallback_summary = _generate_summary_fallback(archived_text[:3000].strip()) or _extractive_summary_fallback(archived_text)
                if fallback_summary:
                    auto_categorization["summary"] = fallback_summary
                    logger.info(f"Filled missing summary fallback for item {item_id}")
            
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
                
                if chunks:
                    # Embed all chunks in batch for efficiency
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
        word_count = len(archived_text.split()) if archived_text else 0
        
        # RACE CONDITION FIX: Look-Before-Write strategy for archived_text field
        # Re-fetch item to see if valid content was uploaded by extension during our processing
        # This prevents a slow failing background task from overwriting good extension-provided content.
        logger.info(f"🔍 [RACE CHECK] Checking for race condition on archived_text for item {item_id}")
        current_item_dict = await db.saved_items.find_one({"_id": ObjectId(item_id)})
        existing_archived_text = current_item_dict.get("archived_text") if current_item_dict else None
        
        # Determine if we should keep existing content
        # We prefer existing content if:
        # 1. It already exists AND is longer than 100 chars
        # 2. AND our new content is empty OR is just a placeholder error message
        should_keep_existing = False
        is_placeholder = archived_text and "[Transcript not available" in archived_text
        
        if existing_archived_text and len(existing_archived_text.strip()) > 100:
            if not archived_text or len(archived_text.strip()) < 100 or is_placeholder:
                should_keep_existing = True
                logger.info(f"🛑 [RACE CHECK] Keeping existing valid content (len={len(existing_archived_text)}) over new failed/placeholder content")
        
        if should_keep_existing:
            archived_text = existing_archived_text
            word_count = current_item_dict.get("word_count", word_count)

        update_doc = {
            "processing_status": "processed",
            "updated_at": datetime.utcnow(),
            "archived_text": archived_text,
            "word_count": word_count,
            "suggested_tags": ai_suggestions.get("tags"),
            "suggested_topic": ai_suggestions.get("topic"),
            "ai_summary": None,  # Reset so stale summary is cleared on reprocessing
            "extraction_type": actual_extraction_method  # Update with actual method used
        }
        
        # Log if extraction method changed due to cascade
        if actual_extraction_method != extraction_type:
            logger.info(
                f"Extraction method cascaded from '{extraction_type}' to '{actual_extraction_method}' "
                f"for item {item_id}"
            )
        
        # Add auto-categorization results if available
        if auto_categorization:
            # Override suggested_tags and topic with Gemini results if available
            if auto_categorization.get("suggested_tags"):
                update_doc["suggested_tags"] = auto_categorization["suggested_tags"]
            if auto_categorization.get("topic"):
                update_doc["suggested_topic"] = auto_categorization["topic"]
            summary = auto_categorization.get("summary")
            if isinstance(summary, str) and summary.strip():
                update_doc["ai_summary"] = summary.strip()
        
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
            
            if not item_doc.get("source") and metadata.get("source"):
                logger.info(f"📋 [SOURCE] Setting source from metadata for item {item_id}: '{metadata.get('source')}'")
                update_doc["source"] = metadata["source"]
        
        # If source is still not set and we have a URL, extract it
        # CRITICAL: Check update_doc first - if we just set source from metadata, don't overwrite it!
        # For YouTube URLs, use lightweight channel name extraction (no transcript)
        if not update_doc.get("source") and not item_doc.get("source") and url:
            if is_youtube:
                logger.info(f"📋 [SOURCE] YouTube URL detected, using lightweight channel name extraction for item {item_id}")
                video_id = extract_video_id(url)
                if video_id:
                    youtube_source = get_youtube_channel_name_only(video_id, settings.youtube_api_key)
                    update_doc["source"] = youtube_source
                    logger.info(f"📋 [SOURCE] Got YouTube source for item {item_id}: '{youtube_source}'")
                else:
                    logger.warning(f"📋 [SOURCE] Could not extract video ID from YouTube URL for item {item_id}")
                    update_doc["source"] = "YouTube"
            else:
                logger.info(f"📋 [SOURCE] Source not set from metadata, extracting from URL for item {item_id}")
                update_doc["source"] = extract_source_from_url(url)
                logger.info(f"📋 [SOURCE] Extracted source from URL for item {item_id}: '{update_doc['source']}'")
        
        # RACE CONDITION FIX: Check-Before-Write strategy for source field
        # Re-fetch item to check if source was set by extension/user during processing
        # This prevents the background worker from overwriting high-quality sources
        # (e.g., "YouTube | Channel Name") with generic fallbacks (e.g., "youtube.com")
        if "source" in update_doc:
            logger.info(f"🔍 [RACE CHECK] Checking for race condition on source field for item {item_id}")
            current_item_dict = await db.saved_items.find_one({"_id": ObjectId(item_id)})
            current_source = current_item_dict.get("source") if current_item_dict else None
            new_source = update_doc["source"]
            
            logger.info(f"🔍 [RACE CHECK] Current source in DB: '{current_source}'")
            logger.info(f"🔍 [RACE CHECK] New source to set: '{new_source}'")
            
            # Determine if we should update the source
            should_update_source = False
            
            if not current_source:
                # No source set yet, use our extracted one
                should_update_source = True
                logger.info(f"✅ [RACE CHECK] No existing source, setting: '{new_source}'")
            elif new_source and new_source.startswith("YouTube |") and current_source == "youtube.com":
                # Upgrade from generic to specific YouTube source
                should_update_source = True
                logger.info(f"⬆️ [RACE CHECK] Upgrading from '{current_source}' to '{new_source}'")
            elif new_source and current_source and not current_source.startswith("YouTube |") and new_source.startswith("YouTube |"):
                # Upgrade to YouTube-specific source
                should_update_source = True
                logger.info(f"⬆️ [RACE CHECK] Upgrading from '{current_source}' to '{new_source}'")
            else:
                # Keep existing source - don't overwrite high-quality source with generic one
                logger.info(f"🛑 [RACE CHECK] Keeping existing source: '{current_source}' (not overwriting with '{new_source}')")
                update_doc["source"] = current_source  # Use existing value
        
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
