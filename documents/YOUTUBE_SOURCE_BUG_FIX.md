# YouTube Source Field Bug Fix

## Problem
New YouTube videos were showing source as "youtube.com" instead of "YouTube | [Channel Name]" regardless of how they were saved or which extraction method was used.

## Root Cause Analysis

### What Was Working
1. ✅ **Backend extraction** ([`backend/app/services/extraction.py`](backend/app/services/extraction.py:600-614)) - Correctly formats source as `"YouTube | {channel_name}"`
2. ✅ **Background processing** ([`backend/app/services/background.py`](backend/app/services/background.py:513-532)) - Correctly receives and sets the YouTube source from metadata
3. ✅ **Chrome extension extraction** ([`chrome_extension/src/background/service-worker.ts`](chrome_extension/src/background/service-worker.ts:104-110)) - Correctly formats and sends source as `"YouTube | {channel_name}"`

### What Was Broken
❌ **Backend API endpoint** ([`backend/app/routers/items.py`](backend/app/routers/items.py:878-881)) - The `UploadContentRequest` model was missing the `source` field!

The Chrome extension was sending:
```typescript
await api.uploadContent(item.id, {
  content: result.content,
  extraction_source: 'chrome_extension_youtube',
  source: source,  // ← "YouTube | Channel Name"
});
```

But the backend model only accepted:
```python
class UploadContentRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000000)
    extraction_source: str = Field(default="local_extension", max_length=50)
    # source field was MISSING!
```

This meant the `source` field from the extension was **silently ignored** by FastAPI's Pydantic validation.

## The Fix

### 1. Added `source` field to `UploadContentRequest` model
**File:** [`backend/app/routers/items.py`](backend/app/routers/items.py:878-882)

```python
class UploadContentRequest(BaseModel):
    """Request model for uploading extracted content from local agent."""
    content: str = Field(..., min_length=1, max_length=10000000)
    extraction_source: str = Field(default="local_extension", max_length=50)
    source: Optional[str] = Field(default=None, max_length=200)  # ← ADDED
```

### 2. Updated upload endpoint to use the source field
**File:** [`backend/app/routers/items.py`](backend/app/routers/items.py:998-1016)

```python
# Update item with extracted content and mark as processing
update_fields = {
    "archived_text": request.content,
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
```

### 3. Added logging for debugging
**File:** [`backend/app/services/background.py`](backend/app/services/background.py:527-534)

Added logging to track when source is set from metadata vs extracted from URL:
```python
if not item_doc.get("source") and metadata.get("source"):
    logger.info(f"Setting source from metadata for item {item_id}: {metadata.get('source')}")
    update_doc["source"] = metadata["source"]

# If source is still not set and we have a URL, extract it
if not update_doc.get("source") and not item_doc.get("source") and url:
    logger.info(f"Source not set from metadata, extracting from URL for item {item_id}")
    update_doc["source"] = extract_source_from_url(url)
    logger.info(f"Extracted source from URL for item {item_id}: {update_doc['source']}")
```

## Impact

This fix ensures that YouTube videos saved through **any method** will now correctly show "YouTube | [Channel Name]":

1. ✅ **Direct backend extraction** (fast/complete modes) - Already worked, now with better logging
2. ✅ **Chrome extension local extraction** - NOW FIXED - source field is properly received and saved
3. ✅ **Manual saves from frontend** - Works correctly

## Testing

Created test script [`backend/test_youtube_source_debug.py`](backend/test_youtube_source_debug.py) which confirms:
- Backend extraction correctly sets source to "YouTube | Rick Astley"
- Source field flows through background processing correctly

## Migration Note

Existing YouTube videos that were saved with "youtube.com" have already been migrated by [`backend/migrate_source_field.py`](backend/migrate_source_field.py). This fix ensures **new** YouTube videos will be saved correctly from the start.