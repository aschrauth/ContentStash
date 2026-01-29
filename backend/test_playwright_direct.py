"""
Direct test of Playwright extraction with the new heuristic.
"""
import asyncio
from playwright.async_api import async_playwright

TEST_URL = "https://www.indiewire.com/news/breaking-news/san-francisco-castro-theatre-reopen-a24-pillion-1235176128/"

async def test_playwright_heuristic():
    """Test the largest container heuristic."""
    
    print("=" * 80)
    print("TESTING PLAYWRIGHT HEURISTIC")
    print("=" * 80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        print("\nNavigating to page...")
        await page.goto(TEST_URL, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)
        
        print("Running largest container heuristic...")
        result = await page.evaluate("""
            () => {
                // Find all divs and sections
                const elements = Array.from(document.querySelectorAll('div, section'));
                
                console.log('Total elements found:', elements.length);
                
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
                
                console.log('Filtered elements:', filtered.length);
                
                // Find element with most text content
                let maxLength = 0;
                let bestElement = null;
                let bestClass = '';
                let bestId = '';
                
                for (const el of filtered) {
                    const textLength = el.innerText?.length || 0;
                    if (textLength > maxLength && textLength > 1000) {
                        maxLength = textLength;
                        bestElement = el;
                        bestClass = el.className;
                        bestId = el.id;
                    }
                }
                
                console.log('Best element text length:', maxLength);
                console.log('Best element class:', bestClass);
                console.log('Best element id:', bestId);
                
                if (bestElement) {
                    return {
                        html: bestElement.innerHTML,
                        textLength: maxLength,
                        className: bestClass,
                        id: bestId
                    };
                }
                
                return null;
            }
        """)
        
        if result:
            print(f"\n✓ Found content container!")
            print(f"  - Text length: {result['textLength']} chars")
            print(f"  - HTML length: {len(result['html'])} chars")
            print(f"  - Class: {result['className']}")
            print(f"  - ID: {result['id']}")
            print(f"\nFirst 500 chars of HTML:")
            print("-" * 80)
            print(result['html'][:500])
            print("-" * 80)
        else:
            print("\n❌ No content container found")
        
        await browser.close()
        
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_playwright_heuristic())