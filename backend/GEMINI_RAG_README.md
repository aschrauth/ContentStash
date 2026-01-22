# Gemini RAG System Documentation

## Table of Contents
1. [Overview](#overview)
2. [Setup Instructions](#setup-instructions)
3. [Features Documentation](#features-documentation)
4. [API Endpoints](#api-endpoints)
5. [Migration Guide](#migration-guide)
6. [Cost Optimization](#cost-optimization)
7. [Troubleshooting](#troubleshooting)
8. [Architecture Details](#architecture-details)
9. [Development](#development)
10. [Future Enhancements](#future-enhancements)

---

## Overview

The Gemini RAG (Retrieval-Augmented Generation) system is an intelligent content search and question-answering system built into ContentStash. It enables users to semantically search their saved content and ask questions that are answered using AI with proper citations.

### Key Features

- **Automatic Chunking & Embedding**: Content is automatically split into chunks and embedded when saved
- **Auto-Categorization**: AI-generated tags, topics, and summaries for saved items
- **Semantic Search**: Find content by meaning, not just keywords
- **Chat/Ask with Citations**: Ask questions and get answers with quoted sources
- **Vector Search**: MongoDB Atlas Vector Search for fast, accurate retrieval
- **Cost-Optimized**: Uses Gemini Flash-Lite models for efficient processing

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     User Saves Content                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Background Processing Pipeline                  │
│  1. Extract content → archived_text                          │
│  2. Chunk text (500 tokens, 75 overlap)                      │
│  3. Generate embeddings (text-embedding-004)                 │
│  4. Store chunks in item_chunks collection                   │
│  5. Generate auto-categorization (Flash-Lite)                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  MongoDB Collections                         │
│  • saved_items: Original content + metadata                  │
│  • item_chunks: Text chunks + 768-dim embeddings             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              User Searches or Asks Question                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    RAG Query Pipeline                        │
│  1. Embed query (text-embedding-004)                         │
│  2. Vector search in item_chunks (MongoDB Atlas)             │
│  3. Retrieve top K relevant chunks                           │
│  4. Generate answer with citations (Flash-Lite)              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Answer with Cited Sources                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Setup Instructions

### Prerequisites

1. **MongoDB Atlas Cluster** (M10+ recommended for production)
   - Free tier (M0) does NOT support vector search
   - M10 or higher required for vector search functionality

2. **Gemini API Key**
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Free tier available with generous limits

3. **Python 3.8+** with required dependencies

### Step 1: Configure Environment Variables

Add to your `backend/.env` file:

```bash
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# MongoDB Configuration (should already exist)
MONGODB_URI=your_mongodb_atlas_connection_string
```

### Step 2: Install Dependencies

The required dependencies should already be in `requirements.txt`:

```bash
cd backend
pip install -r requirements.txt
```

Key dependencies:
- `google-genai`: Gemini API client (new package, replaces deprecated `google-generativeai`)
- `motor`: Async MongoDB driver
- `pymongo`: MongoDB driver

### Step 3: Set Up MongoDB Atlas Vector Search Index

**This is a critical step!** The system will not work without the vector search index.

Follow the detailed instructions in [`VECTOR_SEARCH_SETUP.md`](VECTOR_SEARCH_SETUP.md) to:

1. Create a vector search index named `vector_index`
2. Configure it on the `item_chunks` collection
3. Set up 768-dimensional embeddings with cosine similarity
4. Add owner_id filter for security

**Quick Summary:**

In MongoDB Atlas UI → Search tab → Create Search Index:

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

### Step 4: Verify Setup

Test that everything is configured correctly:

```bash
cd backend
python test_vector_search.py
```

This will:
- Check Gemini API connectivity
- Verify MongoDB connection
- Test embedding generation
- Confirm vector search index is working

---

## Features Documentation

### 1. Automatic Chunking & Embedding

**How It Works:**

When a user saves content, the system automatically:

1. **Extracts Content**: Fetches and extracts text from the URL
2. **Chunks Text**: Splits into ~500 token chunks with 75 token overlap
3. **Generates Embeddings**: Creates 768-dimensional vectors using `text-embedding-004`
4. **Stores Chunks**: Saves to `item_chunks` collection with embeddings

**When It Happens:**

- Automatically triggered when saving new content
- Runs in background (non-blocking)
- Processing status tracked in `saved_items.processing_status`

**Technical Details:**

- **Chunk Size**: 500 tokens (approximate, using whitespace tokenization)
- **Overlap**: 75 tokens between consecutive chunks
- **Embedding Model**: `text-embedding-004` (768 dimensions)
- **Storage**: MongoDB `item_chunks` collection

**Code Reference:**

- Chunking: [`app/services/chunking.py`](app/services/chunking.py)
- Embedding: [`app/services/gemini.py`](app/services/gemini.py)
- Background processing: [`app/services/background.py`](app/services/background.py)

### 2. Auto-Categorization

**How It Works:**

The system uses Gemini 2.0 Flash-Lite to automatically generate:

- **Suggested Tags**: 3-5 relevant tags for the content
- **Topic**: Main topic or category
- **Summary**: 2-3 sentence summary

**When It Happens:**

- Automatically during background processing
- Uses first 1500 characters for cost optimization
- Results stored in `saved_items` document

**Generated Fields:**

```javascript
{
  "suggested_tags": ["tag1", "tag2", "tag3"],
  "suggested_topic": "Main Topic",
  "ai_summary": "2-3 sentence summary of the content..."
}
```

**Code Reference:**

- Implementation: [`app/services/background.py:generate_auto_categorization()`](app/services/background.py)

### 3. Semantic Search

**How It Works:**

Semantic search finds content by meaning, not just keywords:

1. User enters search query
2. Query is embedded using `text-embedding-004`
3. MongoDB Atlas Vector Search finds similar chunks
4. Results ranked by cosine similarity score

**Key Features:**

- Finds conceptually similar content
- Works across different phrasings
- Filters by user ownership (security)
- Returns top K most relevant chunks

**Example:**

Query: "machine learning tutorials"
- Finds: "deep learning guides", "neural network courses", "AI training resources"
- Even if exact words don't match!

**Code Reference:**

- Implementation: [`app/services/rag.py:vector_search()`](app/services/rag.py)
- API endpoint: [`app/routers/chat.py:semantic_search()`](app/routers/chat.py)

### 4. Chat/Ask with Citations

**How It Works:**

Ask questions and get AI-generated answers with proper citations:

1. **Retrieval**: Vector search finds relevant chunks (K=8)
2. **Context Building**: Chunks formatted as evidence
3. **Generation**: Gemini 2.0 Flash-Lite generates answer
4. **Citation Extraction**: Identifies which chunks were used
5. **Response**: Answer with quoted excerpts and source links

**Citation Format:**

```javascript
{
  "answer": "Machine learning is... [Chunk 1] According to the article...",
  "citations": [
    {
      "id": "item_id",
      "title": "Source Title",
      "excerpt": "Quoted text from the source..."
    }
  ],
  "chunks_used": 8
}
```

**Key Features:**

- **Factual Accuracy**: Only uses provided evidence
- **Transparency**: Shows which sources were used
- **Quoted Excerpts**: Includes relevant quotes
- **No Hallucination**: Says "I don't have enough information" when uncertain

**Code Reference:**

- Implementation: [`app/services/rag.py:generate_answer()`](app/services/rag.py)
- API endpoint: [`app/routers/chat.py:ask_question()`](app/routers/chat.py)

### 5. Vector Search

**Technical Details:**

- **Index Type**: MongoDB Atlas Vector Search
- **Similarity Metric**: Cosine similarity
- **Dimensions**: 768 (matches text-embedding-004)
- **Candidates**: K * 10 (for good recall/performance balance)
- **Security**: Filtered by `owner_id`

**Performance:**

- Fast: Sub-second queries on M10+ clusters
- Scalable: Handles thousands of chunks per user
- Accurate: High recall with cosine similarity

**Code Reference:**

- Implementation: [`app/services/rag.py:vector_search()`](app/services/rag.py)

---

## API Endpoints

### GET `/api/v1/chat/search`

Perform semantic search on saved items.

**Query Parameters:**
- `q` (required): Search query text (1-500 chars)
- `k` (optional): Number of results (default: 8, max: 20)

**Request Example:**

```bash
curl -X GET "http://localhost:8000/api/v1/chat/search?q=machine%20learning&k=5" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Response Example:**

```json
{
  "query": "machine learning",
  "results": [
    {
      "chunk_id": "507f1f77bcf86cd799439011",
      "item_id": "507f191e810c19729de860ea",
      "text": "Machine learning is a subset of artificial intelligence...",
      "score": 0.89,
      "chunk_index": 0
    }
  ],
  "total_results": 5
}
```

**Response Fields:**
- `query`: The search query
- `results`: Array of matching chunks
  - `chunk_id`: Unique chunk identifier
  - `item_id`: Parent item ID
  - `text`: Chunk text content
  - `score`: Similarity score (0-1, higher is better)
  - `chunk_index`: Position in original text
- `total_results`: Number of results returned

### POST `/api/v1/chat/ask`

Ask a question and get an AI-generated answer with citations.

**Request Body:**

```json
{
  "question": "What is machine learning?"
}
```

**Request Example:**

```bash
curl -X POST "http://localhost:8000/api/v1/chat/ask" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is machine learning?"}'
```

**Response Example:**

```json
{
  "answer": "Machine learning is a subset of artificial intelligence that enables computers to learn from data without being explicitly programmed. [Chunk 1] According to the article, it involves algorithms that improve automatically through experience.",
  "citations": [
    {
      "id": "507f191e810c19729de860ea",
      "title": "Introduction to Machine Learning",
      "excerpt": "Machine learning is a subset of artificial intelligence that enables computers to learn from data..."
    }
  ],
  "chunks_used": 8
}
```

**Response Fields:**
- `answer`: AI-generated answer with inline citations
- `citations`: Array of source citations
  - `id`: Item ID (can be used to link to full item)
  - `title`: Source title
  - `excerpt`: Quoted text from source (max 200 chars)
- `chunks_used`: Number of chunks used for context

**Error Responses:**

- `400 Bad Request`: Invalid question format
- `401 Unauthorized`: Missing or invalid JWT token
- `500 Internal Server Error`: Generation failed

---

## Migration Guide

If you have existing items in your database that were saved before the RAG system was implemented, you need to migrate them to add chunks and embeddings.

### Using the Migration Script

The migration script processes existing items to add chunking, embeddings, and auto-categorization.

**Basic Usage:**

```bash
cd backend

# Dry run to preview what will be processed
python migrate_existing_items.py --dry-run

# Process all items
python migrate_existing_items.py

# Process first 50 items only (for testing)
python migrate_existing_items.py --limit 50

# Process in smaller batches (default is 10)
python migrate_existing_items.py --batch-size 5

# Skip AI categorization (only chunk and embed)
python migrate_existing_items.py --skip-categorization
```

### What the Migration Does

For each item without chunks:

1. **Validates**: Checks if item has `archived_text`
2. **Chunks**: Splits text into 500-token chunks with 75-token overlap
3. **Embeds**: Generates 768-dimensional embeddings
4. **Stores**: Saves chunks to `item_chunks` collection
5. **Categorizes**: Generates tags, topic, and summary (unless skipped)
6. **Updates**: Marks item as processed

### Migration Best Practices

1. **Start with Dry Run**: Always run with `--dry-run` first to see what will be processed

2. **Test with Limit**: Process a small batch first to verify everything works
   ```bash
   python migrate_existing_items.py --limit 10
   ```

3. **Monitor Progress**: The script provides detailed progress updates
   ```
   Progress: 50/200 items (45 processed, 5 failed)
   ```

4. **Handle Rate Limits**: The script automatically retries with exponential backoff
   - Waits 2 seconds between batches
   - Retries failed requests up to 3 times
   - Waits 60 seconds if rate limit is hit

5. **Resume After Interruption**: The script only processes items without chunks, so you can safely re-run it

### Migration Output

The script provides detailed statistics:

```
============================================================
MIGRATION SUMMARY
============================================================
Total items found: 200
Successfully processed: 185
Skipped (no archived_text): 10
Skipped (already has chunks): 0
Failed: 5
Duration: 245.67 seconds
============================================================
```

### Troubleshooting Migration

**Issue**: "Gemini service not available"
- **Solution**: Ensure `GEMINI_API_KEY` is set in `.env`

**Issue**: Rate limit errors
- **Solution**: Use smaller `--batch-size` or wait between runs

**Issue**: Items skipped (no archived_text)
- **Solution**: These items need to be reprocessed to extract content first

**Code Reference:**

- Migration script: [`migrate_existing_items.py`](migrate_existing_items.py)

---

## Cost Optimization

The system is designed to minimize API costs while maintaining quality.

### Model Choices

**Embedding Model: `text-embedding-004`**
- Cost: Free tier available, then $0.00001 per 1K tokens
- Dimensions: 768 (good balance of quality and size)
- Speed: Fast batch processing

**Generation Model: `gemini-2.0-flash-lite-preview-02-05`**
- Cost: Significantly cheaper than full Gemini models
- Quality: Excellent for RAG tasks
- Speed: Very fast response times

### Token Limits and Chunking Strategy

**Chunking Parameters:**
- **Chunk Size**: 500 tokens
  - Large enough for context
  - Small enough for focused retrieval
- **Overlap**: 75 tokens
  - Prevents information loss at boundaries
  - Maintains context across chunks

**Context Limits:**
- **Search**: Top 8 chunks (K=8)
  - ~4000 tokens of context
  - Good balance of relevance and cost
- **Categorization**: First 1500 characters
  - Sufficient for topic identification
  - Reduces processing cost

**Truncation:**
- Chunks truncated to 500 chars in prompts
- Prevents excessive token usage
- Maintains essential information

### Rate Limit Handling

**Automatic Retry with Exponential Backoff:**
- 1st retry: Wait 1 second
- 2nd retry: Wait 2 seconds
- 3rd retry: Wait 4 seconds
- After 3 attempts: Raise error

**Batch Processing:**
- Embeddings generated in batches
- 2-second delay between batches in migration
- Prevents rate limit exhaustion

**Code Reference:**

- Retry logic: [`app/services/gemini.py:retry_with_exponential_backoff()`](app/services/gemini.py)

### Cost Estimates

**Per Item Processing:**
- Chunking: Free (local processing)
- Embedding: ~$0.0001 per item (varies by length)
- Categorization: ~$0.0001 per item
- **Total**: ~$0.0002 per item

**Per Query:**
- Query embedding: ~$0.00001
- Answer generation: ~$0.0001
- **Total**: ~$0.00011 per query

**Example Costs:**
- 1,000 items: ~$0.20
- 10,000 queries: ~$1.10

---

## Troubleshooting

### Common Issues

#### 1. "Gemini service not available"

**Symptoms:**
- Error message: "Gemini service not available"
- No embeddings generated
- Auto-categorization skipped

**Causes:**
- `GEMINI_API_KEY` not set in environment
- Invalid API key
- API key not configured in `.env`

**Solutions:**
1. Check `.env` file has `GEMINI_API_KEY=your_key_here`
2. Verify API key is valid at [Google AI Studio](https://makersuite.google.com/app/apikey)
3. Restart the backend server after adding the key
4. Check logs for specific error messages

#### 2. "index not found" or "no such index"

**Symptoms:**
- Vector search returns empty results
- Error in logs: "index not found"
- Search endpoint returns 500 error

**Causes:**
- Vector search index not created in MongoDB Atlas
- Index created with wrong name
- Index not on correct collection

**Solutions:**
1. Follow [`VECTOR_SEARCH_SETUP.md`](VECTOR_SEARCH_SETUP.md) to create index
2. Verify index name is exactly `vector_index`
3. Confirm index is on `item_chunks` collection
4. Wait for index to finish building (check Atlas UI)

#### 3. "namespace not found"

**Symptoms:**
- Error: "namespace not found"
- No search results
- Empty chunks collection

**Causes:**
- No chunks have been created yet
- `item_chunks` collection doesn't exist
- No items have been processed

**Solutions:**
1. Save some content items to trigger chunk creation
2. Run migration script for existing items
3. Check `processing_status` field in `saved_items`
4. Verify chunks exist: `db.item_chunks.countDocuments({})`

#### 4. Rate Limit Errors

**Symptoms:**
- Error: "Rate limit exceeded"
- `GeminiRateLimitError` in logs
- Requests failing intermittently

**Causes:**
- Too many requests in short time
- Free tier limits exceeded
- Batch processing too aggressive

**Solutions:**
1. Wait 60 seconds and retry
2. Use smaller batch sizes in migration
3. Upgrade to paid Gemini API tier
4. The system automatically retries with backoff

#### 5. Empty Search Results

**Symptoms:**
- Search returns no results
- `total_results: 0`
- User has saved items

**Possible Causes:**
1. Items not processed yet (check `processing_status`)
2. No chunks created (check `item_chunks` collection)
3. Vector search index not active
4. Query embedding failed

**Debug Steps:**
1. Check item processing status:
   ```javascript
   db.saved_items.find({owner_id: ObjectId("user_id")}, {processing_status: 1})
   ```

2. Check chunks exist:
   ```javascript
   db.item_chunks.countDocuments({owner_id: "user_id"})
   ```

3. Verify index status in Atlas UI (should be "Active")

4. Check backend logs for embedding errors

5. Test with `test_vector_search.py`

#### 6. Poor Search Quality

**Symptoms:**
- Irrelevant results
- Low similarity scores
- Expected content not found

**Possible Causes:**
1. Query too short or vague
2. Content not well-chunked
3. Embedding model mismatch

**Solutions:**
1. Use more specific queries (3+ words)
2. Increase K parameter for more results
3. Check chunk quality in database
4. Verify embedding dimensions (should be 768)

### Getting Help

If you encounter issues not covered here:

1. **Check Logs**: Backend logs provide detailed error messages
   ```bash
   # View logs in terminal where server is running
   ```

2. **Test Components**: Use test scripts to isolate issues
   ```bash
   python test_vector_search.py
   python test_auto_categorization.py
   ```

3. **Verify Configuration**:
   - MongoDB connection string
   - Gemini API key
   - Vector search index
   - Environment variables

4. **Review Documentation**:
   - [`VECTOR_SEARCH_SETUP.md`](VECTOR_SEARCH_SETUP.md)
   - [MongoDB Atlas Vector Search Docs](https://www.mongodb.com/docs/atlas/atlas-vector-search/)
   - [Gemini API Docs](https://ai.google.dev/docs)

---

## Architecture Details

### Data Flow Diagrams

#### Content Ingestion Flow

```
User Saves URL
     │
     ▼
POST /api/v1/items
     │
     ├─► Create SavedItem (status: "pending")
     │
     └─► Trigger Background Task
              │
              ├─► Fetch Metadata
              │
              ├─► Extract Content → archived_text
              │
              ├─► Chunk Text (500 tokens, 75 overlap)
              │
              ├─► Generate Embeddings (batch)
              │        │
              │        └─► Gemini text-embedding-004
              │
              ├─► Store Chunks in item_chunks
              │
              ├─► Generate Auto-Categorization
              │        │
              │        └─► Gemini Flash-Lite
              │
              └─► Update SavedItem (status: "processed")
```

#### Query Flow

```
User Asks Question
     │
     ▼
POST /api/v1/chat/ask
     │
     ├─► Embed Query
     │        │
     │        └─► Gemini text-embedding-004
     │
     ├─► Vector Search
     │        │
     │        ├─► MongoDB Atlas $vectorSearch
     │        │
     │        └─► Filter by owner_id
     │
     ├─► Retrieve Top K Chunks (K=8)
     │
     ├─► Build Context from Chunks
     │
     ├─► Generate Answer
     │        │
     │        └─► Gemini Flash-Lite with prompt
     │
     ├─► Parse Citations
     │
     └─► Return Answer + Citations
```

### Component Descriptions

#### 1. Chunking Service (`app/services/chunking.py`)

**Purpose**: Split long text into manageable chunks

**Key Functions:**
- `chunk_text()`: Main chunking function
- `estimate_token_count()`: Approximate token counting

**Algorithm:**
- Whitespace-based tokenization
- Sliding window with overlap
- Configurable chunk size and overlap

#### 2. Gemini Service (`app/services/gemini.py`)

**Purpose**: Interface with Google Gemini API

**Key Features:**
- Singleton pattern for efficiency
- Automatic retry with exponential backoff
- Batch embedding support
- Error handling and logging

**Key Functions:**
- `generate_content()`: Text generation
- `embed_content()`: Single text embedding
- `embed_batch()`: Batch embedding
- `is_available()`: Check if configured

#### 3. RAG Service (`app/services/rag.py`)

**Purpose**: Retrieval-Augmented Generation logic

**Key Functions:**
- `vector_search()`: Semantic search using embeddings
- `generate_answer()`: Generate answer with citations
- `_build_citation_prompt()`: Construct RAG prompt
- `_parse_answer_with_citations()`: Extract citations

**Prompt Engineering:**
- Enforces evidence-only answers
- Requires citations with quotes
- Prevents hallucination
- Maintains factual accuracy

#### 4. Background Service (`app/services/background.py`)

**Purpose**: Asynchronous item processing

**Key Functions:**
- `process_item_background()`: Main processing pipeline
- `generate_auto_categorization()`: AI categorization

**Processing Steps:**
1. Fetch metadata
2. Extract content
3. Chunk and embed
4. Generate categorization
5. Update database

#### 5. Chat Router (`app/routers/chat.py`)

**Purpose**: API endpoints for search and chat

**Endpoints:**
- `GET /search`: Semantic search
- `POST /ask`: Question answering
- `POST /threads`: Create chat thread
- `GET /threads`: List threads
- `GET /threads/{id}`: Get thread
- `POST /threads/{id}/messages`: Add message
- `DELETE /threads/{id}`: Delete thread

### Database Schema

#### `item_chunks` Collection

```javascript
{
  _id: ObjectId("..."),
  item_id: "507f191e810c19729de860ea",  // Reference to saved_items
  owner_id: "507f1f77bcf86cd799439011",  // User ID for filtering
  chunk_index: 0,                         // Position in original text
  text: "Chunk content here...",          // ~500 tokens
  embedding: [0.123, -0.456, ...],        // 768-dimensional vector
  created_at: ISODate("2024-01-15T10:30:00Z")
}
```

**Indexes:**
- Vector search index on `embedding` (768 dimensions, cosine)
- Filter index on `owner_id`
- Compound index on `item_id` + `chunk_index`

#### `saved_items` Collection (RAG-related fields)

```javascript
{
  _id: ObjectId("..."),
  owner_id: ObjectId("..."),
  url: "https://example.com/article",
  title: "Article Title",
  
  // Content
  archived_text: "Full extracted text...",
  
  // Processing
  processing_status: "processed",  // "pending" | "processed" | "failed"
  processing_error: null,
  
  // Auto-categorization
  suggested_tags: ["tag1", "tag2", "tag3"],
  suggested_topic: "Main Topic",
  ai_summary: "2-3 sentence summary...",
  
  // Timestamps
  created_at: ISODate("..."),
  updated_at: ISODate("...")
}
```

---

## Development

### Running Tests

**Test Vector Search:**
```bash
cd backend
python test_vector_search.py
```

Tests:
- Gemini API connectivity
- Embedding generation
- Vector search functionality
- MongoDB connection

**Test Auto-Categorization:**
```bash
cd backend
python test_auto_categorization.py
```

Tests:
- Categorization generation
- JSON parsing
- Tag/topic/summary extraction

**Test Chat Endpoints:**
```bash
cd backend
python test_chat_endpoints.py
```

Tests:
- Semantic search endpoint
- Ask endpoint
- Citation generation

### Debugging Tips

**Enable Debug Logging:**

```python
# In app/main.py or test scripts
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check Embedding Quality:**

```python
from app.services.gemini import gemini_service

# Test embedding
text = "Your test text here"
embedding = gemini_service.embed_content(text)
print(f"Embedding dimension: {len(embedding)}")
print(f"First 5 values: {embedding[:5]}")
```

**Inspect Chunks:**

```python
from app.database import get_database
import asyncio

async def inspect_chunks():
    db = get_database()
    chunks = await db.item_chunks.find({"item_id": "your_item_id"}).to_list(length=None)
    for chunk in chunks:
        print(f"Chunk {chunk['chunk_index']}: {chunk['text'][:100]}...")

asyncio.run(inspect_chunks())
```

**Test Vector Search Directly:**

```python
from app.services.rag import vector_search
import asyncio

async def test_search():
    results = await vector_search("your query", "your_user_id", k=5)
    for r in results:
        print(f"Score: {r['score']:.3f} - {r['text'][:100]}...")

asyncio.run(test_search())
```

### Adding New Features

**To add a new embedding model:**

1. Update `app/services/gemini.py`:
   ```python
   def embed_content(self, text: str, model: str = "new-model-name"):
       # Update model parameter
   ```

2. Update chunk dimensions if needed
3. Recreate vector search index with new dimensions

**To modify chunking strategy:**

1. Edit `app/services/chunking.py`
2. Adjust `chunk_size` and `overlap` parameters
3. Re-process existing items with migration script

**To customize RAG prompts:**

1. Edit `app/services/rag.py:_build_citation_prompt()`
2. Modify prompt template
3. Test with various queries

---

## Future Enhancements

### Planned Features

1. **Multi-Modal Support**
   - Image embeddings for visual content
   - PDF text extraction improvements
   - Video transcript search

2. **Advanced Search Features**
   - Filters by date, tags, topics
   - Hybrid search (keyword + semantic)
   - Search within specific collections

3. **Improved Citations**
   - Direct links to specific chunks
   - Highlight relevant passages
   - Show context around citations

4. **Performance Optimizations**
   - Caching for frequent queries
   - Incremental embedding updates
   - Parallel processing for large batches

5. **User Experience**
   - Search suggestions/autocomplete
   - Related content recommendations
   - Search history and saved queries

### Known Limitations

1. **Language Support**
   - Currently optimized for English
   - Other languages may have reduced quality

2. **Content Types**
   - Best for text-heavy content
   - Limited support for code, tables, formulas

3. **Context Window**
   - Limited to top 8 chunks per query
   - Very long documents may lose context

4. **Real-time Updates**
   - Background processing has slight delay
   - Chunks not immediately searchable

5. **Cost Considerations**
   - Embedding costs scale with content volume

1. **Multi-Modal Support**
   - Image embeddings
   - PDF text extraction
