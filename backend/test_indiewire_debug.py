"""
Debug script to see what Playwright extracts from IndieWire.
"""
import asyncio
from playwright.async_api import async_playwright

TEST_URL = "https://www.indiewire.com/news/breaking-news/san-francisco-castro-theatre-reopen-a24-pillion-1235176128/"

async def debug_playwright():
    """Debug what Playwright sees on the page."""
    
    print("=" * 80)
    print("DEBUGGING PLAYWRIGHT EXTRACTION")
    print("=" * 80)
    print(f"\nTest URL: {TEST_URL}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Set realistic user agent
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        print("Navigating to page...")
        await page.goto(TEST_URL, wait_until="domcontentloaded", timeout=30000)
        
        print("Waiting for content to load...")
        await asyncio.sleep(3)
        
        # Try different selectors
        selectors_to_try = [
            'article[role="article"]',
            'article',
            'main[role="main"]',
            'main',
            '[role="main"]',
            '.post-content',
            '.entry-content',
            '.article-content',
            '.article__body',
            '.story-body',
            '.news-article',
            'body'
        ]
        
        print("\nTrying different selectors:")
        print("-" * 80)
        
        for selector in selectors_to_try:
            try:
                element = await page.query_selector(selector)
                if element:
                    html = await element.inner_html()
                    text = await element.inner_text()
                    print(f"\n✓ Selector '{selector}' found:")
                    print(f"  - HTML length: {len(html)} chars")
                    print(f"  - Text length: {len(text)} chars")
                    print(f"  - First 200 chars of text: {text[:200]}")
                else:
                    print(f"✗ Selector '{selector}' not found")
            except Exception as e:
                print(f"✗ Selector '{selector}' error: {str(e)}")
        
        # Get page title
        title = await page.title()
        print(f"\n\nPage title: {title}")
        
        # Check for specific elements
        print("\n\nChecking for specific elements:")
        print("-" * 80)
        
        # Check for article tags
        articles = await page.query_selector_all('article')
        print(f"Number of <article> tags: {len(articles)}")
        
        # Check for main tags
        mains = await page.query_selector_all('main')
        print(f"Number of <main> tags: {len(mains)}")
        
        # Check body content
        body = await page.query_selector('body')
        if body:
            body_text = await body.inner_text()
            print(f"\nBody text length: {len(body_text)} chars")
            print(f"First 500 chars of body:\n{body_text[:500]}")
        
        await browser.close()
        
        print("\n" + "=" * 80)
        print("DEBUG COMPLETE")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(debug_playwright())