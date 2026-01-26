"""
Debug script to test local extraction for Substack URL.
This will help identify why only title and footer are being captured.
"""
import asyncio
import logging
from app.services.extraction import extract_content, _extract_with_playwright

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TEST_URL = "https://creatoreconomy.so/p/curious-beginners-guide-to-ai-evaluations"

async def test_extraction():
    """Test extraction with different methods and log detailed output."""
    
    print("\n" + "="*80)
    print("TESTING SUBSTACK EXTRACTION")
    print("="*80)
    print(f"URL: {TEST_URL}\n")
    
    # Test 1: Fast mode (Readability first, then Playwright fallback)
    print("\n--- TEST 1: Fast Mode (Readability + Playwright fallback) ---")
    try:
        content_fast, method_fast = await extract_content(TEST_URL, extraction_type="fast")
        if content_fast:
            print(f"✓ Fast mode succeeded using method: {method_fast}")
            print(f"  Content length: {len(content_fast)} characters")
            print(f"  First 500 chars:\n{content_fast[:500]}")
            print(f"  Last 500 chars:\n{content_fast[-500:]}")
        else:
            print(f"✗ Fast mode failed")
    except Exception as e:
        print(f"✗ Fast mode error: {str(e)}")
    
    # Test 2: Complete mode (Playwright only)
    print("\n--- TEST 2: Complete Mode (Playwright only) ---")
    try:
        content_complete, method_complete = await extract_content(TEST_URL, extraction_type="complete")
        if content_complete:
            print(f"✓ Complete mode succeeded using method: {method_complete}")
            print(f"  Content length: {len(content_complete)} characters")
            print(f"  First 500 chars:\n{content_complete[:500]}")
            print(f"  Last 500 chars:\n{content_complete[-500:]}")
        else:
            print(f"✗ Complete mode failed")
    except Exception as e:
        print(f"✗ Complete mode error: {str(e)}")
    
    # Test 3: Direct Playwright extraction with detailed logging
    print("\n--- TEST 3: Direct Playwright Extraction (with debug output) ---")
    try:
        content_playwright = await _extract_with_playwright(TEST_URL)
        if content_playwright:
            print(f"✓ Playwright extraction succeeded")
            print(f"  Content length: {len(content_playwright)} characters")
            
            # Check for specific content markers
            has_title = "Curious Beginner's Guide" in content_playwright
            has_author = "Peter Yang" in content_playwright
            has_article_content = len(content_playwright) > 2000
            
            print(f"\n  Content Analysis:")
            print(f"    - Has title: {has_title}")
            print(f"    - Has author: {has_author}")
            print(f"    - Has substantial content (>2000 chars): {has_article_content}")
            
            # Look for footer indicators
            has_footer = any(marker in content_playwright.lower() for marker in [
                "privacy", "terms", "collection notice", "substack"
            ])
            print(f"    - Contains footer elements: {has_footer}")
            
            # Count paragraphs (rough estimate)
            paragraph_count = content_playwright.count('\n\n')
            print(f"    - Estimated paragraphs: {paragraph_count}")
            
            print(f"\n  First 1000 chars:\n{content_playwright[:1000]}")
            print(f"\n  Last 1000 chars:\n{content_playwright[-1000:]}")
            
            # Save full content to file for inspection
            with open('debug_local_extraction_output.md', 'w') as f:
                f.write(content_playwright)
            print(f"\n  ✓ Full content saved to: debug_local_extraction_output.md")
            
        else:
            print(f"✗ Playwright extraction returned None")
    except Exception as e:
        print(f"✗ Playwright extraction error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("EXTRACTION TEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_extraction())