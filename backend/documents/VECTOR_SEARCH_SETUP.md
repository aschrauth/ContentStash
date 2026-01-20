# MongoDB Atlas Vector Search Setup Guide

This guide explains how to set up MongoDB Atlas Vector Search for the ContentStash RAG system.

## Overview

The ContentStash RAG system uses MongoDB Atlas Vector Search to perform semantic search over saved content chunks. This requires creating a vector search index in the MongoDB Atlas UI.

## Prerequisites

- MongoDB Atlas cluster (M10 or higher recommended for production)
- Access to MongoDB Atlas UI with appropriate permissions
- Content chunks already created (save some items first)

## Index Configuration

### Index Name
`vector_index`

### Collection
`item_chunks` (in the `contentstash` database)

### Index Definition

Create a vector search index with the following JSON configuration:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 768,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "owner_id"
    }
  ]
}
```

## Step-by-Step Setup Instructions

### 1. Access MongoDB Atlas

1. Log in to [MongoDB Atlas](https://cloud.mongodb.com/)
2. Navigate to your cluster
3. Click on the "Search" tab (Atlas Search)

### 2. Create Search Index

1. Click "Create Search Index"
2. Choose "JSON Editor" (not Visual Editor)
3. Select your database: `contentstash`
4. Select your collection: `item_chunks`
5. Name your index: `vector_index`

### 3. Configure Index

Paste the following JSON configuration:

```json
{
  "fields": [
    {
      "type": "vector",
      "path": "embedding",
      "numDimensions": 768,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "owner_id"
    }
  ]
}
```

### 4. Create and Wait

1. Click "Create Search Index"
2. Wait for the index to build (this may take a few minutes)
3. Status will change from "Building" to "Active"

## Configuration Details

### Vector Field Configuration

- **Field**: `embedding`
- **Type**: `vector`
- **Dimensions**: `768` (matches Gemini text-embedding-004 output)
- **Similarity**: `cosine` (recommended for text embeddings)

### Filter Field Configuration

- **Field**: `owner_id`
- **Type**: `filter`
- **Purpose**: Enables security filtering to ensure users only search their own chunks

## Verification

### Check Index Status

1. In Atlas UI, go to Search tab
2. Verify `vector_index` shows status "Active"
3. Check that it's on the `item_chunks` collection

### Test Vector Search

Once the index is active, the `vector_search()` function in `backend/app/services/rag.py` will automatically use it.

Test by:
1. Saving some content items (to generate chunks)
2. Using the chat feature to ask questions
3. Check backend logs for vector search activity

## Troubleshooting

### Error: "index not found"

**Cause**: Vector search index hasn't been created yet

**Solution**: Follow the setup instructions above to create the index

### Error: "namespace not found"

**Cause**: No chunks exist in the `item_chunks` collection

**Solution**: Save some content items first. The system will automatically chunk and embed them.

### Index Building Takes Too Long

**Cause**: Large number of existing chunks

**Solution**: Wait for index to complete. Building time depends on:
- Number of documents
- Cluster tier (M10+ recommended)
- Current cluster load

### Search Returns No Results

**Possible causes**:
1. No chunks exist for the user (check `owner_id` filter)
2. Query embedding failed (check Gemini API key)
3. Index not fully built yet (check status in Atlas UI)

**Debug steps**:
1. Check backend logs for error messages
2. Verify Gemini API key is configured
3. Confirm chunks exist: `db.item_chunks.countDocuments({owner_id: "your_user_id"})`
4. Verify index is "Active" in Atlas UI

## Performance Considerations

### Cluster Tier

- **M0/M2/M5 (Free/Shared)**: Vector search not available
- **M10+**: Recommended for production use
- **M30+**: Better performance for large datasets

### Index Size

- Each 768-dimensional vector uses ~3KB of storage
- Plan storage accordingly based on expected number of chunks

### Query Performance

- `numCandidates`: Set to `k * 10` for good recall/performance balance
- Increase for better recall, decrease for faster queries
- Filter by `owner_id` reduces search space significantly

## Additional Resources

- [MongoDB Atlas Vector Search Documentation](https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-overview/)
- [Atlas Search Index Management](https://www.mongodb.com/docs/atlas/atlas-search/manage-indexes/)
- [Vector Search Best Practices](https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-best-practices/)

## Support

If you encounter issues:
1. Check backend logs for detailed error messages
2. Verify all configuration matches this guide
3. Ensure Gemini API key is properly configured
4. Confirm MongoDB Atlas cluster tier supports vector search (M10+)