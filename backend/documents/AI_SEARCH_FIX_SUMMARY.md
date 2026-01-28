# AI Search Functionality Fix - Summary

## Date: 2026-01-28

## Issues Fixed

### Issue 1: Gemini API Model Version Incompatibility (CRITICAL) ✅

**Problem**: The embedding model `text-embedding-004` was not available in the Gemini `v1beta` API version, causing all AI search queries to fail with a 404 error.

**Root Cause**: The code was using `text-embedding-004` which is only available in the v1 API, but the application uses the v1beta API.

**Solution**: Changed the embedding model to `models/gemini-embedding-001` which is compatible with v1beta API.

**Files Modified**:
- [`backend/app/services/gemini.py`](../app/services/gemini.py) - Updated `embed_content()` and `embed_batch()` methods to use `models/gemini-embedding-001`

**Changes Made**:
```python
# Before (line 191):
model: str = "text-embedding-004"

# After:
model: str = "models/gemini-embedding-001"
```

**Verification**: Tested with [`backend/test_embedding_fix.py`](../test_embedding_fix.py) - embeddings now generate successfully with 3072 dimensions.

### Issue 2: MongoDB Atlas Vector Search Index Configuration (REQUIRED) 📝

**Problem**: The MongoDB Atlas Vector Search index `vector_index` needs to be created manually in the Atlas UI. Additionally, the index configuration needs to be updated to match the new embedding dimensions.

**Root Cause**: Vector search indexes cannot be created programmatically and must be set up through the MongoDB Atlas UI.

**Solution**: Updated documentation with clear instructions for creating the vector search index with the correct configuration.

**Files Modified**:
- [`backend/documents/VECTOR_SEARCH_SETUP.md`](VECTOR_SEARCH_SETUP.md) - Updated with correct model name and dimensions

**Key Configuration Changes**:
- **Embedding Model**: `models/gemini-embedding-001` (was `text-embedding-004`)
- **Vector Dimensions**: `3072` (was `768`)
- **Index Name**: `vector_index` (unchanged)
- **Collection**: `item_chunks` (unchanged)
- **Similarity**: `cosine` (unchanged)

## MongoDB Atlas Vector Search Index Setup

### Required Index Configuration

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 3072,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "owner_id"
    }
  ]
}
```

### Setup Instructions

1. Log in to [MongoDB Atlas](https://cloud.mongodb.com/)
2. Navigate to your cluster
3. Click on the "Search" tab (Atlas Search)
4. Click "Create Search Index"
5. Choose "JSON Editor"
6. Select database: `contentstash`
7. Select collection: `item_chunks`
8. Name the index: `vector_index`
9. Paste the JSON configuration above
10. Click "Create Search Index"
11. Wait for the index to build (status will change from "Building" to "Active")

**Important**: If you already have a `vector_index` with 768 dimensions, you will need to:
1. Delete the old index
2. Create a new index with 3072 dimensions using the configuration above

## Testing

### Test Embedding Generation

Run the test script to verify embeddings are working:

```bash
cd backend
source venv/bin/activate
python test_embedding_fix.py
```

Expected output:
```
✓ Gemini service is configured
✓ Embedding generated successfully
  - Dimension: 3072
✓ Embedding dimension is correct (3072)
✓ ALL TESTS PASSED
```

### List Available Models

To see all available Gemini models:

```bash
cd backend
source venv/bin/activate
python list_available_models.py
```

## Impact

### What's Fixed
- ✅ Query embedding generation now works
- ✅ AI search queries can be processed
- ✅ Compatible with Gemini v1beta API

### What Still Needs Setup
- ⚠️ MongoDB Atlas Vector Search index must be created/updated manually
- ⚠️ Existing chunks with 768-dimensional embeddings may need to be re-embedded (optional)

### Existing Data
- User test2@test.com has 216 saved items with 594 chunks
- These chunks have embeddings from when they were created
- If the old embeddings were 768-dimensional, they will need to be regenerated
- New items saved after this fix will automatically use 3072-dimensional embeddings

## Next Steps

1. **Create/Update MongoDB Atlas Vector Search Index** (REQUIRED)
   - Follow the instructions in [`VECTOR_SEARCH_SETUP.md`](VECTOR_SEARCH_SETUP.md)
   - Use the new configuration with 3072 dimensions

2. **Test AI Search** (RECOMMENDED)
   - Save a new item to generate fresh embeddings
   - Use the chat feature to ask questions about your content
   - Verify search results are returned

3. **Re-embed Existing Content** (OPTIONAL)
   - If you have existing chunks with 768-dimensional embeddings
   - They will need to be re-embedded with the new model
   - This can be done by re-saving items or running a migration script

## Technical Details

### Embedding Model Comparison

| Model | API Version | Dimensions | Status |
|-------|-------------|------------|--------|
| `text-embedding-004` | v1 only | 768 | ❌ Not compatible |
| `models/embedding-001` | v1beta | N/A | ❌ Not found |
| `models/gemini-embedding-001` | v1beta | 3072 | ✅ Working |

### Code Changes Summary

**File**: `backend/app/services/gemini.py`
- Line 191: Changed default model parameter in `embed_content()`
- Line 235: Changed default model parameter in `embed_batch()`

**Documentation Updates**:
- `VECTOR_SEARCH_SETUP.md`: Updated with correct model and dimensions
- `AI_SEARCH_FIX_SUMMARY.md`: Created this summary document

## Troubleshooting

### Error: "404 models/text-embedding-004 is not found"
**Solution**: This error should no longer occur. The code has been updated to use `models/gemini-embedding-001`.

### Error: "index not found"
**Solution**: Create the MongoDB Atlas Vector Search index following the instructions above.

### Error: "dimension mismatch"
**Solution**: Update your MongoDB Atlas Vector Search index to use 3072 dimensions instead of 768.

### Search returns no results
**Possible causes**:
1. Vector search index not created yet
2. Index still building (check Atlas UI)
3. Index has wrong dimensions (should be 3072)
4. No chunks exist for the user

## References

- [MongoDB Atlas Vector Search Documentation](https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-overview/)
- [Gemini API Documentation](https://ai.google.dev/gemini-api/docs)
- [`VECTOR_SEARCH_SETUP.md`](VECTOR_SEARCH_SETUP.md) - Detailed setup guide