"""
RAG (Retrieval-Augmented Generation) service for chat-based search.
"""
from typing import List, Dict, Optional
import logging
from app.config import settings
from app.database import get_database
from app.models.chat import Citation
from app.services.gemini import (
    GEMINI_MODEL_TEXT_REASONING,
    gemini_service,
    GeminiServiceError,
)

logger = logging.getLogger(__name__)

async def vector_search(query: str, owner_id: str, k: int = 8, max_chunks_per_item: int = 2) -> List[Dict]:
    """
    Perform semantic search using MongoDB Atlas Vector Search with diversity.
    
    This function:
    1. Embeds the query using Gemini models/gemini-embedding-001
    2. Executes MongoDB Atlas $vectorSearch aggregation on item_chunks
    3. Filters by owner_id for security
    4. Applies diversity filtering to ensure multiple unique articles
    5. Returns top K most similar chunks with scores and metadata
    
    Args:
        query: The search query text
        owner_id: User ID to filter chunks (security)
        k: Number of top results to return (default: 8)
        max_chunks_per_item: Maximum chunks per article to ensure diversity (default: 2)
        
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
        
        # Retrieve more chunks initially to ensure diversity
        # We'll filter down to k chunks with diversity constraints
        retrieval_limit = k * 5  # Get 5x more chunks for diversity filtering (increased from 3x)
        
        # MongoDB Atlas Vector Search aggregation pipeline.
        # We filter by owner_id in vectorSearch, then join with saved_items
        # to ensure each chunk still has a valid parent item.
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",  # Name of the Atlas Search index
                    "path": "embedding",       # Field containing embeddings
                    "queryVector": query_embedding,
                    "numCandidates": retrieval_limit * 10,   # Number of candidates to consider
                    "limit": retrieval_limit,                 # Get more candidates for diversity
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
            },
            {
                # Join with saved_items to verify parent item exists.
                "$lookup": {
                    "from": "saved_items",
                    "let": {"item_id_str": "$item_id"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$eq": [{"$toString": "$_id"}, "$$item_id_str"]
                                }
                            }
                        },
                    ],
                    "as": "item_info"
                }
            },
            {
                # Filter out orphaned chunks where parent item does not exist.
                "$match": {
                    "item_info": {"$ne": []}  # Item must exist
                }
            },
            {
                # Remove the joined item_info field from results
                "$project": {
                    "item_info": 0
                }
            },
            {
                # Limit to retrieval_limit after filtering
                "$limit": retrieval_limit
            }
        ]
        
        logger.info(f"Executing vector search for owner_id={owner_id}, k={k}, retrieval_limit={retrieval_limit}")
        
        try:
            cursor = db.item_chunks.aggregate(pipeline)
            chunks = await cursor.to_list(length=retrieval_limit)
            
            if not chunks:
                logger.info(f"No chunks found for query: '{query[:50]}...'")
                return []
            
            # Format results
            all_results = []
            for chunk in chunks:
                all_results.append({
                    "chunk_id": str(chunk["_id"]),
                    "item_id": chunk["item_id"],
                    "text": chunk["text"],
                    "score": chunk.get("score", 0.0),
                    "chunk_index": chunk["chunk_index"]
                })
            
            # Apply diversity filtering with Round-Robin approach
            # This ensures multi-article diversity while allowing long articles 
            # to provide more context if relevant.
            diverse_results = _apply_diversity_filter(all_results, k)
            
            return diverse_results
            
        except Exception as e:
            error_msg = str(e)
            
            # Check for common errors
            if "index not found" in error_msg.lower() or "no such index" in error_msg.lower():
                logger.error(
                    "MongoDB Atlas Vector Search index 'vector_index' not found. "
                    "Please create the index in Atlas UI on the 'item_chunks' collection. "
                    "Index should be on 'embedding' field with 3072 dimensions, cosine similarity."
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


def _apply_diversity_filter(chunks: List[Dict], k: int) -> List[Dict]:
    """
    Apply diversity filtering using a Round-Robin approach.
    
    This ensures that we pick the top chunk from every unique article first,
    then the second best chunk from each, and so on, until we reach k chunks.
    This guarantees variety while allowing long articles to contribute more
    if they are highly relevant.
    
    Args:
        chunks: List of result chunks sorted by score (descending)
        k: Target number of chunks to return
        
    Returns:
        List of up to k diverse chunks
    """
    if not chunks:
        return []
    
    # Group chunks by item_id, maintaining their relative order (sorted by score)
    item_chunks_map = {}
    for chunk in chunks:
        item_id = chunk['item_id']
        if item_id not in item_chunks_map:
            item_chunks_map[item_id] = []
        item_chunks_map[item_id].append(chunk)
    
    # Sort the list of item_ids based on the score of their first (best) chunk
    # This ensures that even in round-robin, we prioritize more relevant articles
    sorted_item_ids = sorted(
        item_chunks_map.keys(), 
        key=lambda i: item_chunks_map[i][0]['score'], 
        reverse=True
    )
    
    selected_chunks = []
    round_idx = 0
    
    # Continue rounds until we have k chunks or no more chunks are available
    while len(selected_chunks) < k:
        chunks_added_this_round = 0
        
        for item_id in sorted_item_ids:
            # Check if this article has a chunk for the current round
            if round_idx < len(item_chunks_map[item_id]):
                selected_chunks.append(item_chunks_map[item_id][round_idx])
                chunks_added_this_round += 1
                
                # Stop if we've reached the limit
                if len(selected_chunks) >= k:
                    break
        
        # If no chunks were added in a full round, we're done
        if chunks_added_this_round == 0:
            break
            
        round_idx += 1
        
    return selected_chunks



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


async def generate_answer(query: str, chunks: List[Dict]) -> Dict[str, any]:
    """
    Generate an answer using Gemini 2.5 Flash based on retrieved chunks.
    
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
        # Build evidence from chunks with numbered sources
        evidence, source_mapping = await _build_evidence_from_chunks(chunks)
        
        # Build the prompt with strict citation requirements
        prompt = _build_citation_prompt(query, evidence, source_mapping)
        
        # Use the higher-reasoning model for citation-grounded answers.
        response_text = gemini_service.generate_content(
            prompt=prompt,
            model=GEMINI_MODEL_TEXT_REASONING
        )
        
        if not response_text:
            logger.warning("Empty response from Gemini")
            return {
                'answer': "I received an empty response. Please try again.",
                'citations': [],
                'chunks_used': 0
            }
        
        # Parse response and extract citations with source mapping
        answer, citations = await _parse_answer_with_citations(response_text, chunks, source_mapping)
        
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


async def _build_evidence_from_chunks(chunks: List[Dict]) -> tuple:
    """
    Build evidence string from chunks for the prompt with numbered sources.
    
    Args:
        chunks: List of chunk dicts from vector_search
        
    Returns:
        Tuple of (evidence_string, source_mapping)
        - evidence_string: Formatted evidence with numbered sources
        - source_mapping: Dict mapping source numbers to titles
    """
    evidence_parts = []
    source_mapping = {}
    seen_items = {}  # Track unique items by item_id
    current_number = 1
    
    for chunk in chunks:
        text = chunk.get('text', '')
        # Truncate very long chunks to keep token usage within context limits
        # Each chunk is ~500 tokens, which maps to ~2500-4000 chars.
        if len(text) > 4000:
            text = text[:4000] + "..."
        
        # Fetch item metadata to get the title
        item_metadata = await _get_item_metadata(chunk)
        item_id = chunk.get('item_id')
        title = item_metadata.get('title', f'Source {current_number}')
        
        # Assign a number to this source if we haven't seen it before
        if item_id not in seen_items:
            seen_items[item_id] = current_number
            source_mapping[current_number] = title
            current_number += 1
        
        source_num = seen_items[item_id]
        evidence_parts.append(f"[{source_num}] {text}")
    
    return "\n\n".join(evidence_parts), source_mapping


def _build_citation_prompt(query: str, evidence: str, source_mapping: Dict[int, str]) -> str:
    """
    Build the RAG prompt with strict citation requirements using numbered sources.
    
    This prompt enforces:
    - Answer ONLY using provided evidence
    - Include numbered citations (e.g., [1], [2])
    - Say "I don't have enough information" if evidence is insufficient
    - Keep answers concise
    
    Args:
        query: User's question
        evidence: Formatted evidence from chunks with numbers
        source_mapping: Dict mapping source numbers to titles
        
    Returns:
        Complete prompt string for Gemini
    """
    # Build source list for reference
    source_list = "\n".join([f"{num}. {title}" for num, title in sorted(source_mapping.items())])
    
    return f"""You are a helpful assistant that answers questions based ONLY on the provided evidence.

EVIDENCE:
{evidence}

SOURCE LIST:
{source_list}

QUESTION: {query}

INSTRUCTIONS:
- Answer using ONLY the evidence provided above
- Include citations using numbered references (e.g., [1], [2]) when referencing evidence
- Use the source numbers shown in the evidence (e.g., [1], [2], [3])
- You may cite the same source multiple times if needed
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


async def _parse_answer_with_citations(response_text: str, chunks: List[Dict], source_mapping: Dict[int, str]) -> tuple:
    """
    Parse Gemini response to extract answer and generate citations using sequential re-indexing.
    
    This function:
    1. Extracts the answer text
    2. Identifies which sources were cited by the AI (using original source numbers)
    3. Re-indexes the cited sources sequentially ([1], [2], [3]...) based on their 
       first appearance in the text to avoid gaps and offer a cleaner UX.
    4. Creates Citation objects with matching sequential numbers
    
    Args:
        response_text: Raw response from Gemini
        chunks: Original chunks used for evidence
        source_mapping: Dict mapping source numbers to titles
        
    Returns:
        Tuple of (reindexed_answer_text, list_of_citations)
    """
    import re
    from ..models.chat import Citation
    
    # Extract answer (everything is the answer)
    answer = response_text.strip()
    
    # Build a mapping of item_id to chunk for quick lookup
    item_to_chunk = {}
    for chunk in chunks:
        item_id = chunk.get('item_id')
        if item_id and item_id not in item_to_chunk:
            item_to_chunk[item_id] = chunk
    
    # Build mapping: item_id -> original source number
    item_to_orig_number = {}
    seen_items = {}
    current_number = 1
    
    for chunk in chunks:
        item_id = chunk.get('item_id')
        if item_id and item_id not in seen_items:
            seen_items[item_id] = current_number
            item_to_orig_number[item_id] = current_number
            current_number += 1
            
    # Find all numbered citations in the answer (e.g. [1], [1, 2])
    # This finds the original numbers used by the AI
    citation_pattern = r'\[(\d+(?:,\s*\d+)*)\]'
    
    # 1. First, identify all unique original source numbers cited, in order of appearance
    orig_matches = re.finditer(citation_pattern, answer)
    ordered_orig_nums = []
    seen_orig_nums = set()
    
    for match in orig_matches:
        # Extract individual numbers from the match
        nums = re.findall(r'\d+', match.group(1))
        for n in nums:
            n_int = int(n)
            if n_int not in seen_orig_nums:
                seen_orig_nums.add(n_int)
                ordered_orig_nums.append(n_int)
    
    # 2. Create a mapping from original source number to new sequential citation number
    # Only for sources that actually exist in our mapping
    orig_to_new_map = {}
    new_idx = 1
    citations = []
    
    for orig_num in ordered_orig_nums:
        title = source_mapping.get(orig_num)
        if not title:
            continue
            
        # Find matching item_id
        matching_item_id = None
        for item_id, num in item_to_orig_number.items():
            if num == orig_num:
                matching_item_id = item_id
                break
        
        if not matching_item_id:
            continue
            
        # Assign new sequential index
        orig_to_new_map[orig_num] = new_idx
        
        # Create Citation object
        chunk = item_to_chunk.get(matching_item_id)
        excerpt = "No preview available"
        if chunk:
            text = chunk.get('text', '')
            excerpt = text[:200]
            if len(text) > 200:
                excerpt += "..."
        
        citations.append(Citation(
            id=str(matching_item_id),
            title=f"{new_idx}. {title}",
            excerpt=excerpt
        ))
        new_idx += 1
        
    # 3. Handle citation replacement in the text to avoid gaps
    def replace_citation(match):
        orig_content = match.group(1)
        orig_nums = re.findall(r'\d+', orig_content)
        new_nums = []
        for n in orig_nums:
            n_int = int(n)
            if n_int in orig_to_new_map:
                new_nums.append(str(orig_to_new_map[n_int]))
        
        if not new_nums:
            return f"[{orig_content}]" # Keep original if we can't map it
            
        return f"[{', '.join(sorted(new_nums, key=int))}]"
        
    reindexed_answer = re.sub(citation_pattern, replace_citation, answer)
    
    return reindexed_answer, citations


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
    """Build the RAG prompt for grounded answer generation."""
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
