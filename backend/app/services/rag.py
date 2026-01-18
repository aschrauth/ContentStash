"""
RAG (Retrieval-Augmented Generation) service for chat-based search.
"""
from openai import OpenAI
from typing import List, Dict, Optional
import logging
from app.config import settings
from app.database import get_database
from app.models.chat import Citation
from app.services.gemini import gemini_service, GeminiServiceError

logger = logging.getLogger(__name__)

async def vector_search(query: str, owner_id: str, k: int = 8) -> List[Dict]:
    """
    Perform semantic search using MongoDB Atlas Vector Search.
    
    This function:
    1. Embeds the query using Gemini text-embedding-004
    2. Executes MongoDB Atlas $vectorSearch aggregation on item_chunks
    3. Filters by owner_id for security
    4. Returns top K most similar chunks with scores and metadata
    
    Args:
        query: The search query text
        owner_id: User ID to filter chunks (security)
        k: Number of top results to return (default: 8)
        
    Returns:
        List of dicts with keys: chunk_id, item_id, text, score, chunk_index
        Returns empty list on errors or if no results found
        
    Raises:
        Does not raise exceptions - returns empty list on errors
    """
    try:
        # Check if Gemini service is available
        if not gemini_service.is_available():
            logger.warning("Gemini service not available for vector search")
            return []
        
        # Step 1: Embed the query
        logger.info(f"Embedding query for vector search: '{query[:50]}...'")
        try:
            query_embedding = gemini_service.embed_content(query)
            if not query_embedding:
                logger.error("Failed to generate query embedding - empty result")
                return []
            logger.info(f"Query embedded successfully (dimension: {len(query_embedding)})")
        except GeminiServiceError as e:
            logger.error(f"Gemini service error during embedding: {str(e)}")
            return []
        
        # Step 2: Execute MongoDB Atlas Vector Search
        db = get_database()
        
        # MongoDB Atlas Vector Search aggregation pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",  # Name of the Atlas Search index
                    "path": "embedding",       # Field containing embeddings
                    "queryVector": query_embedding,
                    "numCandidates": k * 10,   # Number of candidates to consider
                    "limit": k,                # Number of results to return
                    "filter": {
                        "owner_id": owner_id   # Security: only search user's chunks
                    }
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "item_id": 1,
                    "text": 1,
                    "chunk_index": 1,
                    "owner_id": 1,
                    "score": {"$meta": "vectorSearchScore"}
                }
            }
        ]
        
        logger.info(f"Executing vector search for owner_id={owner_id}, k={k}")
        
        try:
            cursor = db.item_chunks.aggregate(pipeline)
            chunks = await cursor.to_list(length=k)
            
            if not chunks:
                logger.info(f"No chunks found for query: '{query[:50]}...'")
                return []
            
            # Format results
            results = []
            for chunk in chunks:
                results.append({
                    "chunk_id": str(chunk["_id"]),
                    "item_id": chunk["item_id"],
                    "text": chunk["text"],
                    "score": chunk.get("score", 0.0),
                    "chunk_index": chunk["chunk_index"]
                })
            
            logger.info(f"Vector search returned {len(results)} chunks with scores: {[r['score'] for r in results]}")
            return results
            
        except Exception as e:
            error_msg = str(e)
            
            # Check for common errors
            if "index not found" in error_msg.lower() or "no such index" in error_msg.lower():
                logger.error(
                    "MongoDB Atlas Vector Search index 'vector_index' not found. "
                    "Please create the index in Atlas UI on the 'item_chunks' collection. "
                    "Index should be on 'embedding' field with 768 dimensions, cosine similarity."
                )
            elif "namespace not found" in error_msg.lower():
                logger.error(
                    "Collection 'item_chunks' not found. No chunks have been created yet. "
                    "Save some items first to generate chunks."
                )
            else:
                logger.error(f"MongoDB aggregation error during vector search: {error_msg}")
            
            return []
        
    except Exception as e:
        logger.error(f"Unexpected error in vector_search: {str(e)}")
        return []



async def search_items(user_id: str, query: str, limit: int = 5) -> List[Dict]:
    """
    Search saved items using MongoDB text search.
    
    Args:
        user_id: The user's ID to filter items
        query: The search query
        limit: Maximum number of results to return (default: 5)
        
    Returns:
        List of relevant saved items
    """
    try:
        db = get_database()
        
        # Use MongoDB text search with user filter
        cursor = db.saved_items.find(
            {
                "$text": {"$search": query},
                "owner_id": user_id
            },
            {
                "score": {"$meta": "textScore"}
            }
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)
        
        items = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for each item
        for item in items:
            item['id'] = str(item.pop('_id'))
        
        logger.info(f"Found {len(items)} items for query: {query}")
        return items
        
    except Exception as e:
        logger.error(f"Error searching items: {str(e)}")
        # Fallback to regex search if text search fails
        return await _fallback_search(user_id, query, limit)


async def _fallback_search(user_id: str, query: str, limit: int = 5) -> List[Dict]:
    """
    Fallback search using regex when text search is unavailable.
    
    Args:
        user_id: The user's ID to filter items
        query: The search query
        limit: Maximum number of results to return
        
    Returns:
        List of relevant saved items
    """
    try:
        db = get_database()
        
        # Create case-insensitive regex pattern
        pattern = {"$regex": query, "$options": "i"}
        
        # Search across multiple fields
        cursor = db.saved_items.find(
            {
                "owner_id": user_id,
                "$or": [
                    {"title": pattern},
                    {"description": pattern},
                    {"notes_markdown": pattern},
                    {"tags": pattern},
                    {"archived_text": pattern}
                ]
            }
        ).limit(limit)
        
        items = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for item in items:
            item['id'] = str(item.pop('_id'))
        
        logger.info(f"Fallback search found {len(items)} items for query: {query}")
        return items
        
    except Exception as e:
        logger.error(f"Error in fallback search: {str(e)}")
        return []


def generate_answer(query: str, chunks: List[Dict]) -> Dict[str, any]:
    """
    Generate an answer using Gemini 2.5 Flash-Lite based on retrieved chunks.
    
    This function:
    1. Takes the user's query and relevant chunks from vector search
    2. Constructs a prompt with evidence that enforces citation requirements
    3. Calls Gemini to generate an answer with citations
    4. Parses the response and extracts citations
    5. Returns structured result with answer, citations, and metadata
    
    Args:
        query: The user's question
        chunks: List of relevant chunks from vector_search()
        
    Returns:
        Dictionary with:
        - 'answer': Generated answer text
        - 'citations': List of Citation objects with quotes
        - 'chunks_used': Number of chunks used
    """
    # Check if Gemini service is available
    if not gemini_service.is_available():
        logger.warning("Gemini service not available for answer generation")
        return {
            'answer': "I'm sorry, but I cannot answer questions without the Gemini API configured. Please set the GEMINI_API_KEY environment variable.",
            'citations': [],
            'chunks_used': 0
        }
    
    # Check if we have any chunks
    if not chunks or len(chunks) == 0:
        return {
            'answer': "I couldn't find any relevant content to answer your question. Try saving some content first!",
            'citations': [],
            'chunks_used': 0
        }
    
    try:
        # Build evidence from chunks
        evidence = _build_evidence_from_chunks(chunks)
        
        # Build the prompt with strict citation requirements
        prompt = _build_citation_prompt(query, evidence, chunks)
        
        # Call Gemini API with Flash-Lite model for cost optimization
        logger.info(f"Generating answer with Gemini for query: '{query[:50]}...'")
        response_text = gemini_service.generate_content(
            prompt=prompt,
            model="gemini-2.0-flash-lite-preview-02-05"
        )
        
        if not response_text:
            logger.warning("Empty response from Gemini")
            return {
                'answer': "I received an empty response. Please try again.",
                'citations': [],
                'chunks_used': 0
            }
        
        # Parse response and extract citations
        answer, citations = _parse_answer_with_citations(response_text, chunks)
        
        logger.info(f"Generated answer with {len(citations)} citations from {len(chunks)} chunks")
        
        return {
            'answer': answer,
            'citations': citations,
            'chunks_used': len(chunks)
        }
        
    except GeminiServiceError as e:
        logger.error(f"Gemini service error generating answer: {str(e)}")
        return {
            'answer': f"I encountered an error while generating an answer: {str(e)}",
            'citations': [],
            'chunks_used': 0
        }
    except Exception as e:
        logger.error(f"Unexpected error generating answer: {str(e)}")
        return {
            'answer': f"I encountered an unexpected error: {str(e)}",
            'citations': [],
            'chunks_used': 0
        }


def _build_evidence_from_chunks(chunks: List[Dict]) -> str:
    """
    Build evidence string from chunks for the prompt.
    
    Args:
        chunks: List of chunk dicts from vector_search
        
    Returns:
        Formatted evidence string with numbered chunks
    """
    evidence_parts = []
    
    for i, chunk in enumerate(chunks, 1):
        text = chunk.get('text', '')
        # Truncate very long chunks to keep token usage low
        if len(text) > 500:
            text = text[:500] + "..."
        evidence_parts.append(f"[Chunk {i}] {text}")
    
    return "\n\n".join(evidence_parts)


def _build_citation_prompt(query: str, evidence: str, chunks: List[Dict]) -> str:
    """
    Build the RAG prompt with strict citation requirements.
    
    This prompt enforces:
    - Answer ONLY using provided evidence
    - Include citations with quoted excerpts
    - Say "I don't have enough information" if evidence is insufficient
    - Keep answers concise
    
    Args:
        query: User's question
        evidence: Formatted evidence from chunks
        chunks: Original chunk data (for context)
        
    Returns:
        Complete prompt string for Gemini
    """
    return f"""You are a helpful assistant that answers questions based ONLY on the provided evidence.

EVIDENCE:
{evidence}

QUESTION: {query}

INSTRUCTIONS:
- Answer using ONLY the evidence provided above
- Include citations like [Chunk 1] when referencing evidence
- Quote relevant excerpts to support your answer (use quotation marks)
- If the evidence doesn't contain enough information, say "I don't have enough information to answer that question."
- Keep your answer concise and factual
- Never make up information or use knowledge outside the provided evidence

ANSWER:"""


async def _get_item_metadata(chunk: Dict) -> Dict:
    """
    Fetch item metadata for a chunk.
    
    Args:
        chunk: Chunk dict with item_id
        
    Returns:
        Item metadata dict or empty dict if not found
    """
    try:
        db = get_database()
        from bson import ObjectId
        
        item_id = chunk.get('item_id')
        if not item_id:
            return {}
        
        # Handle both string and ObjectId
        if isinstance(item_id, str):
            if not ObjectId.is_valid(item_id):
                return {}
            item_id = ObjectId(item_id)
        
        item = await db.saved_items.find_one({"_id": item_id})
        
        if not item:
            return {}
        
        return {
            'id': str(item['_id']),
            'title': item.get('title', 'Untitled'),
            'url': item.get('url', '')
        }
        
    except Exception as e:
        logger.error(f"Error fetching item metadata: {str(e)}")
        return {}


def _parse_answer_with_citations(response_text: str, chunks: List[Dict]) -> tuple:
    """
    Parse Gemini response to extract answer and generate citations.
    
    This function:
    1. Extracts the answer text
    2. Identifies which chunks were cited (e.g., [Chunk 1])
    3. Creates Citation objects with quoted excerpts
    
    Args:
        response_text: Raw response from Gemini
        chunks: Original chunks used for evidence
        
    Returns:
        Tuple of (answer_text, list_of_citations)
    """
    import re
    from bson import ObjectId
    
    # Extract answer (everything is the answer)
    answer = response_text.strip()
    
    # Find all chunk citations in the answer (e.g., [Chunk 1], [Chunk 2])
    citation_pattern = r'\[Chunk (\d+)\]'
    cited_chunk_numbers = set(int(match) for match in re.findall(citation_pattern, answer))
    
    # Generate citations for cited chunks
    citations = []
    seen_items = set()  # Track items to avoid duplicate citations
    
    for chunk_num in sorted(cited_chunk_numbers):
        # Chunk numbers are 1-indexed
        chunk_idx = chunk_num - 1
        
        if chunk_idx < 0 or chunk_idx >= len(chunks):
            continue
        
        chunk = chunks[chunk_idx]
        item_id = chunk.get('item_id')
        
        # Skip if we already have a citation for this item
        if item_id in seen_items:
            continue
        seen_items.add(item_id)
        
        # Create excerpt from chunk text (first 200 chars)
        text = chunk.get('text', '')
        excerpt = text[:200]
        if len(text) > 200:
            excerpt += "..."
        
        # Try to get item title (synchronously for now - we'll need to fetch async later)
        # For now, use a placeholder title
        title = f"Source {chunk_num}"
        
        citation = Citation(
            id=str(item_id) if item_id else f"chunk_{chunk_num}",
            title=title,
            excerpt=excerpt or "No preview available"
        )
        citations.append(citation)
    
    return answer, citations


def _build_context(items: List[Dict]) -> str:
    """Build context string from relevant items."""
    context_parts = []
    
    for i, item in enumerate(items, 1):
        title = item.get('title', 'Untitled')
        description = item.get('description', '')
        notes = item.get('notes_markdown', '')
        archived_text = item.get('archived_text', '')
        
        # Combine available content
        content_parts = []
        if description:
            content_parts.append(f"Description: {description}")
        if notes:
            content_parts.append(f"Notes: {notes}")
        if archived_text:
            # Truncate archived text if too long
            truncated_text = archived_text[:1000] if len(archived_text) > 1000 else archived_text
            content_parts.append(f"Content: {truncated_text}")
        
        content = "\n".join(content_parts)
        
        context_parts.append(f"[Item {i}: {title}]\n{content}\n")
    
    return "\n---\n".join(context_parts)


def _build_rag_prompt(query: str, context: str) -> str:
    """Build the RAG prompt for OpenAI."""
    return f"""Based on the following saved items, please answer this question:

Question: {query}

Context from saved items:
{context}

Please provide a clear, concise answer based ONLY on the information in the context above. If the context doesn't contain enough information to answer the question, please say so. Reference which items you used in your answer."""


def _generate_citations(items: List[Dict]) -> List[Citation]:
    """Generate citation objects from items."""
    citations = []
    
    for item in items:
        # Create excerpt from description or notes
        excerpt = ""
        if item.get('description'):
            excerpt = item['description'][:200]
        elif item.get('notes_markdown'):
            excerpt = item['notes_markdown'][:200]
        elif item.get('archived_text'):
            excerpt = item['archived_text'][:200]
        
        # Add ellipsis if truncated
        if len(excerpt) == 200:
            excerpt += "..."
        
        citation = Citation(
            id=item['id'],
            title=item.get('title', 'Untitled'),
            excerpt=excerpt or "No preview available"
        )
        citations.append(citation)
    
    return citations