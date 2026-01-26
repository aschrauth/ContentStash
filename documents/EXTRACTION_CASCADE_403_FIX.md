# Extraction Cascade 403 Fix

## Problem Summary

When "fast" extraction mode encountered a 403 Forbidden error, it immediately raised `ExtractionBlockError` and fell back to local extraction, bypassing the intended cascade sequence (fast→complete→local).

### Root Cause

In [`backend/app/services/extraction.py:479-484`](backend/app/services/extraction.py:479-484), the exception handler for `requests.RequestException` would:
1. Detect 403/401/Forbidden errors
2. Immediately raise `ExtractionBlockError`
3. This prevented the Playwright fallback (lines 488-492) from being attempted

The `ExtractionBlockError` was then caught in [`backend/app/services/background.py:295-309`](backend/app/services/background.py:295-309), which immediately triggered local extraction fallback, skipping the "complete" mode entirely.

## Solution Implemented

Modified the exception handler in [`backend/app/services/extraction.py`](backend/app/services/extraction.py) to:

1. **Detect 403/401/Forbidden errors** but don't immediately raise `ExtractionBlockError`
2. **Attempt Playwright fallback** to bypass bot detection
3. **Only raise `ExtractionBlockError`** if BOTH `requests.get()` AND Playwright fail with access errors

### Code Changes

**File:** `backend/app/services/extraction.py`

**Lines Modified:** 479-503

**Key Changes:**
- When a 403/401/Forbidden error occurs, log a warning instead of immediately raising an exception
- Attempt Playwright extraction to bypass bot detection
- Only raise `ExtractionBlockError` if Playwright also fails
- This allows the cascade logic in `background.py` to work correctly

## How It Works Now

### Fast Mode Cascade (Fixed)
1. **Try `requests.get()`** → Gets 403 Forbidden
2. **Try Playwright fallback** → Succeeds (bypasses bot detection)
3. **Return content** with method="complete"

If Playwright also fails:
4. **Raise `ExtractionBlockError`**
5. **Cascade to complete mode** (in background.py)
6. **If complete fails** → Cascade to local mode

### Complete Mode (Unchanged)
1. **Skip `requests.get()`**
2. **Use Playwright directly** → Succeeds
3. **Return content** with method="complete"

## Test Results

Created test script: `backend/test_extraction_cascade_403_fix.py`

**Test URL:** https://www.theneurondaily.com/p/world-models-just-got-primed-for-their-chatgpt-moment
- This URL returns 403 for `requests.get()` but works with Playwright

**Test Results:**
```
✓ PASSED: Fast mode 403 handling
  - requests.get() failed with 403
  - Playwright fallback succeeded
  - Extracted 25,546 characters
  - Method correctly shows "complete"

✓ PASSED: Complete mode
  - Skipped requests.get()
  - Playwright succeeded directly
  - Extracted 25,497 characters
  - Method correctly shows "complete"
```

## Benefits

1. **Improved Success Rate:** URLs that return 403 for simple requests now work in fast mode
2. **Proper Cascade:** The fast→complete→local cascade now works as designed
3. **Better User Experience:** Users get content faster without needing to manually switch modes
4. **Backward Compatible:** Existing behavior for other error types unchanged
5. **YouTube URLs:** Still properly raise `ExtractionBlockError` to skip to local extraction

## Files Modified

- `backend/app/services/extraction.py` (lines 479-503)

## Files Created

- `backend/test_extraction_cascade_403_fix.py` (test script)
- `documents/EXTRACTION_CASCADE_403_FIX.md` (this document)

## Testing Recommendations

1. **Test with 403 URLs:** Verify fast mode now uses Playwright fallback
2. **Test cascade logic:** Ensure fast→complete→local still works
3. **Test YouTube URLs:** Verify they still skip to local extraction
4. **Test normal URLs:** Ensure existing behavior unchanged

## Related Issues

This fix addresses the extraction cascade bug where bot-protected sites (like Substack) would immediately fall back to local extraction instead of trying Playwright first.