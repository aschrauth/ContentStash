# Local Extraction Metadata Auto-Fetch Fix

## Problem
When a URL is shared from the iOS shortcut with "local" extraction type, the item was created with the URL as the title and no metadata was fetched. The Chrome extension would process the local extraction but wouldn't check if metadata was missing, resulting in items with:
- URL as title (e.g., `https://www.nytimes.com/2026/01/29/style/...`)
- No description
- No thumbnail

## Solution
The Chrome extension now automatically detects and fetches missing metadata when processing local extraction items.

## Implementation Details

### 1. API Client Enhancement ([`chrome_extension/src/lib/api.ts`](src/lib/api.ts))
Added a new method to update item metadata:

```typescript
async updateItemMetadata(itemId: string, metadata: {
  title?: string;
  description?: string;
  image_url?: string;
}): Promise<SavedItem>
```

This method sends a PATCH request to `/api/v1/items/{itemId}` to update the item's metadata fields.

### 2. Content Script Metadata Extraction ([`chrome_extension/src/content/content-script.ts`](src/content/content-script.ts))
Added a new function `extractPageMetadata()` that extracts metadata from the page using:

**Priority order for each field:**
- **Title**: Open Graph title → Page title
- **Description**: Open Graph description → Meta description
- **Image**: Open Graph image → Twitter image

The function returns an object with the extracted metadata:
```typescript
{
  title?: string;
  description?: string;
  image?: string;
}
```

### 3. Service Worker Processing Logic ([`chrome_extension/src/background/service-worker.ts`](src/background/service-worker.ts))
Modified [`processGenericItem()`](src/background/service-worker.ts:119) to:

1. **Check if metadata is missing** before content extraction:
   - Title starts with `http://` or `https://`
   - Missing or empty description
   - Missing or empty image_url

2. **Extract metadata** if needed:
   - Inject content script into the tab
   - Call `extractPageMetadata()` to get metadata from the page
   - Log extracted metadata for debugging

3. **Update the item** with extracted metadata:
   - Only update fields that are missing or need replacement
   - Send PATCH request to update the item
   - Continue with content extraction even if metadata update fails

## Workflow

```
1. iOS Shortcut shares URL with "local" extraction type
   ↓
2. Backend creates item with URL as title, status: pending_local_extraction
   ↓
3. Chrome extension polls /api/v1/items/pending-local
   ↓
4. Extension detects missing metadata (title is URL)
   ↓
5. Extension opens tab and waits for page load
   ↓
6. Extension extracts metadata (title, description, image)
   ↓
7. Extension updates item with extracted metadata
   ↓
8. Extension extracts page content
   ↓
9. Extension uploads content to backend
   ↓
10. Item now has proper title, description, and thumbnail
```

## Error Handling

- If metadata extraction fails, the extension logs a warning and continues with content extraction
- If metadata update fails, the extension logs an error and continues with content extraction
- The content extraction process is not blocked by metadata failures

## Testing

To test the implementation:

1. **Share a URL from iOS shortcut** with "local" extraction type
2. **Reload the Chrome extension** in `chrome://extensions`
3. **Trigger processing** by clicking "Process Now" in the extension popup or wait for automatic polling
4. **Check the console logs** in the extension's service worker:
   - Look for `[Generic] Item {id} needs metadata extraction`
   - Look for `[Generic] Extracted metadata:` with the extracted data
   - Look for `✓ [Generic] Updated metadata for item {id}`
5. **Verify in the frontend** that the item now has:
   - Proper title (not the URL)
   - Description
   - Thumbnail image

## Benefits

- **Automatic**: No manual intervention required
- **Seamless**: Works with existing local extraction flow
- **Robust**: Handles failures gracefully
- **Efficient**: Only extracts metadata when needed
- **Compatible**: Works with all URL types (articles, YouTube videos, etc.)

## Files Modified

1. [`chrome_extension/src/lib/api.ts`](src/lib/api.ts) - Added `updateItemMetadata()` method
2. [`chrome_extension/src/content/content-script.ts`](src/content/content-script.ts) - Added `extractPageMetadata()` function
3. [`chrome_extension/src/background/service-worker.ts`](src/background/service-worker.ts) - Modified `processGenericItem()` to check and update metadata

## Next Steps

After reloading the extension in Chrome:
1. Test with various URL types (news articles, blogs, YouTube videos)
2. Verify metadata extraction works correctly
3. Check that items are properly updated in the database
4. Monitor console logs for any errors or issues