# Extraction Type Feature Implementation

## Overview
This feature allows users to select between "fast" and "complete" extraction modes when saving items, giving them control over the trade-off between speed and completeness.

## Implementation Summary

### Backend Changes

#### 1. Database Model (`backend/app/models/saved_item.py`)
- Added `extraction_type` field to `SavedItemBase`, `SavedItemUpdate`, and `SavedItem` models
- Field accepts values: "fast" (default) or "complete"
- Pattern validation ensures only valid values are accepted
- Backward compatible: defaults to "fast" for existing items

#### 2. Extraction Service (`backend/app/services/extraction.py`)
- Updated `extract_content()` and `extract_content_with_metadata()` to accept `extraction_type` parameter
- **Fast mode (default)**: Uses existing cascade logic (Readability → Playwright fallback)
- **Complete mode**: Skips Readability and goes directly to Playwright for full rendering
- **YouTube URLs**: Always use transcript extraction regardless of extraction_type
- Maintains all existing functionality and error handling

#### 3. API Endpoints (`backend/app/routers/items.py`)
- **POST `/api/v1/items`**: Accepts `extraction_type` in request body
- **PATCH `/api/v1/items/{item_id}`**: Allows updating `extraction_type`
  - When `extraction_type` is changed, automatically triggers reprocessing
  - Sets `processing_status` to "pending" and clears `processing_error`
  - Schedules background task to reprocess with new extraction type
- All GET endpoints return `extraction_type` field
- Backward compatible: defaults to "fast" if not provided

#### 4. Background Processing (`backend/app/services/background.py`)
- Updated `process_item_background()` to read and pass `extraction_type` to extraction functions
- Respects the item's `extraction_type` setting during processing and reprocessing

### Frontend Changes

#### 1. TypeScript Types (`frontend/lib/store.ts`)
- Added `extractionType?: 'fast' | 'complete'` to `SavedItem` interface
- Updated all API response mapping to include `extraction_type` field
- Updated `addItem()` and `updateItem()` to send `extraction_type` to backend

#### 2. Save Modal (`frontend/components/SaveModal.tsx`)
- Added extraction type selector with two options:
  - **Fast**: "Quick extraction, may miss images on some sites"
  - **Complete**: "Full extraction with images, slower (~5-10s)"
- Visual toggle buttons with icons (Zap for Fast, Clock for Complete)
- Only shown for URL tab (not for pasted content)
- Defaults to "fast" mode
- Sends selected `extraction_type` when creating new items

#### 3. Item Detail Page (`frontend/app/items/[id]/page.tsx`)
- Added "Extraction Type" panel in the sidebar
- Shows current extraction type
- Dropdown to change between Fast and Complete
- Automatically triggers reprocessing when changed
- Shows toast notification when extraction type is updated
- Only displayed for items with URLs

### Testing

#### Test Script (`backend/test_extraction_type.py`)
Created comprehensive test script that verifies:
1. Fast extraction works correctly
2. Complete extraction works correctly
3. YouTube URLs use transcript extraction regardless of type

**Test Results**: ✅ All tests passed successfully

### Key Features

1. **User Control**: Users can choose extraction speed vs. completeness
2. **Automatic Reprocessing**: Changing extraction type automatically reprocesses content
3. **Backward Compatible**: Existing items default to "fast" mode
4. **YouTube Handling**: YouTube URLs always use transcript extraction
5. **Visual Feedback**: Clear UI indicators and loading states
6. **Type Safety**: Full TypeScript support with proper types

### Usage

#### Creating a New Item with Extraction Type
```typescript
// Frontend
await addItem({
  title: "Article Title",
  url: "https://example.com/article",
  extractionType: "complete", // or "fast"
  // ... other fields
});
```

#### Updating Extraction Type
```typescript
// Frontend - automatically triggers reprocessing
await updateItem(itemId, {
  extractionType: "complete"
});
```

#### Backend API
```bash
# Create item with complete extraction
POST /api/v1/items
{
  "url": "https://example.com/article",
  "title": "Article Title",
  "extraction_type": "complete"
}

# Update extraction type (triggers reprocessing)
PATCH /api/v1/items/{item_id}
{
  "extraction_type": "fast"
}
```

### Performance Considerations

- **Fast mode**: ~1-3 seconds for most sites
- **Complete mode**: ~5-10 seconds (launches full browser)
- YouTube transcripts: ~2-4 seconds (regardless of mode)

### Future Enhancements

Potential improvements for future iterations:
1. Add extraction quality metrics/feedback
2. Allow users to set default extraction type in preferences
3. Add batch reprocessing with extraction type selection
4. Show extraction method used in item metadata
5. Add extraction time tracking and display

## Commit Information

**Branch**: testing
**Commit**: 351c5ed
**Files Changed**: 8 files, 222 insertions(+), 8 deletions(-)

### Modified Files:
- `backend/app/models/saved_item.py`
- `backend/app/routers/items.py`
- `backend/app/services/background.py`
- `backend/app/services/extraction.py`
- `frontend/app/items/[id]/page.tsx`
- `frontend/components/SaveModal.tsx`
- `frontend/lib/store.ts`

### New Files:
- `backend/test_extraction_type.py`

## Conclusion

The extraction type feature has been successfully implemented and tested. It provides users with granular control over content extraction while maintaining backward compatibility and the existing cascade logic for the default "fast" mode.