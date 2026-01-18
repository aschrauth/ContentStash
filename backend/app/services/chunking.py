"""
Chunking service for splitting text into overlapping chunks.
Uses token-based chunking with configurable chunk size and overlap.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 75
) -> List[str]:
    """
    Split text into overlapping chunks based on approximate token count.
    
    This function uses a simple whitespace-based tokenization strategy where
    each word is considered approximately one token. This is a reasonable
    approximation for most English text.
    
    Args:
        text: The text to chunk
        chunk_size: Target size of each chunk in tokens (default: 500)
        overlap: Number of tokens to overlap between chunks (default: 75)
    
    Returns:
        List of text chunks, each approximately chunk_size tokens
    
    Raises:
        ValueError: If chunk_size <= overlap or if parameters are invalid
    
    Examples:
        >>> text = "This is a sample text " * 100
        >>> chunks = chunk_text(text, chunk_size=50, overlap=10)
        >>> len(chunks) > 1
        True
    """
    # Validate parameters
    if chunk_size <= 0:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")
    
    if overlap < 0:
        raise ValueError(f"overlap must be non-negative, got {overlap}")
    
    if overlap >= chunk_size:
        raise ValueError(
            f"overlap ({overlap}) must be less than chunk_size ({chunk_size})"
        )
    
    # Handle edge cases
    if not text or not text.strip():
        logger.warning("Empty or whitespace-only text provided for chunking")
        return []
    
    # Tokenize by splitting on whitespace (approximate token count)
    tokens = text.split()
    
    if not tokens:
        logger.warning("No tokens found after splitting text")
        return []
    
    # If text is shorter than chunk_size, return as single chunk
    if len(tokens) <= chunk_size:
        logger.info(f"Text has {len(tokens)} tokens, returning as single chunk")
        return [text.strip()]
    
    chunks = []
    start_idx = 0
    
    while start_idx < len(tokens):
        # Calculate end index for this chunk
        end_idx = min(start_idx + chunk_size, len(tokens))
        
        # Extract chunk tokens and join back into text
        chunk_tokens = tokens[start_idx:end_idx]
        chunk = " ".join(chunk_tokens)
        chunks.append(chunk)
        
        # Move start index forward by (chunk_size - overlap)
        # This creates overlap between consecutive chunks
        start_idx += (chunk_size - overlap)
        
        # If we've reached the end, break
        if end_idx >= len(tokens):
            break
    
    logger.info(
        f"Chunked text into {len(chunks)} chunks "
        f"(original: {len(tokens)} tokens, "
        f"chunk_size: {chunk_size}, overlap: {overlap})"
    )
    
    return chunks


def estimate_token_count(text: str) -> int:
    """
    Estimate the number of tokens in a text using whitespace splitting.
    
    This is a simple approximation where each word is counted as one token.
    For more accurate token counting, consider using a proper tokenizer.
    
    Args:
        text: The text to estimate tokens for
    
    Returns:
        Estimated number of tokens
    """
    if not text or not text.strip():
        return 0
    
    return len(text.split())