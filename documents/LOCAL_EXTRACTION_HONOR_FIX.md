# Local Extraction Honor Fix

## Problem

When a user explicitly selected "local" extraction type, the system was ignoring this choice and attempting server-side extraction anyway. This resulted in:

1. Wasted server resources attempting extraction that would be ignored
2. Confusing logs showing Readability/Playwright attempts for "local" items
3. User's explicit choice not being respected

### Example from Terminal Logs

```
Readability extracted insufficient content (718 chars)...trying Playwright
```

This showed the system attempting server-side extraction even when `extraction_type` was set to "local".

## Root Cause

In [`backend/app/services/background.py`](backend/app/services/background.py), the check for `extraction_type == "local"` was:

1. **Positioned too late** in the processing flow (after status was set to "processing")
2. **Had a conditional** that only triggered when `not archived_text`, meaning if there was any existing archived_text, it would skip the early return and proceed to extraction

This meant the system would attempt server-side extraction before checking if the user explicitly chose local extraction.

## Solution

### Code Changes

**File:** [`backend/app/services/background.py`](backend/app/services/background.py:172-224)

**Key Change:** Moved the "local" extraction check to the **very beginning** of the processing logic, before any status updates or extraction attempts.

```python
# CRITICAL: Honor explicit "local" extraction choice
# If user explicitly chose "local" extraction and there's no archived_text yet,
# skip all server-side extraction and wait for browser extension
if url and extraction_type == "local" and not is_youtube and not archived_text:
    logger.info(f"User explicitly chose 'local' extraction for {url}, skipping server-side extraction")
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
    return  # Exit early, wait for browser extension to provide content
```

### Behavior Changes

#### Before Fix
1. User selects "local" extraction
2. System sets status to "processing"
3. System attempts Readability extraction
4. System attempts Playwright extraction
5. Only after failures, falls back to "pending_local_extraction"

#### After Fix
1. User selects "local" extraction
2. System **immediately** sets status to "pending_local_extraction"
3. System **skips all server-side extraction**
4. System waits for browser extension to provide content via `/api/v1/items/{item_id}/content`

## Testing

### Test Script

Created [`backend/test_local_extraction_honor_choice.py`](backend/test_local_extraction_honor_choice.py) to verify the fix.

### Test Results

```
✅ TEST PASSED: Explicit 'local' extraction choice was honored!
   - No server-side extraction was attempted
   - Status set to 'pending_local_extraction'
   - System is waiting for browser extension
```

**Verification:**
- ✅ Status is 'pending_local_extraction' (correct)
- ✅ No archived_text (server-side extraction was skipped)
- ✅ extraction_type remains 'local' (not changed)

## Impact

### Benefits

1. **Respects user choice** - When user explicitly selects "local", system honors it
2. **Saves server resources** - No wasted Readability/Playwright attempts
3. **Clearer logs** - No confusing extraction attempts for local items
4. **Faster processing** - Immediate status update instead of waiting for extraction failures

### Backward Compatibility

✅ **Fully backward compatible**

- Existing items with `extraction_type="local"` and `archived_text` already present continue to work
- Automatic cascade fallback (fast → complete → local) still works for server-side extraction failures
- YouTube URLs still attempt backend extraction first (as intended)

## Related Files

- [`backend/app/services/background.py`](backend/app/services/background.py) - Main fix
- [`backend/test_local_extraction_honor_choice.py`](backend/test_local_extraction_honor_choice.py) - Test verification
- [`documents/LOCAL_EXTRACTION_PLAN.md`](documents/LOCAL_EXTRACTION_PLAN.md) - Original feature plan
- [`documents/EXTRACTION_TYPE_FEATURE.md`](documents/EXTRACTION_TYPE_FEATURE.md) - Feature documentation

## Date

2026-01-25