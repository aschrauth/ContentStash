"""
Content extraction service using readability-lxml for robust text extraction.
Falls back to Playwright for JavaScript-heavy sites.
"""
import requests
from readability import Document
from typing import Optional, Dict
import logging
from markdownify import markdownify as md
from .youtube import is_youtube_url, extract_video_id, get_video_transcript, get_transcript_from_ytdlp, get_video_metadata_from_api, get_video_metadata_from_ytdlp
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio
from ..config import settings

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
        # Be VERY specific to avoid false positives that would remove article content
        # Only trigger on exact heading patterns, not inline mentions
        if re.match(r'^#+\s*(related articles|you might also like|more from|read next|discover more|in our library)$', stripped, re.IGNORECASE):
            in_related_section = True
            continue
        
        # Also check for these as standalone lines (not headings)
        if stripped.lower() in ['related articles', 'you might also like', 'more from', 'read next', 'discover more', 'in our library']:
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
            # Launch browser in headless mode with realistic user agent
            try:
                browser = await p.chromium.launch(headless=True)
            except Exception as launch_error:
                logger.error(
                    f"Failed to launch Chromium browser. This may indicate missing browser binaries or system dependencies. "
                    f"Error: {str(launch_error)}",
                    exc_info=True
                )
                logger.error(
                    "TROUBLESHOOTING: "
                    "1. Ensure 'playwright install chromium' was run during deployment. "
                    "2. Verify system dependencies are installed (libnss3, libatk1.0-0, etc.). "
                    "3. Check Render.com build logs for Playwright installation errors. "
                    f"See deployment documentation for details."
                )
                raise
            page = await browser.new_page()
            
            # Set a realistic user agent to avoid bot detection
            await page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            # Detect if this is a Substack URL
            is_substack = 'substack.com' in url or '.so/p/' in url
            
            # Increase timeout for Substack and other slow-loading sites
            timeout = 90000 if is_substack else 30000
            
            # Navigate to the page - use 'domcontentloaded' for faster loading
            # networkidle can be too slow for some sites
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            # For Substack, wait for specific content elements to load
            if is_substack:
                try:
                    # Wait for the main article content to be present
                    await page.wait_for_selector('article, .post-content, .body', timeout=10000)
                    logger.info("Substack article content loaded")
                except:
                    logger.warning("Substack content selector not found, continuing anyway")
            
            # Wait a bit more for any lazy-loaded content
            await asyncio.sleep(3 if is_substack else 2)
            
            # Remove unwanted elements before extraction
            # For Substack, be VERY conservative - don't remove elements that might contain article content
            is_substack_js = 'true' if is_substack else 'false'
            await page.evaluate(f"""
                () => {{
                    const isSubstack = {is_substack_js};
                    
                    // Remove script and style tags
                    document.querySelectorAll('script, style, noscript').forEach(el => el.remove());
                    
                    // Remove JSON data blocks (often in square brackets)
                    document.querySelectorAll('*').forEach(el => {{
                        if (el.textContent.trim().startsWith('[') &&
                            el.textContent.includes('"type":') &&
                            el.textContent.includes('"id":')) {{
                            el.remove();
                        }}
                    }});
                    
                    if (isSubstack) {{
                        // For Substack, only remove very specific elements
                        // DO NOT use broad selectors that might catch article content
                        const unwantedSelectors = [
                            'nav:not(.post-header)',
                            'header:not(.post-header)',
                            'footer',
                            '.comments-container',
                            '.subscription-widget-wrap'
                        ];
                        
                        unwantedSelectors.forEach(selector => {{
                            document.querySelectorAll(selector).forEach(el => el.remove());
                        }});
                    }} else {{
                        // For non-Substack sites, use broader cleanup
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
                        
                        unwantedSelectors.forEach(selector => {{
                            document.querySelectorAll(selector).forEach(el => el.remove());
                        }});
                    }}
                    
                    // Remove elements containing "More useful" or similar text
                    // Be VERY specific - only match exact phrases as standalone headings
                    document.querySelectorAll('h3, h4, h5, h6').forEach(el => {{
                        const text = el.textContent.toLowerCase().trim();
                        // Only match exact phrases, not partial matches
                        if (text === 'more useful' ||
                            text === 'you might also like' ||
                            text === 'related articles' ||
                            text === 'related posts' ||
                            text === 'related content' ||
                            text === 'discover more' ||
                            text === 'read next' ||
                            text === 'more from' ||
                            text === 'in our library') {{
                            // Remove this heading and all following siblings
                            let sibling = el.nextElementSibling;
                            el.remove();
                            while (sibling) {{
                                const next = sibling.nextElementSibling;
                                sibling.remove();
                                sibling = next;
                            }}
                        }}
                    }});
                }}
            """)
            
            # Try to find the main content area using common selectors
            # Different selectors for different platforms
            if is_substack:
                # Substack-specific selectors (in priority order)
                content_selectors = [
                    '.body.markup',  # Main article body in Substack
                    'article .body',  # Article body
                    '.post-content',  # Post content wrapper
                    'article',  # Generic article tag
                    '.available-content',  # Available content section
                    'main',  # Main content area
                ]
            else:
                # Generic selectors for other sites (Squarespace, etc.)
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
            
    except PlaywrightTimeoutError as e:
        logger.error(
            f"Playwright timeout while loading {url}. The page took too long to load (timeout exceeded). "
            f"This may indicate a slow website or network issues. Error: {str(e)}"
        )
        return None
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        # Provide specific guidance based on error type
        if "Executable doesn't exist" in error_msg or "Browser closed" in error_msg:
            logger.error(
                f"Playwright browser error for {url}: {error_type} - {error_msg}. "
                f"CAUSE: Chromium browser binaries are not installed or system dependencies are missing. "
                f"SOLUTION: "
                f"1. Verify 'playwright install chromium' ran successfully during build. "
                f"2. Check that all required system packages are installed (see DEPLOYMENT.md). "
                f"3. Review Render.com build logs for installation errors.",
                exc_info=True
            )
        elif "net::" in error_msg or "NS_ERROR" in error_msg:
            logger.error(
                f"Playwright network error for {url}: {error_type} - {error_msg}. "
                f"CAUSE: Network connectivity issue or DNS resolution failure. "
                f"SOLUTION: Check network connectivity and verify the URL is accessible.",
                exc_info=True
            )
        elif "Target closed" in error_msg or "Protocol error" in error_msg:
            logger.error(
                f"Playwright browser crash for {url}: {error_type} - {error_msg}. "
                f"CAUSE: Browser process crashed, possibly due to insufficient memory or missing dependencies. "
                f"SOLUTION: "
                f"1. Ensure sufficient memory is allocated (minimum 512MB recommended). "
                f"2. Verify all system dependencies are installed. "
                f"3. Check for memory-related errors in deployment logs.",
                exc_info=True
            )
        else:
            logger.error(
                f"Playwright error extracting content from {url}: {error_type} - {error_msg}. "
                f"See stack trace for details.",
                exc_info=True
            )
        
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
            logger.info(f"Attempting to extract transcript for video ID: {video_id}")
            
            # Step 1: Try youtube_transcript_api (fastest)
            transcript = get_video_transcript(video_id)
            
            if transcript:
                logger.info(f"✓ Successfully extracted YouTube transcript for {url} ({len(transcript)} characters)")
                return transcript
            else:
                logger.warning(f"✗ YouTube transcript API failed for {url}")
                logger.info(f"Attempting yt-dlp transcript fallback for video ID: {video_id}")
                
                # Step 2: Try yt-dlp transcript extraction (most reliable)
                ytdlp_transcript = get_transcript_from_ytdlp(video_id)
                
                if ytdlp_transcript:
                    logger.info(f"✓ Successfully extracted transcript from yt-dlp for {url} ({len(ytdlp_transcript)} characters)")
                    return ytdlp_transcript
                else:
                    logger.warning(f"✗ yt-dlp transcript extraction failed for {url}")
                    logger.info(f"Attempting YouTube Data API metadata fallback for video ID: {video_id}")
                    
                    # Step 3: Try YouTube Data API for metadata only
                    youtube_metadata = get_video_metadata_from_api(video_id, settings.youtube_api_key)
                    
                    if youtube_metadata:
                        logger.info(f"✓ Successfully fetched metadata from YouTube API for {url}")
                        # Create content from metadata
                        content = f"# {youtube_metadata.get('title', 'YouTube Video')}\n\n"
                        content += f"**Channel:** {youtube_metadata.get('channel_name', 'Unknown')}\n\n"
                        if youtube_metadata.get('description'):
                            content += f"{youtube_metadata['description']}"
                        
                        logger.info(f"Using YouTube API metadata as content ({len(content)} characters)")
                        return content
                    else:
                        logger.warning(f"✗ YouTube API failed, trying yt-dlp metadata fallback for {url}")
                        
                        # Step 4: Try yt-dlp for metadata only (final fallback)
                        ytdlp_metadata = get_video_metadata_from_ytdlp(video_id)
                        
                        if ytdlp_metadata:
                            logger.info(f"✓ Successfully fetched metadata from yt-dlp for {url}")
                            # Create content from yt-dlp metadata
                            content = f"# {ytdlp_metadata.get('title', 'YouTube Video')}\n\n"
                            content += f"**Channel:** {ytdlp_metadata.get('channel_name', 'Unknown')}\n\n"
                            if ytdlp_metadata.get('description'):
                                content += f"{ytdlp_metadata['description']}"
                            
                            logger.info(f"Using yt-dlp metadata as content ({len(content)} characters)")
                            return content
                        else:
                            logger.error(f"✗ All YouTube extraction methods failed for {url}, falling back to web scraping")
        else:
            logger.error(f"✗ Failed to extract video ID from YouTube URL: {url}, falling back to standard extraction")
    
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
    For YouTube URLs, uses transcript API with YouTube Data API v3 fallback.
    
    Args:
        url: The URL to extract from
        extraction_type: "fast" (default) uses Readability with Playwright fallback,
                        "complete" skips Readability and goes directly to Playwright
        
    Returns:
        Dictionary with 'text' and optional metadata fields
    """
    # Check if this is a YouTube URL and handle it specially
    if is_youtube_url(url):
        logger.info(f"Detected YouTube URL for metadata extraction: {url}")
        video_id = extract_video_id(url)
        
        if video_id:
            # Step 1: Try youtube_transcript_api (fastest)
            transcript = get_video_transcript(video_id)
            
            # Step 2: If transcript API failed, try yt-dlp transcript
            if not transcript:
                logger.info(f"YouTube transcript API failed, trying yt-dlp transcript for {url}")
                transcript = get_transcript_from_ytdlp(video_id)
                if transcript:
                    logger.info(f"✓ Successfully extracted transcript from yt-dlp for {url}")
            
            # Try to get metadata from YouTube Data API
            youtube_metadata = get_video_metadata_from_api(video_id, settings.youtube_api_key)
            
            # If API failed, try yt-dlp as fallback for metadata
            if not youtube_metadata:
                logger.info(f"YouTube API unavailable, trying yt-dlp for metadata")
                youtube_metadata = get_video_metadata_from_ytdlp(video_id)
                if youtube_metadata:
                    logger.info(f"✓ Successfully fetched metadata from yt-dlp")
            
            if transcript:
                logger.info(f"Successfully extracted YouTube transcript and metadata for {url}")
                # If we have both transcript and metadata, use them
                if youtube_metadata:
                    return {
                        'text': transcript,
                        'title': youtube_metadata.get('title'),
                        'description': youtube_metadata.get('description'),
                        'image_url': youtube_metadata.get('thumbnail_url'),
                        'author': youtube_metadata.get('channel_name'),
                        'date': youtube_metadata.get('published_at'),
                        'url': url
                    }
                else:
                    # Transcript succeeded but metadata failed - still return transcript
                    logger.warning(f"YouTube metadata unavailable for {url}, using transcript only")
                    return {
                        'text': transcript,
                        'title': None,
                        'description': None,
                        'image_url': None,
                        'author': None,
                        'date': None,
                        'url': url
                    }
            elif youtube_metadata:
                # Transcript failed but we have metadata
                logger.warning(f"YouTube transcript unavailable for {url}, using metadata with description as content")
                # Use description as content if transcript is unavailable
                content = f"# {youtube_metadata.get('title', 'YouTube Video')}\n\n"
                content += f"**Channel:** {youtube_metadata.get('channel_name', 'Unknown')}\n\n"
                if youtube_metadata.get('description'):
                    content += f"{youtube_metadata['description']}"
                
                return {
                    'text': content,
                    'title': youtube_metadata.get('title'),
                    'description': youtube_metadata.get('description'),
                    'image_url': youtube_metadata.get('thumbnail_url'),
                    'author': youtube_metadata.get('channel_name'),
                    'date': youtube_metadata.get('published_at'),
                    'url': url
                }
            else:
                # Both transcript and metadata failed
                logger.error(f"Failed to extract both transcript and metadata from YouTube for {url}")
                return {
                    'text': None,
                    'title': None,
                    'description': None,
                    'image_url': None,
                    'author': None,
                    'date': None,
                    'url': url
                }
        else:
            logger.error(f"Failed to extract video ID from YouTube URL: {url}")
            return {'text': None}
    
    # For non-YouTube URLs, use the existing extraction logic
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