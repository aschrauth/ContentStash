"""
Debug Playwright extraction to see what HTML is being fetched.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from playwright.sync_api import sync_playwright
from readability import Document
from markdownify import markdownify as md
import time

test_url = "https://www.bitesizelearning.co.uk/resources/scarf-model-david-rock-explained"

print(f"Testing Playwright extraction for: {test_url}\n")
print("=" * 80)

try:
    with sync_playwright() as p:
        print("\n1. Launching browser...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("2. Navigating to page...")
        page.goto(test_url, wait_until="networkidle", timeout=30000)
        
        print("3. Waiting for content to load...")
        time.sleep(3)
        
        print("4. Getting page content...")
        html_content = page.content()
        print(f"   ✓ Got {len(html_content):,} characters of HTML")
        
        # Save the rendered HTML
        with open('debug_playwright_rendered.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        print("   ✓ Saved to debug_playwright_rendered.html")
        
        browser.close()
        
        print("\n5. Parsing with readability...")
        doc = Document(html_content)
        extracted_html = doc.summary()
        print(f"   ✓ Readability extracted {len(extracted_html):,} characters")
        
        # Save readability output
        with open('debug_playwright_readability.html', 'w', encoding='utf-8') as f:
            f.write(extracted_html)
        print("   ✓ Saved to debug_playwright_readability.html")
        
        print("\n6. Converting to markdown...")
        markdown = md(extracted_html, heading_style="ATX", strip=['script', 'style'])
        print(f"   ✓ Converted to {len(markdown):,} characters of markdown")
        
        # Save markdown
        with open('debug_playwright_markdown.md', 'w', encoding='utf-8') as f:
            f.write(markdown)
        print("   ✓ Saved to debug_playwright_markdown.md")
        
        print("\n7. Content preview:")
        print("-" * 80)
        print(markdown[:1000])
        print("-" * 80)
        
        # Check for SCARF elements
        scarf_elements = ['Status', 'Certainty', 'Autonomy', 'Relatedness', 'Fairness']
        found = [elem for elem in scarf_elements if elem in markdown]
        print(f"\n✓ Found {len(found)}/{len(scarf_elements)} SCARF elements: {', '.join(found)}")
        
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)