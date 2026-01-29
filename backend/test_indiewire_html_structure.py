"""
Debug script to examine the HTML structure of IndieWire.
"""
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

TEST_URL = "https://www.indiewire.com/news/breaking-news/san-francisco-castro-theatre-reopen-a24-pillion-1235176128/"

async def debug_html_structure():
    """Examine the HTML structure to find content containers."""
    
    print("=" * 80)
    print("EXAMINING HTML STRUCTURE")
    print("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        await page.goto(TEST_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        
        # Get the HTML
        html = await page.content()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for divs with class containing "content", "article", "post", "story"
        print("\nSearching for content containers...")
        print("-" * 80)
        
        content_keywords = ['content', 'article', 'post', 'story', 'body', 'text']
        
        for keyword in content_keywords:
            elements = soup.find_all(class_=lambda x: x and keyword in x.lower())
            if elements:
                print(f"\nElements with '{keyword}' in class:")
                for i, elem in enumerate(elements[:5]):  # Show first 5
                    classes = ' '.join(elem.get('class', []))
                    text_preview = elem.get_text()[:100].replace('\n', ' ')
                    print(f"  {i+1}. <{elem.name} class='{classes}'>")
                    print(f"     Text preview: {text_preview}...")
        
        # Look for divs with id containing similar keywords
        print("\n\nSearching for elements by ID...")
        print("-" * 80)
        
        for keyword in content_keywords:
            elements = soup.find_all(id=lambda x: x and keyword in x.lower())
            if elements:
                print(f"\nElements with '{keyword}' in id:")
                for elem in elements:
                    text_preview = elem.get_text()[:100].replace('\n', ' ')
                    print(f"  <{elem.name} id='{elem.get('id')}'>")
                    print(f"  Text preview: {text_preview}...")
        
        # Find the longest text blocks
        print("\n\nFinding elements with most text content...")
        print("-" * 80)
        
        all_divs = soup.find_all(['div', 'section'])
        text_lengths = [(div, len(div.get_text(strip=True))) for div in all_divs]
        text_lengths.sort(key=lambda x: x[1], reverse=True)
        
        print("\nTop 10 elements by text length:")
        for i, (elem, length) in enumerate(text_lengths[:10]):
            classes = ' '.join(elem.get('class', []))
            elem_id = elem.get('id', '')
            print(f"\n{i+1}. <{elem.name}> - {length} chars")
            if classes:
                print(f"   class: {classes}")
            if elem_id:
                print(f"   id: {elem_id}")
            text_preview = elem.get_text()[:150].replace('\n', ' ').strip()
            print(f"   Preview: {text_preview}...")
        
        await browser.close()
        
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(debug_html_structure())