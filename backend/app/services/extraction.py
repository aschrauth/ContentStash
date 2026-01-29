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
from .exceptions import ExtractionBlockError
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import asyncio
from ..config import settings

logger = logging.getLogger(__name__)

# Minimum content length threshold - if readability extracts less than this,
# we'll try Playwright as the site likely uses JavaScript rendering
MIN_CONTENT_LENGTH = 1000


def extract_source_from_url(url: str) -> str:
    """
    Extract source domain from URL for display purposes.
    
    Args:
        url: The URL to extract source from
        
    Returns:
        Formatted source string (e.g., "nytimes.com" or "blog.example.com")
        Returns "Unknown" if URL parsing fails
    """
    try:
        from urllib.parse import urlparse
        
        # Parse the URL
        parsed = urlparse(url)
        
        # Get the netloc (domain with subdomain)
        netloc = parsed.netloc or parsed.path.split('/')[0]
        
        if not netloc:
            return "Unknown"
        
        # Remove port if present
        if ':' in netloc:
            netloc = netloc.split(':')[0]
        
        # Split into parts
        parts = netloc.split('.')
        
        # Handle edge cases
        if len(parts) < 2:
            return netloc
        
        # If subdomain is "www", return just domain.tld
        if parts[0] == 'www':
            return '.'.join(parts[1:])
        
        # Otherwise return subdomain.domain.tld
        return netloc
        
    except Exception as e:
        logger.warning(f"Failed to extract source from URL {url}: {str(e)}")
        return "Unknown"

def _clean_extracted_content(content: str) -> str:
    """
    Clean extracted markdown content by removing unwanted patterns.
    Uses generalizable patterns for ads, navigation, sharing widgets, and policies.
    Matches the comprehensive cleaning logic from the Chrome extension.
    
    Args:
        content: The markdown content to clean
        
    Returns:
        Cleaned markdown content
    """
    import re
    
    lines = content.split('\n')
    cleaned_lines = []
    in_json_block = False
    in_related_section = False
    related_section_skip_count = 0  # Track how many lines we've skipped in related section
    in_clutter_section = False
    in_navigation = False
    in_consent_section = False
    in_author_bio = False
    in_read_more_section = False
    skip_until_content = 0  # Counter to skip lines after certain patterns
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        lower_line = stripped.lower()
        
        # Skip lines if we're in a skip zone
        if skip_until_content > 0:
            skip_until_content -= 1
            continue
        
        # Detect "Manage Consent Preferences" section - skip everything after this
        # This needs to be very aggressive since it's always at the end
        # Check both the line itself and if it's a heading
        if 'manage consent' in lower_line or \
           'consent preferences' in lower_line or \
           'strictly necessary cookies' in lower_line or \
           'always active' in lower_line or \
           'opt out of sale' in lower_line or \
           'switch label' in lower_line or \
           'targeting cookies' in lower_line or \
           'performance cookies' in lower_line or \
           re.match(r'^#{1,6}\s*manage consent', stripped, re.IGNORECASE) or \
           re.match(r'^#{1,6}\s*consent preferences', stripped, re.IGNORECASE):
            in_consent_section = True
            continue
        
        # Once in consent section, skip everything
        if in_consent_section:
            continue
        
        # Detect broken markdown link patterns: lines that are just "](url)" or "text](url)"
        # These are the second half of multi-line markdown links (usually related articles)
        if re.match(r'^\]\(https?://[^)]+\)$', stripped):
            continue
        
        # Detect orphaned link endings from partially removed markdown links
        # Pattern: "Google Preferred](url)" or similar
        if re.match(r'^[^[]*\]\(https?://[^)]+\)$', stripped):
            # This looks like an orphaned link ending (no opening bracket)
            continue
        
        # Detect plain URLs (not markdown links) that are standalone
        # These are usually related articles
        if re.match(r'^https?://[^\s]+$', stripped):
            # It's a standalone URL on its own line - likely a related article
            continue
        
        # Detect multi-line markdown image-link patterns (related articles)
        # Pattern: "[" on one line, followed by image, followed by "](url)"
        if stripped == '[':
            # Look ahead to see if this is a multi-line image link pattern
            next1 = lines[i + 1].strip() if i + 1 < len(lines) else ''
            next2 = lines[i + 2].strip() if i + 2 < len(lines) else ''
            next3 = lines[i + 3].strip() if i + 3 < len(lines) else ''
            
            # Check if next line is blank, then image, then blank, then link closing
            if next1 == '' and next2.startswith('![') and next3 == '':
                next4 = lines[i + 4].strip() if i + 4 < len(lines) else ''
                if re.match(r'^\]\(https?://[^)]+\)$', next4):
                    # Skip the entire pattern: "[", blank, image, blank, "](url)"
                    skip_until_content = 4  # Skip next 4 lines (we're already on the "[")
                    continue
        
        # Detect embedded related article images - these are usually standalone images
        # that link to other articles (not part of the main content)
        if stripped.startswith('!['):
            # Check if this is followed by a link or if it's a standalone image
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ''
            prev_line = lines[i - 1].strip() if i > 0 else ''
            
            # If the image is followed by a link, or surrounded by blank lines, it's likely related content
            if next_line.startswith('[') or next_line.startswith('http') or \
               (prev_line == '' and next_line == ''):
                # Skip this image
                continue
        
        # Detect standalone article links (URLs that appear on their own line)
        # These are usually related articles, not inline citations
        if re.match(r'^https?://.*/(news|features|articles?|gallery|video)/', stripped) or \
           re.match(r'^\[.*\]\(https?://.*/(news|features|articles?|gallery|video)/.*\)', stripped):
            # Check if this is standalone (surrounded by blank lines or other media)
            prev_line = lines[i - 1].strip() if i > 0 else ''
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ''
            
            # If it's standalone or part of a media block, skip it
            if prev_line == '' or next_line == '' or \
               prev_line.startswith('![') or next_line.startswith('!['):
                continue
        
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
        
        # Detect navigation patterns (common menu items)
        navigation_patterns = [
            'open menu', 'close menu', 'open search', 'close search',
            'got a tip', 'newsletters', 'sign in', 'sign up',
            'news', 'film', 'tv', 'awards', 'video', 'toolkit',
            'future of filmmaking'
        ]
        
        # Check if line is likely navigation (short line with navigation keywords)
        if len(stripped) < 30 and any(pattern in lower_line for pattern in navigation_patterns):
            # Check if next few lines are also short (indicates menu structure)
            next_lines_short = sum(1 for j in range(i+1, min(i+4, len(lines)))
                                  if len(lines[j].strip()) < 30)
            if next_lines_short >= 2:
                in_navigation = True
                continue
        
        # Exit navigation when we hit substantial content
        if in_navigation and (len(stripped) > 100 or re.match(r'^#{1,3}\s+\w+', stripped)):
            in_navigation = False
        
        if in_navigation:
            continue
        
        # Detect author bio sections
        # Patterns: "has joined", "courtesy of", "more stories by"
        author_bio_patterns = [
            'has joined',
            'courtesy of',
            'more stories by',
            'about the author',
            'author bio',
            'staff writer',
            'senior reporter',
            'contributing writer'
        ]
        
        if any(pattern in lower_line for pattern in author_bio_patterns):
            # Check if it's a short line (likely a bio snippet)
            if len(stripped) < 200:
                in_author_bio = True
                continue
        
        # Exit author bio section when we hit substantial content or a heading
        if in_author_bio and (len(stripped) > 200 or re.match(r'^#{1,3}\s+', stripped)):
            in_author_bio = False
        
        if in_author_bio:
            continue
        
        # Detect "Read More" sections - including with colons
        read_more_patterns = [
            r'^#+\s*(read more|more reading|further reading|related reading)',
            r'^(read more|more reading|further reading|related reading):?$'
        ]
        
        if any(re.match(pattern, stripped, re.IGNORECASE) for pattern in read_more_patterns):
            in_read_more_section = True
            continue
        
        # Skip everything in the read more section
        if in_read_more_section:
            continue
        
        # Detect "Daily Headlines" and newsletter signup sections
        newsletter_patterns = [
            'daily headlines',
            'newsletter',
            'sign up for',
            'subscribe to',
            'get our newsletter',
            'email updates',
            'stay informed',
            'join our mailing list'
        ]
        
        if any(pattern in lower_line for pattern in newsletter_patterns):
            # Check if it's a heading or short promotional text
            if re.match(r'^#+\s*', stripped) or len(stripped) < 100:
                in_clutter_section = True
                continue
        
        # Detect ad/redirect messages (common pattern)
        if 'you will be redirected' in lower_line or 'redirecting' in lower_line:
            continue
        
        # Skip ad countdown/timer text
        if re.match(r'^(skip ad|ad \d+|advertisement|\d+ seconds?)$', lower_line):
            continue
        
        # Detect "Read Next" or similar inline related content
        if re.match(r'^read next:', lower_line, re.IGNORECASE):
            # Skip this line and the next 2-3 lines (usually the related article title/link)
            skip_until_content = 3
            continue
        
        # Exit related section when we encounter:
        # 1. A major heading (H1-H3) - indicates new section
        # 2. A long paragraph (>200 chars) - indicates main content resumed
        # 3. After skipping more than 10 consecutive lines - related sections are usually short
        if in_related_section:
            # Check exit conditions
            is_major_heading = re.match(r'^#{1,3}\s+\w+', stripped)
            is_long_paragraph = len(stripped) > 200 and not stripped.startswith('#')
            too_many_skipped = related_section_skip_count > 10
            
            if is_major_heading or is_long_paragraph or too_many_skipped:
                # Exit related section and process this line normally
                in_related_section = False
                related_section_skip_count = 0
                # Don't continue - let this line be processed normally
            else:
                # Still in related section, skip this line
                related_section_skip_count += 1
                continue
        
        # Detect "Related articles" or similar sections - ONLY trigger on headings
        # This makes detection more precise and prevents false positives
        # IMPORTANT: This check must happen BEFORE we add the line to cleaned_lines
        related_patterns = [
            r'^#{1,6}\s*(related articles?|related stories|you might also like|more from|read next|discover more|in our library|recommended|more stories|trending now)',
        ]
        
        if any(re.match(pattern, stripped, re.IGNORECASE) for pattern in related_patterns):
            in_related_section = True
            related_section_skip_count = 0
            continue
        
        # Detect common clutter sections (policies, sharing, consent, etc.)
        clutter_headings = [
            'privacy policy', 'cookie policy', 'terms of service', 'advertising policy',
            'consent preferences', 'manage consent', 'privacy settings',
            'share this', 'share article', 'follow us', 'newsletter', 'subscribe',
            'sign up', 'get updates', 'stay connected', 'join our',
            'cookies', 'advertising', 'your privacy choices',
            'opt out of sale', 'targeted advertising', 'switch label'
        ]
        
        if any(heading in lower_line for heading in clutter_headings):
            # Check if it's a heading or standalone text
            if re.match(r'^#+\s*', stripped) or len(stripped) < 80:
                in_clutter_section = True
                continue
        
        # Exit clutter section when we hit a substantial heading that's not clutter
        if in_clutter_section and re.match(r'^#{1,3}\s+', stripped) and len(stripped) > 20:
            # Check if this is still a clutter heading
            if not any(heading in lower_line for heading in clutter_headings):
                in_clutter_section = False
        
        if in_clutter_section:
            continue
        
        # Skip common sharing/social patterns (comprehensive list from Chrome extension)
        skip_patterns = [
            r'^\[.*\]\(/resources\?author=',  # Author links
            r'^\[.*\]\(/resources/tag/',       # Tag links
            r'^\[!\[\].*\]\(/resources/',      # Related article image links
            r'^\[.*\]\(/resources/[^)]+\)$',   # Generic resource links
            r'^(share|email|print|facebook|twitter|linkedin|copy link|whatsapp|reddit|pinterest|post|google|flipboard|tumblr)$',  # Sharing buttons
            r'^\*\*(share|email|print|facebook|twitter|linkedin|copy link|post|google)\*\*$',  # Bold sharing buttons
            r'^\[(share|email|print|facebook|twitter|linkedin|copy link|post|google)\]',  # Link sharing buttons
        ]
        
        if any(re.match(pattern, stripped, re.IGNORECASE) for pattern in skip_patterns):
            continue
        
        # Skip markdown links with sharing/social text (including list items)
        # Pattern: [Share on Facebook](url), * [Post](url), etc.
        sharing_link_patterns = [
            r'^\*?\s*\[share on facebook\]',
            r'^\*?\s*\[share on twitter\]',
            r'^\*?\s*\[share on linkedin\]',
            r'^\*?\s*\[share on whatsapp\]',
            r'^\*?\s*\[share to flipboard\]',
            r'^\*?\s*\[submit to reddit\]',
            r'^\*?\s*\[pin it\]',
            r'^\*?\s*\[post to tumblr\]',
            r'^\*?\s*\[print this page\]',
            r'^\*?\s*\[show more sharing options\]',
            r'^\*?\s*\[post\]\(',  # Twitter/X "Post" button as link
            r'^\*?\s*\[google',  # Google sharing link (matches "google" or "google preferred")
            r'^\*?\s*\[email\]\(',
            r'^\*?\s*\[print\]\(',
        ]
        
        if any(re.match(pattern, stripped, re.IGNORECASE) for pattern in sharing_link_patterns):
            continue
        
        # Skip standalone social media/sharing text (comprehensive list)
        # Also check for list items (* text)
        standalone_skip = [
            'share', 'email', 'print', 'facebook', 'twitter', 'linkedin',
            'copy link', 'share this article', 'share this story', 'whatsapp',
            'reddit', 'pinterest', 'share on facebook', 'share on twitter',
            'post',  # Twitter/X "Post" button
            'google',  # Google sharing
            'show more sharing options',
            'share to flipboard',
            'submit to reddit',
            'pin it',  # Pinterest
            'post to tumblr',
            'print this page',
            'share on whatsapp',
            'share on linkedin',
            'plus icon',  # Common icon text
            'google preferred'  # Google sharing variant
        ]
        # Check both with and without list marker
        if lower_line in standalone_skip or lower_line.lstrip('* ') in standalone_skip:
            continue
        
        # Skip lines that contain author bylines with names
        # Pattern: "By [Author Name](url)" or just author names after bylines
        if re.match(r'^by\s+\[.+\]\(.+\)', stripped, re.IGNORECASE):
            # This is a byline with link - skip it entirely
            continue
        
        # Skip lines that are just author names (when they appear standalone after byline)
        # This catches "Brian Welk" or "### Brian Welk" appearing on its own line
        if i > 0:
            prev_line = lines[i - 1].strip().lower()
            # If previous line was a byline link and this is a short line, it's likely the author name
            # Also check if it's a heading with just a name
            if ('author' in prev_line or 'by [' in prev_line) and len(stripped) < 50:
                continue
        
        # Skip headings that are just author names (e.g., "### Brian Welk")
        if re.match(r'^#{1,6}\s+[A-Z][a-z]+\s+[A-Z][a-z]+$', stripped):
            # This is likely an author name heading (FirstName LastName)
            continue
        
        # This duplicate "Related Stories" check is now handled above with better logic
        # Removed to avoid redundancy
        
        cleaned_lines.append(line)
    
    # Join lines and remove excessive blank lines
    cleaned_content = '\n'.join(cleaned_lines)
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
    
    return cleaned_content.strip()



async def _extract_with_playwright(url: str) -> Optional[str]:
    """
    Extract content using Playwright for JavaScript-heavy sites.
    Uses semantic HTML5 elements and common CMS patterns for robust extraction.
    
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
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            # For Substack, wait for specific content elements to load
            if is_substack:
                try:
                    await page.wait_for_selector('article, .post-content, .body', timeout=10000)
                    logger.info("Substack article content loaded")
                except:
                    logger.warning("Substack content selector not found, continuing anyway")
            
            # Wait for any lazy-loaded content
            await asyncio.sleep(3 if is_substack else 2)
            
            # Only remove obvious non-content elements (conservative approach)
            is_substack_js = 'true' if is_substack else 'false'
            await page.evaluate(f"""
                () => {{
                    const isSubstack = {is_substack_js};
                    
                    // Remove script and style tags only
                    document.querySelectorAll('script, style, noscript').forEach(el => el.remove());
                    
                    if (isSubstack) {{
                        // Conservative cleanup for Substack
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
                    }}
                }}
            """)
            
            # Try to find main content using semantic HTML5 and CMS patterns
            if is_substack:
                content_selectors = [
                    '.body.markup',
                    'article .body',
                    '.post-content',
                    'article',
                    '.available-content',
                    'main',
                ]
            else:
                # Prioritize semantic HTML5 elements and common CMS patterns
                content_selectors = [
                    # Semantic HTML5
                    'article[role="article"]',
                    'article',
                    'main[role="main"]',
                    'main',
                    '[role="main"]',
                    
                    # Common CMS patterns (WordPress, Medium, Ghost, etc.)
                    '.post-content', '.entry-content', '.article-content',
                    '.content-body', '.article-body', '.post-body',
                    
                    # IndieWire and similar news sites
                    '.article__body', '.story-body', '.news-article',
                    
                    # Squarespace
                    '.blog-item-content', '.sqs-block-content',
                    
                    # Generic fallbacks
                    '#content', '.content', '#main-content', '.main-content',
                    '#page', '.page-content'
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
            
            # If no selector worked, try to find the largest content container
            if not extracted_html or len(extracted_html) < MIN_CONTENT_LENGTH:
                logger.info("Semantic selectors failed, searching for largest content container")
                try:
                    # Use JavaScript to find the element with the most text content
                    # This works for sites with custom/obfuscated class names
                    extracted_html = await page.evaluate("""
                        () => {
                            // Find all divs and sections
                            const elements = Array.from(document.querySelectorAll('div, section'));
                            
                            // Filter out elements that are likely navigation/ads/footer
                            const filtered = elements.filter(el => {
                                const classes = el.className.toLowerCase();
                                const id = el.id.toLowerCase();
                                const combined = classes + ' ' + id;
                                
                                // Skip obvious non-content elements
                                if (combined.includes('nav') ||
                                    combined.includes('header') ||
                                    combined.includes('footer') ||
                                    combined.includes('sidebar') ||
                                    combined.includes('menu') ||
                                    combined.includes('ad-') ||
                                    combined.includes('cookie') ||
                                    combined.includes('consent')) {
                                    return false;
                                }
                                return true;
                            });
                            
                            // Find element with most paragraph content (better indicator of article text)
                            let maxScore = 0;
                            let bestElement = null;
                            
                            for (const el of filtered) {
                                const textLength = el.innerText?.length || 0;
                                const paragraphs = el.querySelectorAll('p').length;
                                
                                // Score based on text length and paragraph count
                                // Paragraphs are a strong indicator of article content
                                const score = textLength + (paragraphs * 200);
                                
                                if (score > maxScore && textLength > 500) {
                                    maxScore = score;
                                    bestElement = el;
                                }
                            }
                            
                            return bestElement ? bestElement.innerHTML : null;
                        }
                    """)
                    
                    if extracted_html and len(extracted_html) > MIN_CONTENT_LENGTH:
                        logger.info(f"Found content using largest container heuristic ({len(extracted_html)} chars)")
                except Exception as e:
                    logger.warning(f"Largest container heuristic failed: {str(e)}")
            
            # Last resort: get the full body
            if not extracted_html or len(extracted_html) < MIN_CONTENT_LENGTH:
                logger.info("Using full body content as final fallback")
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
            
            # Post-process to remove any remaining clutter
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


async def extract_content(url: str, extraction_type: str = "fast") -> tuple[Optional[str], str]:
    """
    Extract main content text from a URL using readability-lxml.
    For YouTube URLs, attempts to extract video transcript first.
    
    Args:
        url: The URL to extract content from
        extraction_type: "fast" (default) uses Readability with Playwright fallback,
                        "complete" skips Readability and goes directly to Playwright
        
    Returns:
        Tuple of (extracted text content or None if extraction fails, actual extraction method used)
        The extraction method will be one of: "fast", "complete", or the requested type if it failed
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
                return transcript, extraction_type
            else:
                logger.warning(f"✗ YouTube transcript API failed for {url}")
                logger.info(f"Attempting yt-dlp transcript fallback for video ID: {video_id}")
                
                # Step 2: Try yt-dlp transcript extraction (most reliable)
                ytdlp_transcript = get_transcript_from_ytdlp(video_id)
                
                if ytdlp_transcript:
                    logger.info(f"✓ Successfully extracted transcript from yt-dlp for {url} ({len(ytdlp_transcript)} characters)")
                    return ytdlp_transcript, extraction_type
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
                        return content, extraction_type
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
                            return content, extraction_type
                        else:
                            logger.error(f"✗ All YouTube extraction methods failed for {url}")
                            raise ExtractionBlockError(f"YouTube blocked all extraction methods for {url}")
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
                return markdown_content, "complete"
            else:
                logger.warning(f"Playwright failed to extract content from {url}")
                return None, extraction_type
        
        # For "fast" extraction type, use the cascade logic (Readability → Playwright fallback)
        # First attempt: Try with requests + readability
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse with readability
        doc = Document(response.text)
        html_content = doc.summary()
        
        # Check if we got enough content AND it's not just ad/redirect text
        if html_content and len(html_content) >= MIN_CONTENT_LENGTH:
            # Convert to markdown first to check content quality
            markdown_content = md(
                html_content,
                heading_style="ATX",
                strip=['script', 'style']
            )
            
            # Check for ad/redirect patterns that indicate bad extraction
            lower_content = markdown_content.lower()
            is_ad_content = (
                'you will be redirected' in lower_content or
                'redirecting' in lower_content or
                markdown_content.strip().startswith('Skip Ad') or
                (len(markdown_content) < 500 and 'advertisement' in lower_content)
            )
            
            if markdown_content and not is_ad_content:
                # Clean the content
                markdown_content = _clean_extracted_content(markdown_content)
                
                # Verify we still have substantial content after cleaning
                if len(markdown_content) >= 500:
                    logger.info(f"Successfully extracted {len(markdown_content)} characters from {url} using readability (fast mode)")
                    return markdown_content, "fast"
                else:
                    logger.warning(f"Readability content too short after cleaning ({len(markdown_content)} chars), trying Playwright")
            else:
                logger.warning(f"Readability extracted ad/redirect content from {url}, trying Playwright")
        else:
            logger.warning(f"Readability extracted insufficient content ({len(html_content) if html_content else 0} chars) from {url}, trying Playwright")
        
        # Second attempt: Use Playwright for JavaScript rendering or better content extraction
        markdown_content = await _extract_with_playwright(url)
        
        if markdown_content:
            logger.info(f"Successfully extracted {len(markdown_content)} characters from {url} using Playwright (fallback from fast)")
            return markdown_content, "complete"
        else:
            logger.warning(f"Playwright also failed to extract content from {url}")
            return None, extraction_type
            
    except requests.RequestException as e:
        error_msg = str(e)
        # For 403/401/Forbidden errors in fast mode, try Playwright before giving up
        # This allows the cascade to work: requests.get() → Playwright → complete mode → local
        if "403" in error_msg or "401" in error_msg or "Forbidden" in error_msg:
            logger.warning(f"Access blocked for {url} with requests.get(): {error_msg}")
            logger.info(f"Attempting Playwright extraction to bypass bot detection")
            
            # Try Playwright fallback
            markdown_content = await _extract_with_playwright(url)
            if markdown_content:
                logger.info(f"Successfully extracted {len(markdown_content)} characters from {url} using Playwright fallback after 403")
                return markdown_content, "complete"
            
            # Both requests.get() and Playwright failed with access errors
            # Now raise ExtractionBlockError to trigger cascade to complete mode
            logger.error(f"Both requests.get() and Playwright failed for {url} - access blocked")
            raise ExtractionBlockError(f"Server blocked access to {url}: {error_msg}")
        
        logger.error(f"Error fetching content from {url}: {error_msg}")
        # Try Playwright as a last resort for other request errors
        logger.info(f"Attempting Playwright extraction after request error")
        markdown_content = await _extract_with_playwright(url)
        if markdown_content:
            logger.info(f"Successfully extracted {len(markdown_content)} characters from {url} using Playwright fallback")
            return markdown_content, "complete"
        return None, extraction_type
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {str(e)}")
        return None, extraction_type


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
        logger.info(f"🎥 [YOUTUBE METADATA] Detected YouTube URL: {url}")
        video_id = extract_video_id(url)
        
        if video_id:
            logger.info(f"🎥 [YOUTUBE METADATA] Extracted video ID: {video_id}")
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
                    logger.info(f"🎥 [YOUTUBE METADATA] Channel name from yt-dlp: {youtube_metadata.get('channel_name')}")
                
                if transcript:
                    logger.info(f"🎥 [YOUTUBE METADATA] Successfully extracted YouTube transcript and metadata for {url}")
                    # If we have both transcript and metadata, use them
                    if youtube_metadata:
                        # Format source as "YouTube | Channel Name"
                        channel_name = youtube_metadata.get('channel_name', '')
                        source = f"YouTube | {channel_name}" if channel_name else "YouTube"
                        logger.info(f"🎥 [YOUTUBE METADATA] Formatted source field: '{source}'")
                        
                        return {
                        'text': transcript,
                        'title': youtube_metadata.get('title'),
                        'description': youtube_metadata.get('description'),
                        'image_url': youtube_metadata.get('thumbnail_url'),
                        'author': youtube_metadata.get('channel_name'),
                        'date': youtube_metadata.get('published_at'),
                        'source': source,
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
                        'source': 'YouTube',
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
                
                # Format source as "YouTube | Channel Name"
                channel_name = youtube_metadata.get('channel_name', '')
                source = f"YouTube | {channel_name}" if channel_name else "YouTube"
                logger.info(f"🎥 [YOUTUBE METADATA] Formatted source field (no transcript): '{source}'")
                
                return {
                    'text': content,
                    'title': youtube_metadata.get('title'),
                    'description': youtube_metadata.get('description'),
                    'image_url': youtube_metadata.get('thumbnail_url'),
                    'author': youtube_metadata.get('channel_name'),
                    'date': youtube_metadata.get('published_at'),
                    'source': source,
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
                    'source': 'YouTube',
                    'url': url
                }
        else:
            logger.error(f"Failed to extract video ID from YouTube URL: {url}")
            return {'text': None, 'source': 'YouTube'}
    
    # For non-YouTube URLs, use the existing extraction logic
    try:
        # For "complete" extraction type, skip Readability and go directly to Playwright
        if extraction_type == "complete":
            logger.info(f"Using complete extraction (Playwright) for {url}")
            markdown_text = await _extract_with_playwright(url)
            
            if not markdown_text:
                return {'text': None, 'source': extract_source_from_url(url)}
            
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
                'source': extract_source_from_url(url),
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
                'source': extract_source_from_url(url),
                'url': url
            }
        
        # Insufficient content, try Playwright
        logger.warning(f"Readability extracted insufficient content from {url}, trying Playwright")
        markdown_text = await _extract_with_playwright(url)
        
        if not markdown_text:
            return {'text': None, 'source': extract_source_from_url(url)}
        
        # For title, we still need to parse the original response
        doc = Document(response.text)
        title = doc.title()
        
        logger.info(f"Extracted content with metadata from {url} using Playwright")
        return {
            'text': markdown_text,
            'title': title,
            'author': None,
            'date': None,
            'source': extract_source_from_url(url),
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
                'source': extract_source_from_url(url),
                'url': url
            }
        return {'text': None, 'source': extract_source_from_url(url)}
    except Exception as e:
        logger.error(f"Error extracting content with metadata from {url}: {str(e)}")
        return {'text': None, 'source': extract_source_from_url(url)}