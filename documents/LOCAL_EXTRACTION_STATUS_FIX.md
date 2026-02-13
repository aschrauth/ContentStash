# Local Extraction Status Fix

## Overview
Fixed critical issues with processing status updates and queue management for local extraction to ensure clear separation between server and local processing.

## Issues Fixed

### 1. Processing Status Flow for Local Extraction
**Problem**: The flow for local extraction was correct but needed clarification.

**Solution**: The existing flow is correct:
1. Chrome extension uploads content via [`/api/v1/items/{id}/content`](../backend/app/routers/items.py:731-842)
2. Endpoint sets status to `"processing"` (line 806)
3. Background task processes the content (embeddings, AI categorization)
4. Background task sets final status to `"processed"` (line 386 in [`background.py`](../backend/app/services/background.py:386))

**Key Fix**: Added safeguard in [`background.py:223`](../backend/app/services/background.py:223) to check if `archived_text` already exists before marking item for local extraction. This ensures that when local extraction completes and uploads content, the background task processes it instead of re-queuing it.

### 2. Pending Local Queue Filtering
**Problem**: The [`/api/v1/items/pending-local`](../backend/app/routers/items.py:338-389) endpoint didn't filter out items that already had content, causing processed items to remain in the queue.

**Solution**: Added explicit filter to exclude items with content:
```python
query = {
    "owner_id": ObjectId(current_user.id),
    "extraction_type": "local",  # MUST be local
    "processing_status": {"$in": ["pending", "pending_local_extraction"]},
    "$or": [
        {"archived_text": {"$exists": False}},
        {"archived_text": ""},
        {"archived_text": None}
    ],
}
```

### 3. Server vs Local Processing Separation
**Problem**: Items processed on the server could potentially appear in the local queue.

**Solution**: 
- The `extraction_type: "local"` filter in the pending-local query ensures ONLY items explicitly marked for local extraction appear in the queue
- Items with `extraction_type` of `"fast"` or `"complete"` will NEVER appear in the local queue, regardless of their `processing_status`
- Added comprehensive documentation to clarify this separation

## Status Flow Documentation

### Local Extraction Flow
1. **Item Created**: `extraction_type="local"`, `processing_status="pending"`
2. **Background Task Runs**: Detects `extraction_type="local"` and no `archived_text`, sets status to `"pending_local_extraction"` and returns
3. **Chrome Extension Polls**: Gets item from `/api/v1/items/pending-local`
4. **Extension Extracts**: Uploads content via `/api/v1/items/{id}/content`
5. **Content Upload**: Sets status to `"processing"`, triggers background task
6. **Background Task Runs Again**: Detects `archived_text` exists, processes it (embeddings, AI tags)
7. **Final Status**: Background task sets status to `"processed"`

### Server Extraction Flow
1. **Item Created**: `extraction_type="fast"` or `"complete"`, `processing_status="pending"`
2. **Background Task Runs**: Extracts content from server, processes it
3. **Final Status**: Sets status to `"processed"` or `"failed"`
4. **Never Enters Local Queue**: `extraction_type` filter prevents this

## Files Modified

1. **[`backend/app/routers/items.py`](../backend/app/routers/items.py)**
   - Lines 338-389: Enhanced `/pending-local` endpoint with content filtering and documentation

2. **[`backend/app/services/background.py`](../backend/app/services/background.py)**
   - Line 223: Added check for existing `archived_text` before marking for local extraction

## Testing Recommendations

1. **Test Local Extraction Complete Flow**:
   - Create item with `extraction_type="local"`
   - Verify it appears in `/api/v1/items/pending-local`
   - Upload content via `/api/v1/items/{id}/content`
   - Verify status changes to `"processing"` then `"processed"`
   - Verify item no longer appears in pending-local queue

2. **Test Server Extraction Isolation**:
   - Create item with `extraction_type="fast"`
   - Verify it NEVER appears in `/api/v1/items/pending-local`
   - Even if processing fails, verify it stays out of local queue

3. **Test Content Filter**:
   - Create item with `extraction_type="local"` and manually set `archived_text`
   - Verify it does NOT appear in pending-local queue

## Key Principles

1. **Explicit Separation**: Only items with `extraction_type="local"` can enter the local queue
2. **Content-Based Filtering**: Items with content are excluded from the local queue
3. **Status Progression**: Local extraction follows: `pending` → `pending_local_extraction` → `processing` → `processed`
4. **No Automatic Fallback**: Server processing failures do NOT automatically switch items to local extraction

## Date
2026-01-21