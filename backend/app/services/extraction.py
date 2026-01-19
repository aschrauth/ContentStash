"""
Content extraction service using readability-lxml for robust text extraction.
Falls back to Playwright for JavaScript-heavy sites.
"""
import requests
from readability import Document
from typing import Optional
import logging
from markdownify import markdownify as md
from .youtube import is_youtube_url, extract_video_id, get_video_transcript
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio

logger = logging.getLogger(__name__)

# Minimum content length threshold - if readability extracts less than this,
# we'll try Playwright as the site likely uses JavaScript rendering
MIN_CONTENT_LENGTH = 1000


async def _extract_with_playwright(url: str) -> Optional[str]:
    """
    Extract content using Playwright for JavaScript-heavy sites.
    Uses direct text extraction from the main content area instead of relying on readability.
    
    Args:
        url: The URL to extract content from
        
    Returns:
        Extracted markdown content or None if extraction fails
    """
    try:
        logger.info(f"Attempting Playwright extraction for {url}")
        async with async_playwright() as p:
            # Launch browser in headless mode
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Navigate to the page and wait for network to be idle
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait a bit more for any lazy-loaded content
            await asyncio.sleep(2)
            
            # Try to find the main content area using common selectors
            # Squarespace typically uses article, main, or specific content divs
            content_selectors = [
                'article',
                'main',
                '[role="main"]',
                '.blog-item-content',
                '.sqs-block-content',
                '#page',
                '.page-content'
            ]
            
            extracted_html = None
            for selector in content_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        extracted_html = await element.inner_html()
                        if len(extracted_html) > MIN_CONTENT_LENGTH:
                            logger.info(f"Found content using selector '{selector}' ({len(extracted_html)} chars)")
                            break
                except:
                    continue
            
            # If no selector worked, get the full body
            if not extracted_html or len(extracted_html) < MIN_CONTENT_LENGTH:
                logger.info("Using full body content as fallback")
                body = await page.query_selector('body')
                if body:
                    extracted_html = await body.inner_html()
            
            await browser.close()
            
            if not extracted_html:
                logger.warning(f"No content extracted from {url}")
                return None
            
            # Convert the extracted HTML to markdown
            markdown_content = md(
                extracted_html,
                heading_style="ATX",
                strip=['script', 'style', 'nav', 'header', 'footer']
            )
            
            logger.info(f"Playwright successfully extracted {len(markdown_content)} characters from {url}")
            return markdown_content
            
    except PlaywrightTimeoutError:
        logger.error(f"Playwright timeout while loading {url}")
        return None
    except Exception as e:
        logger.error(f"Playwright error extracting content from {url}: {str(e)}")
        return None


async def extract_content(url: str) -> Optional[str]:
    """
    Extract main content text from a URL using readability-lxml.
    For YouTube URLs, attempts to extract video transcript first.
    
    Args:
        url: The URL to extract content from
        
    Returns:
        Extracted text content or None if extraction fails
    """
    # Check if this is a YouTube URL and try to get transcript
    if is_youtube_url(url):
        logger.info(f"Detected YouTube URL: {url}")
        video_id = extract_video_id(url)
        
        if video_id:
            transcript = get_video_transcript(video_id)
            if transcript:
                logger.info(f"Successfully extracted YouTube transcript for {url}")
                return transcript
            else:
                logger.warning(f"Failed to get YouTube transcript for {url}, falling back to standard extraction")
        else:
            logger.warning(f"Failed to extract video ID from YouTube URL: {url}, falling back to standard extraction")
    
    # Fall back to standard web content extraction
    try:
        # First attempt: Try with requests + readability
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse with readability
        doc = Document(response.text)
        html_content = doc.summary()
        
        # Check if we got enough content
        if html_content and len(html_content) >= MIN_CONTENT_LENGTH:
            # Good content from readability, convert to markdown
            markdown_content = md(
                html_content,
                heading_style="ATX",
                strip=['script', 'style']
            )
            
            if markdown_content:
                logger.info(f"Successfully extracted {len(markdown_content)} characters from {url} using readability")
                return markdown_content
        
        # If we got here, readability didn't extract enough content
        # This likely means the site uses JavaScript rendering
        logger.warning(f"Readability extracted insufficient content ({len(html_content) if html_content else 0} chars) from {url}, trying Playwright")
        
        # Second attempt: Use Playwright for JavaScript rendering
        # Note: _extract_with_playwright now returns markdown directly
        markdown_content = await _extract_with_playwright(url)
        
        if markdown_content:
            logger.info(f"Successfully extracted {len(markdown_content)} characters from {url} using Playwright")
            return markdown_content
        else:
            logger.warning(f"Playwright also failed to extract content from {url}")
            return None
            
    except requests.RequestException as e:
        logger.error(f"Error fetching content from {url}: {str(e)}")
        # Try Playwright as a last resort
        logger.info(f"Attempting Playwright extraction after request error")
        markdown_content = await _extract_with_playwright(url)
        if markdown_content:
            logger.info(f"Successfully extracted {len(markdown_content)} characters from {url} using Playwright fallback")
            return markdown_content
        return None
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {str(e)}")
        return None


async def extract_content_with_metadata(url: str) -> dict:
    """
    Extract content and metadata using readability-lxml.
    Falls back to Playwright for JavaScript-heavy sites.
    
    Args:
        url: The URL to extract from
        
    Returns:
        Dictionary with 'text' and optional metadata fields
    """
    try:
        # First attempt: Try with requests + readability
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse with readability
        doc = Document(response.text)
        html_content = doc.summary()
        
        # Check if we got enough content
        if html_content and len(html_content) >= MIN_CONTENT_LENGTH:
            # Good content from readability
            markdown_text = md(
                html_content,
                heading_style="ATX",
                strip=['script', 'style']
            )
            
            title = doc.title()
            
            logger.info(f"Extracted content with metadata from {url} using readability")
            return {
                'text': markdown_text,
                'title': title,
                'author': None,
                'date': None,
                'url': url
            }
        
        # Insufficient content, try Playwright
        logger.warning(f"Readability extracted insufficient content from {url}, trying Playwright")
        markdown_text = await _extract_with_playwright(url)
        
        if not markdown_text:
            return {'text': None}
        
        # For title, we still need to parse the original response
        doc = Document(response.text)
        title = doc.title()
        
        logger.info(f"Extracted content with metadata from {url} using Playwright")
        return {
            'text': markdown_text,
            'title': title,
            'author': None,
            'date': None,
            'url': url
        }
        
    except requests.RequestException as e:
        logger.error(f"Error fetching content from {url}: {str(e)}")
        # Try Playwright as fallback
        markdown_text = await _extract_with_playwright(url)
        if markdown_text:
            return {
                'text': markdown_text,
                'title': None,  # Can't get title without initial request
                'author': None,
                'date': None,
                'url': url
            }
        return {'text': None}
    except Exception as e:
        logger.error(f"Error extracting content with metadata from {url}: {str(e)}")
        return {'text': None}