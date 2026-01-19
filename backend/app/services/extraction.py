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

def _clean_extracted_content(content: str) -> str:
    """
    Clean extracted markdown content by removing unwanted patterns.
    
    Args:
        content: The markdown content to clean
        
    Returns:
        Cleaned markdown content
    """
    import re
    
    # Remove JSON data blocks (lines starting with [ { and containing JSON-like patterns)
    lines = content.split('\n')
    cleaned_lines = []
    in_json_block = False
    in_related_section = False
    
    for line in lines:
        stripped = line.strip()
        
        # Detect start of JSON block
        if stripped.startswith('[ {') or (stripped.startswith('[') and '"type":' in stripped):
            in_json_block = True
            continue
        
        # Detect end of JSON block
        if in_json_block:
            if stripped.endswith('] ]') or stripped.endswith('}]'):
                in_json_block = False
            continue
        
        # Skip lines with hex-encoded JavaScript (obfuscated code)
        if re.search(r'\\x[0-9a-fA-F]{2}', line):
            continue
        
        # Skip lines that look like minified/obfuscated JavaScript
        if re.search(r'[a-z]\[\'\\x[0-9a-fA-F]{2}', line):
            continue
        
        # Detect "Related articles" or similar sections and skip everything after
        # Also detect "More useful" or "Discover more" type sections
        # Use word boundaries to avoid matching legitimate headings like "Relatedness"
        if re.search(r'\b(related articles|you might also like|more from|read next|more useful|discover more|in our library)\b', stripped, re.IGNORECASE):
            in_related_section = True
            continue
        
        # Skip everything in the related section
        if in_related_section:
            continue
        
        # Skip common footer/navigation patterns
        skip_patterns = [
            r'^\[.*\]\(/resources\?author=',  # Author links
            r'^\[.*\]\(/resources/tag/',       # Tag links
            r'^\[!\[\].*\]\(/resources/',      # Related article image links
            r'^\[.*\]\(/resources/[^)]+\)$',   # Generic resource links
            r'^Share this',
            r'^Subscribe',
            r'^Newsletter',
        ]
        
        if any(re.match(pattern, stripped, re.IGNORECASE) for pattern in skip_patterns):
            continue
        
        cleaned_lines.append(line)
    
    # Join lines and remove excessive blank lines
    cleaned_content = '\n'.join(cleaned_lines)
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
    
    return cleaned_content.strip()



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
            
            # Remove unwanted elements before extraction
            await page.evaluate("""
                () => {
                    // Remove script and style tags
                    document.querySelectorAll('script, style, noscript').forEach(el => el.remove());
                    
                    // Remove JSON data blocks (often in square brackets)
                    document.querySelectorAll('*').forEach(el => {
                        if (el.textContent.trim().startsWith('[') &&
                            el.textContent.includes('"type":') &&
                            el.textContent.includes('"id":')) {
                            el.remove();
                        }
                    });
                    
                    // Remove common navigation and footer elements
                    const unwantedSelectors = [
                        'nav', 'header', 'footer',
                        '.navigation', '.nav', '.menu',
                        '.sidebar', '.related', '.comments',
                        '.share', '.social', '.newsletter',
                        '[class*="related"]', '[class*="share"]',
                        '[class*="subscribe"]', '[class*="newsletter"]',
                        '.blog-meta-item', '.blog-categories',
                        '.blog-tags', '.author-bio',
                        '[class*="summary-item"]', '.summary-item-list'
                    ];
                    
                    unwantedSelectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => el.remove());
                    });
                    
                    // Remove elements containing "More useful" or similar text
                    // Use more specific patterns to avoid removing legitimate headings like "Relatedness"
                    document.querySelectorAll('h3, h4, h5').forEach(el => {
                        const text = el.textContent.toLowerCase().trim();
                        if (text.includes('more useful') ||
                            text.includes('you might also') ||
                            text.includes('related articles') ||
                            text.includes('related posts') ||
                            text.includes('related content') ||
                            text.includes('discover more')) {
                            // Remove this heading and all following siblings
                            let sibling = el.nextElementSibling;
                            el.remove();
                            while (sibling) {
                                const next = sibling.nextElementSibling;
                                sibling.remove();
                                sibling = next;
                            }
                        }
                    });
                }
            """)
            
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
            
            # Post-process to remove any remaining JSON blocks and unwanted patterns
            markdown_content = _clean_extracted_content(markdown_content)
            
            logger.info(f"Playwright successfully extracted {len(markdown_content)} characters from {url}")
            return markdown_content
            
    except PlaywrightTimeoutError:
        logger.error(f"Playwright timeout while loading {url}")
        return None
    except Exception as e:
        logger.error(f"Playwright error extracting content from {url}: {str(e)}")
        return None


async def extract_content(url: str, extraction_type: str = "fast") -> Optional[str]:
    """
    Extract main content text from a URL using readability-lxml.
    For YouTube URLs, attempts to extract video transcript first.
    
    Args:
        url: The URL to extract content from
        extraction_type: "fast" (default) uses Readability with Playwright fallback,
                        "complete" skips Readability and goes directly to Playwright
        
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
        # For "complete" extraction type, skip Readability and go directly to Playwright
        if extraction_type == "complete":
            logger.info(f"Using complete extraction (Playwright) for {url}")
            markdown_content = await _extract_with_playwright(url)
            
            if markdown_content:
                logger.info(f"Successfully extracted {len(markdown_content)} characters from {url} using Playwright (complete mode)")
                return markdown_content
            else:
                logger.warning(f"Playwright failed to extract content from {url}")
                return None
        
        # For "fast" extraction type, use the cascade logic (Readability → Playwright fallback)
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


async def extract_content_with_metadata(url: str, extraction_type: str = "fast") -> dict:
    """
    Extract content and metadata using readability-lxml.
    Falls back to Playwright for JavaScript-heavy sites.
    
    Args:
        url: The URL to extract from
        extraction_type: "fast" (default) uses Readability with Playwright fallback,
                        "complete" skips Readability and goes directly to Playwright
        
    Returns:
        Dictionary with 'text' and optional metadata fields
    """
    try:
        # For "complete" extraction type, skip Readability and go directly to Playwright
        if extraction_type == "complete":
            logger.info(f"Using complete extraction (Playwright) for {url}")
            markdown_text = await _extract_with_playwright(url)
            
            if not markdown_text:
                return {'text': None}
            
            # Try to get title from initial request
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                doc = Document(response.text)
                title = doc.title()
            except:
                title = None
            
            logger.info(f"Extracted content with metadata from {url} using Playwright (complete mode)")
            return {
                'text': markdown_text,
                'title': title,
                'author': None,
                'date': None,
                'url': url
            }
        
        # For "fast" extraction type, use the cascade logic
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