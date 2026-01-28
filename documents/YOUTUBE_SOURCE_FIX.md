# YouTube Source Display Fix

## Problem
YouTube videos were displaying source as "youtube.com" instead of "YouTube | [Channel Name]" regardless of how they were saved (Save Modal or Chrome Extension) or extraction method (fast, complete, or local).

## Root Cause
The bug was in [`backend/app/routers/items.py`](../backend/app/routers/items.py) at line 266 in the `create_item` endpoint.

When creating a new item with a URL, the code was calling `extract_source_from_url()` for ALL URLs, including YouTube URLs:

```python
if item_data.url:
    # For URLs, extract source from URL immediately for API response
    source = extract_source_from_url(item_data.url)
```

The problem: `extract_source_from_url()` is a generic function that simply extracts the domain from any URL (e.g., "youtube.com" for YouTube URLs). It doesn't have YouTube-specific logic.

The correct YouTube source with channel name (e.g., "YouTube | AI For Humans") was being set later during background processing in [`backend/app/services/background.py`](../backend/app/services/background.py) and [`backend/app/services/extraction.py`](../backend/app/services/extraction.py), but by that time the item had already been returned to the client with "youtube.com" as the source.

## Solution

### 1. Fixed Item Creation Logic
Modified [`backend/app/routers/items.py`](../backend/app/routers/items.py) to skip setting source for YouTube URLs during item creation:

```python
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
```

This ensures:
- YouTube URLs: Source is left as `None` initially and will be set by background processing with the correct "YouTube | [Channel Name]" format
- Other URLs: Source is extracted immediately from the domain (e.g., "nytimes.com", "blog.example.com")
- Pasted content: Uses provided source or defaults to "Pasted Content"

### 2. Migration Script
Created [`backend/fix_youtube_sources.py`](../backend/fix_youtube_sources.py) to fix existing YouTube items that had "youtube.com" as their source.

The script:
- Finds all YouTube items with `source="youtube.com"`
- Extracts video ID from each URL
- Fetches metadata using YouTube Data API (with yt-dlp fallback)
- Updates source to "YouTube | [Channel Name]" format
- Falls back to generic "YouTube" if channel name cannot be retrieved

Migration results:
- Fixed: 9 items
- Failed: 0 items

## Verification

### Before Fix
```
URL: https://www.youtube.com/watch?v=fcFOYzMeG7U
Source: youtube.com  ❌
```

### After Fix
```
URL: https://www.youtube.com/watch?v=fcFOYzMeG7U
Source: YouTube | How I AI  ✅
```

## How It Works Now

### For New YouTube Videos
1. User saves a YouTube URL (via Save Modal or Chrome Extension)
2. Item is created with `source=None` (not "youtube.com")
3. Background processing extracts video metadata including channel name
4. Source is set to "YouTube | [Channel Name]" format
5. Frontend displays the correct source

### For Existing YouTube Videos
- All existing items with "youtube.com" have been migrated to "YouTube | [Channel Name]"
- Items can also be reprocessed manually if needed

## Files Modified
- [`backend/app/routers/items.py`](../backend/app/routers/items.py) - Fixed item creation logic
- [`backend/fix_youtube_sources.py`](../backend/fix_youtube_sources.py) - Migration script (new)
- [`backend/debug_youtube_source.py`](../backend/debug_youtube_source.py) - Debug script (new)

## Testing
To verify the fix works:
1. Save a new YouTube video through the Save Modal or Chrome Extension
2. Wait for background processing to complete
3. Check that the source displays as "YouTube | [Channel Name]"
4. Verify it works for all extraction methods (fast, complete, local)

## Related Code
The YouTube source formatting logic is implemented in:
- [`backend/app/services/extraction.py`](../backend/app/services/extraction.py) - Lines 601-603, 638-639
- [`backend/app/services/youtube.py`](../backend/app/services/youtube.py) - Metadata extraction functions
- [`backend/app/services/background.py`](../backend/app/services/background.py) - Background processing that sets the source