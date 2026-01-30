
import asyncio
import sys
import os
from playwright.async_api import async_playwright

async def investigate(url, output_dir="debug_output"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    async with async_playwright() as p:
        print(f"🚀 Starting investigation of: {url}")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()
        
        try:
            # Navigate
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print(f"✅ Loaded: {page.title()}")
            
            # Initial Screenshot
            await page.screenshot(path=f"{output_dir}/initial.png")
            
            # Expansion Logic
            expand_selectors = ['.readMoreBtn', '.read-more-btn', '.expand-btn', '.show-more', '.view-more', 'button']
            expand_texts = ['expand', 'read more', 'continue reading', 'show more', 'view more']
            
            buttons = await page.query_selector_all('button, div, a')
            clicked = 0
            for btn in buttons:
                try:
                    text = (await btn.inner_text()).lower()
                    if any(t in text for t in expand_texts):
                        if await btn.is_visible():
                            print(f"🖱️ Clicking expansion element with text: '{text[:30]}...'")
                            await btn.click()
                            clicked += 1
                            await asyncio.sleep(1) # Wait for expansion
                except:
                    continue
            
            if clicked > 0:
                print(f"✨ Expanded {clicked} elements.")
                await page.screenshot(path=f"{output_dir}/expanded.png")
            
            # Capture DOM
            content = await page.content()
            with open(f"{output_dir}/dom.html", "w") as f:
                f.write(content)
            
            print(f"📊 DOM and screenshots saved to {output_dir}/")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            # Take error screenshot
            await page.screenshot(path=f"{output_dir}/error.png")
        finally:
            await browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_url.py <URL>")
        sys.exit(1)
    url = sys.argv[1]
    asyncio.run(investigate(url))
