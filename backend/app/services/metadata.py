"""
Metadata extraction service for fetching page metadata from URLs.
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
import logging

logger = logging.getLogger(__name__)

# User agent to avoid being blocked by some sites
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_metadata(url: str, timeout: int = 10) -> Dict[str, Optional[str]]:
    """
    Fetch metadata (title, description, image, favicon) from a URL.
    
    Args:
        url: The URL to fetch metadata from
        timeout: Request timeout in seconds
        
    Returns:
        Dictionary with keys: title, description, image_url, favicon_url
        Returns None values for fields that couldn't be extracted
    """
    metadata = {
        'title': None,
        'description': None,
        'image_url': None,
        'favicon_url': None
    }
    
    try:
        # Fetch the page
        response = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        metadata['title'] = _extract_title(soup)
        
        # Extract description
        metadata['description'] = _extract_description(soup)
        
        # Extract image
        metadata['image_url'] = _extract_image(soup, url)
        
        # Extract favicon
        metadata['favicon_url'] = _extract_favicon(soup, url)
        
        logger.info(f"Successfully extracted metadata from {url}")
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout while fetching metadata from {url}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching metadata from {url}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error extracting metadata from {url}: {str(e)}")
    
    return metadata


def _extract_title(soup: BeautifulSoup) -> Optional[str]:
    """Extract page title from various meta tags and title element."""
    # Try Open Graph title
    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        return og_title['content'].strip()
    
    # Try Twitter title
    twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
    if twitter_title and twitter_title.get('content'):
        return twitter_title['content'].strip()
    
    # Try regular title tag
    title_tag = soup.find('title')
    if title_tag and title_tag.string:
        return title_tag.string.strip()
    
    return None


def _extract_description(soup: BeautifulSoup) -> Optional[str]:
    """Extract page description from various meta tags."""
    # Try Open Graph description
    og_desc = soup.find('meta', property='og:description')
    if og_desc and og_desc.get('content'):
        return og_desc['content'].strip()
    
    # Try Twitter description
    twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
    if twitter_desc and twitter_desc.get('content'):
        return twitter_desc['content'].strip()
    
    # Try standard meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        return meta_desc['content'].strip()
    
    return None


def _extract_image(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """Extract main image URL from various meta tags."""
    # Try Open Graph image
    og_image = soup.find('meta', property='og:image')
    if og_image and og_image.get('content'):
        return _make_absolute_url(og_image['content'], base_url)
    
    # Try Twitter image
    twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
    if twitter_image and twitter_image.get('content'):
        return _make_absolute_url(twitter_image['content'], base_url)
    
    return None


def _extract_favicon(soup: BeautifulSoup, base_url: str) -> Optional[str]:
    """Extract favicon URL from link tags."""
    # Try various favicon link types
    favicon_rels = ['icon', 'shortcut icon', 'apple-touch-icon']
    
    for rel in favicon_rels:
        favicon = soup.find('link', rel=lambda r: r and rel in r.lower())
        if favicon and favicon.get('href'):
            return _make_absolute_url(favicon['href'], base_url)
    
    # Fallback to /favicon.ico
    from urllib.parse import urljoin
    return urljoin(base_url, '/favicon.ico')


def _make_absolute_url(url: str, base_url: str) -> str:
    """Convert relative URL to absolute URL."""
    from urllib.parse import urljoin, urlparse
    
    # If already absolute, return as-is
    if urlparse(url).netloc:
        return url
    
    # Make absolute using base URL
    return urljoin(base_url, url)