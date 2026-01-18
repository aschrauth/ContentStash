"""
Content extraction service using readability-lxml for robust text extraction.
"""
import requests
from readability import Document
from typing import Optional
import logging
from markdownify import markdownify as md

logger = logging.getLogger(__name__)


def extract_content(url: str) -> Optional[str]:
    """
    Extract main content text from a URL using readability-lxml.
    
    Args:
        url: The URL to extract content from
        
    Returns:
        Extracted text content or None if extraction fails
    """
    try:
        # Fetch the page content
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse with readability
        doc = Document(response.text)
        
        # Get the main content HTML
        html_content = doc.summary()
        
        if not html_content:
            logger.warning(f"No content extracted from {url}")
            return None
        
        # Convert HTML to Markdown using markdownify
        # markdownify preserves list structures including ordered lists
        markdown_content = md(
            html_content,
            heading_style="ATX",  # Use # style headers
            strip=['script', 'style']  # Remove script and style tags
        )
        
        if markdown_content:
            logger.info(f"Successfully extracted {len(markdown_content)} characters from {url}")
            # Debug: Log a sample of the markdown to check list formatting
            sample = markdown_content[:500] if len(markdown_content) > 500 else markdown_content
            logger.debug(f"Markdown sample from {url}:\n{sample}")
            return markdown_content
        else:
            logger.warning(f"Failed to convert HTML to Markdown for {url}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error fetching content from {url}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {str(e)}")
        return None


def extract_content_with_metadata(url: str) -> dict:
    """
    Extract content and metadata using readability-lxml.
    
    Args:
        url: The URL to extract from
        
    Returns:
        Dictionary with 'text' and optional metadata fields
    """
    try:
        # Fetch the page content
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse with readability
        doc = Document(response.text)
        
        # Get the main content HTML
        html_content = doc.summary()
        
        if not html_content:
            return {'text': None}
        
        # Convert to markdown using markdownify
        markdown_text = md(
            html_content,
            heading_style="ATX",
            strip=['script', 'style']
        )
        
        # Extract metadata from readability
        title = doc.title()
        
        logger.info(f"Extracted content with metadata from {url}")
        return {
            'text': markdown_text,
            'title': title,
            'author': None,  # readability-lxml doesn't extract author
            'date': None,    # readability-lxml doesn't extract date
            'url': url
        }
        
    except requests.RequestException as e:
        logger.error(f"Error fetching content from {url}: {str(e)}")
        return {'text': None}
    except Exception as e:
        logger.error(f"Error extracting content with metadata from {url}: {str(e)}")
        return {'text': None}