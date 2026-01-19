"""
Debug script to see what selectors are available on the Substack page.
"""
import asyncio
from playwright.async_api import async_playwright

async def debug_selectors():
    url = "https://creatoreconomy.so/p/curious-beginners-guide-to-ai-evaluations"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        
        print(f"Loading {url}...")
        await page.goto(url, wait_until="domcontentloaded", timeout=90000)
        
        # Wait for content
        await asyncio.sleep(5)
        
        print("\n" + "="*80)
        print("CHECKING SELECTORS:")
        print("="*80)
        
        selectors_to_check = [
            '.body.markup',
            'article .body',
            '.post-content',
            'article',
            '.available-content',
            'main',
            '.body',
            '[class*="body"]',
            '[class*="post"]',
            '[class*="article"]',
            '.post',
            '#main',
        ]
        
        for selector in selectors_to_check:
            try:
                element = await page.query_selector(selector)
                if element:
                    html = await element.inner_html()
                    text = await element.inner_text()
                    print(f"\n✅ '{selector}' found:")
                    print(f"   HTML length: {len(html)} chars")
                    print(f"   Text length: {len(text)} chars")
                    print(f"   First 200 chars of text: {text[:200]}")
                else:
                    print(f"\n❌ '{selector}' not found")
            except Exception as e:
                print(f"\n❌ '{selector}' error: {e}")
        
        # Get all elements with class containing 'body' or 'post' or 'article'
        print("\n" + "="*80)
        print("ALL ELEMENTS WITH 'body', 'post', or 'article' in class:")
        print("="*80)
        
        elements = await page.evaluate("""
            () => {
                const results = [];
                document.querySelectorAll('*').forEach(el => {
                    const className = el.className;
                    if (typeof className === 'string' && 
                        (className.includes('body') || 
                         className.includes('post') || 
                         className.includes('article'))) {
                        const text = el.innerText || '';
                        results.push({
                            tag: el.tagName,
                            class: className,
                            textLength: text.length,
                            preview: text.substring(0, 100)
                        });
                    }
                });
                return results;
            }
        """)
        
        for el in elements[:20]:  # Show first 20
            print(f"\n{el['tag']}.{el['class']}")
            print(f"  Text length: {el['textLength']} chars")
            print(f"  Preview: {el['preview']}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_selectors())