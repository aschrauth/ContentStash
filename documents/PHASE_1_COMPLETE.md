# Phase 1: Backend Updates - COMPLETE ✅

## Summary
Successfully implemented backend support for local extraction fallback system. The backend can now detect when content extraction is blocked and mark items for local processing by the Chrome Extension.

## Changes Made

### 1. Model Updates (`backend/app/models/saved_item.py`)
- ✅ Added `pending_local_extraction` to `processing_status` enum
- ✅ Added `local` to `extraction_type` enum (alongside `fast` and `complete`)

### 2. Exception Handling (`backend/app/services/exceptions.py`)
- ✅ Created new `ExtractionBlockError` exception
- Used to signal when server-side extraction is blocked (YouTube bot detection, 403 errors, etc.)

### 3. Extraction Service Updates (`backend/app/services/extraction.py`)
- ✅ Import `ExtractionBlockError`
- ✅ Raise `ExtractionBlockError` when YouTube extraction fails completely
- ✅ Raise `ExtractionBlockError` for 403/401 HTTP errors (access blocked)
- ✅ Better differentiation between "blocked" vs "empty content" states

### 4. Background Processing Updates (`backend/app/services/background.py`)
- ✅ Import `ExtractionBlockError`
- ✅ **Force Local Mode**: If `extraction_type == "local"`, skip server extraction entirely and set status to `pending_local_extraction`
- ✅ **Auto Fallback**: Catch `ExtractionBlockError` during extraction and set status to `pending_local_extraction` with error message
- ✅ Items marked for local extraction wait for Chrome Extension to process them

### 5. API Endpoints (`backend/app/routers/items.py`)
- ✅ Added `Field` import from pydantic
- ✅ **New Endpoint**: `GET /items/pending-local`
  - Returns list of items with status `pending_local_extraction`
  - Used by Chrome Extension to poll for work
  - Filters by authenticated user
- ✅ **New Endpoint**: `PATCH /items/{item_id}/content`
  - Accepts extracted content from Chrome Extension
  - Updates `archived_text` field
  - Resets status to `pending` to trigger post-processing (embeddings, AI tags)
  - Validates ownership

## How It Works

### Workflow 1: User Forces Local Extraction
1. User saves URL with `extraction_type: "local"` (from Chrome Extension or Web UI)
2. Backend skips server extraction
3. Item immediately marked as `pending_local_extraction`
4. Chrome Extension polls and processes it

### Workflow 2: Auto Fallback on Block
1. User saves URL with `extraction_type: "fast"` or `"complete"`
2. Backend attempts server-side extraction
3. If blocked (YouTube 403, paywall, etc.), `ExtractionBlockError` is raised
4. Item marked as `pending_local_extraction` with error message
5. Chrome Extension polls and processes it

### Workflow 3: Extension Uploads Content
1. Chrome Extension calls `GET /items/pending-local`
2. For each item, extension opens URL in background tab
3. Extension extracts content using browser context (bypasses blocks)
4. Extension calls `PATCH /items/{id}/content` with extracted text
5. Backend receives content, generates embeddings and AI tags
6. Item marked as `processed`

## Testing Recommendations

### Test 1: Force Local Extraction
```bash
# Create item with local extraction type
curl -X POST http://localhost:8000/api/items \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "title": "Test Video",
    "extraction_type": "local"
  }'

# Check if it's pending local extraction
curl http://localhost:8000/api/items/pending-local \
  -H "Authorization: Bearer YOUR_JWT"
```

### Test 2: Auto Fallback (YouTube Block)
```bash
# Create item with fast extraction (will fail on YouTube in production)
curl -X POST http://localhost:8000/api/items \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "title": "Test Video",
    "extraction_type": "fast"
  }'

# Wait a few seconds, then check pending local
curl http://localhost:8000/api/items/pending-local \
  -H "Authorization: Bearer YOUR_JWT"
```

### Test 3: Upload Content
```bash
# Upload extracted content
curl -X PATCH http://localhost:8000/api/items/ITEM_ID/content \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# Test Content\n\nThis is extracted content from the browser.",
    "extraction_source": "test_script"
  }'
```

## Next Steps
- **Phase 2**: Build Chrome Extension (Quick Capture UI)
- **Phase 3**: Implement Local Extraction Agent in Extension
- **Phase 4**: Create iOS Shortcut documentation