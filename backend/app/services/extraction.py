"""
Content extraction service using trafilatura for robust text extraction.
"""
import trafilatura
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def extract_content(url: str) -> Optional[str]:
    """
    Extract main content text from a URL using trafilatura.
    
    Args:
        url: The URL to extract content from
        
    Returns:
        Extracted text content or None if extraction fails
    """
    try:
        # Fetch the page content
        downloaded = trafilatura.fetch_url(url)
        
        if not downloaded:
            logger.warning(f"Failed to download content from {url}")
            return None
        
        # Extract the main content
        # include_comments=False to exclude comment sections
        # include_tables=True to preserve table data
        # no_fallback=False to use fallback extraction if needed
        extracted = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_precision=False  # Favor recall to get more content
        )
        
        if extracted:
            logger.info(f"Successfully extracted {len(extracted)} characters from {url}")
            return extracted
        else:
            logger.warning(f"No content extracted from {url}")
            return None
            
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {str(e)}")
        return None


def extract_content_with_metadata(url: str) -> dict:
    """
    Extract content and metadata using trafilatura.
    
    Args:
        url: The URL to extract from
        
    Returns:
        Dictionary with 'text' and optional metadata fields
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        
        if not downloaded:
            return {'text': None}
        
        # Extract with metadata
        result = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_tables=True,
            output_format='json',
            with_metadata=True
        )
        
        if result:
            import json
            data = json.loads(result)
            logger.info(f"Extracted content with metadata from {url}")
            return {
                'text': data.get('text'),
                'title': data.get('title'),
                'author': data.get('author'),
                'date': data.get('date'),
                'url': data.get('url')
            }
        
        return {'text': None}
        
    except Exception as e:
        logger.error(f"Error extracting content with metadata from {url}: {str(e)}")
        return {'text': None}