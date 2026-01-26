# Local Extraction Content Preservation Fix

## Problem Summary

When the browser extension uploaded locally-extracted content via the `/api/v1/items/{item_id}/content` endpoint, the system was incorrectly triggering server-side extraction (Readability/Playwright), which would overwrite the locally-extracted content with server-extracted content.

### Root Cause

The issue occurred in the interaction between two components:

1. **`/content` endpoint** ([`backend/app/routers/items.py:849-1007`](backend/app/routers/items.py:849-1007))
   - Received locally-extracted content from browser extension
   - Saved it to `archived_text` field
   - Called `process_item_background()` to handle post-processing

2. **`process_item_background()` function** ([`backend/app/services/background.py:136-521`](backend/app/services/background.py:136-521))
   - Had an early-return check for `extraction_type == "local"` (line 183-195)
   - BUT this check only returned early if `not archived_text`
   - Since the `/content` endpoint had ALREADY set `archived_text`, the check failed
   - The function continued to line 229 and attempted server-side extraction
   - This overwrote the locally-extracted content

### Evidence from Logs

```
PATCH /api/v1/items/6976c10e007fc1cffbbcfa6d/content HTTP/1.1" 200 OK
Readability extracted insufficient content (718 chars)...trying Playwright
```

This showed that after receiving local content, the system was still attempting server-side extraction.

## Solution

Added a `skip_extraction` parameter to `process_item_background()` to explicitly indicate when content has already been provided and extraction should be skipped entirely.

### Changes Made

#### 1. Updated `process_item_background()` signature ([`backend/app/services/background.py:136`](backend/app/services/background.py:136))

```python
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
```

#### 2. Added extraction skip logic ([`backend/app/services/background.py:232-239`](backend/app/services/background.py:232-239))

```python
# Skip extraction if content was already provided (e.g., from local extraction upload)
if skip_extraction:
    logger.info(f"Skipping extraction for item {item_id} - content already provided")
    if not archived_text:
        logger.error(f"skip_extraction=True but no archived_text for item {item_id}")
        raise Exception("Content extraction skipped but no archived_text available")
elif url:
    # ... existing extraction logic
```

#### 3. Updated `/content` endpoint to pass `skip_extraction=True` ([`backend/app/routers/items.py:978-984`](backend/app/routers/items.py:978-984))

```python
# Trigger background processing for embeddings and AI categorization
# Pass skip_extraction=True since content was already provided by local extraction
background_tasks.add_task(
    process_item_background,
    item_id,
    current_user.id,
    skip_extraction=True
)
```

## Behavior After Fix

When content is uploaded via `/api/v1/items/{item_id}/content` for a "local" extraction item:

1. ✅ Accept the uploaded content
2. ✅ **Skip server-side extraction entirely** (Readability/Playwright NOT called)
3. ✅ **Only run post-extraction processing**:
   - Chunking the content
   - Creating embeddings
   - Generating AI tags and categorization
4. ✅ Set status to "processed"
5. ✅ **Preserve the locally-extracted content**

## Testing

Created comprehensive test: [`backend/test_local_content_upload_fix.py`](backend/test_local_content_upload_fix.py)

### Test Results

```
✅ SUCCESS: Local content was preserved!
   Server extraction was correctly skipped.

🎉 All tests passed!
```

The test verifies:
- Content is accepted and saved
- `process_item_background()` is called with `skip_extraction=True`
- Server-side extraction is NOT triggered
- Original locally-extracted content is preserved
- Item status is set to "processed"

## Impact

### What Changed
- Local extraction content is now preserved and never overwritten
- Server-side extraction is explicitly skipped when content is provided
- Post-extraction processing (embeddings, AI tags) still runs normally

### What Stayed the Same
- All other extraction flows remain unchanged
- The early-return check for `extraction_type == "local"` without content still works
- Cascade fallback logic (fast → complete → local) still works
- Error handling and retry logic unchanged

### Backward Compatibility
- ✅ Fully backward compatible
- The `skip_extraction` parameter defaults to `False`
- All existing calls to `process_item_background()` work without changes
- Only the `/content` endpoint uses the new parameter

## Related Files

- [`backend/app/routers/items.py`](backend/app/routers/items.py) - `/content` endpoint
- [`backend/app/services/background.py`](backend/app/services/background.py) - Background processing
- [`backend/test_local_content_upload_fix.py`](backend/test_local_content_upload_fix.py) - Test verification

## Previous Related Fixes

This fix builds on previous local extraction improvements:
- [`documents/LOCAL_EXTRACTION_HONOR_FIX.md`](documents/LOCAL_EXTRACTION_HONOR_FIX.md) - Initial local extraction support
- [`documents/LOCAL_EXTRACTION_STATUS_FIX.md`](documents/LOCAL_EXTRACTION_STATUS_FIX.md) - Status handling
- [`documents/LOCAL_EXTRACTION_STUCK_ITEM_FIX.md`](documents/LOCAL_EXTRACTION_STUCK_ITEM_FIX.md) - Queue management

## Conclusion

The fix successfully prevents server-side extraction from overwriting locally-extracted content by introducing an explicit `skip_extraction` parameter. This ensures that when the browser extension provides content, it is preserved exactly as extracted locally, while still allowing all post-extraction processing (embeddings, AI categorization) to run normally.