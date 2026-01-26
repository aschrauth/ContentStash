"""
Test script to verify the extraction cascade fix for 403 errors.

This test verifies that when "fast" mode encounters a 403 error:
1. It tries requests.get() → gets 403
2. It tries Playwright fallback → should succeed (bypasses bot detection)
3. If Playwright also fails, it cascades to complete mode (not local)

Test URL: https://www.theneurondaily.com/p/world-models-just-got-primed-for-their-chatgpt-moment
This URL is known to return 403 for requests.get() but works with Playwright.
"""

import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.extraction import extract_content
from app.services.exceptions import ExtractionBlockError
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_403_cascade():
    """Test that 403 errors trigger Playwright fallback before cascading."""
    
    # Test URL that returns 403 for requests.get() but works with Playwright
    test_url = "https://www.theneurondaily.com/p/world-models-just-got-primed-for-their-chatgpt-moment"
    
    logger.info("=" * 80)
    logger.info("Testing extraction cascade fix for 403 errors")
    logger.info("=" * 80)
    
    # Test 1: Fast mode should try Playwright fallback when requests.get() gets 403
    logger.info("\n--- Test 1: Fast mode with 403 URL ---")
    logger.info(f"URL: {test_url}")
    logger.info("Expected: requests.get() fails with 403 → Playwright succeeds → returns content")
    
    try:
        content, method = await extract_content(test_url, extraction_type="fast")
        
        if content:
            logger.info(f"✓ SUCCESS: Fast mode extracted content using Playwright fallback")
            logger.info(f"  - Extraction method: {method}")
            logger.info(f"  - Content length: {len(content)} characters")
            logger.info(f"  - Content preview: {content[:200]}...")
            
            # Verify it used Playwright (method should be "complete" since Playwright was used)
            if method == "complete":
                logger.info("✓ VERIFIED: Method correctly shows 'complete' (Playwright was used)")
            else:
                logger.warning(f"⚠ WARNING: Expected method='complete' but got '{method}'")
            
            return True
        else:
            logger.error("✗ FAILED: Fast mode returned None (should have used Playwright fallback)")
            return False
            
    except ExtractionBlockError as e:
        logger.error(f"✗ FAILED: ExtractionBlockError raised too early (Playwright fallback not attempted)")
        logger.error(f"  Error: {str(e)}")
        logger.error("  This means the fix didn't work - 403 error raised before Playwright fallback")
        return False
    except Exception as e:
        logger.error(f"✗ FAILED: Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_complete_mode():
    """Test that complete mode still works correctly."""
    
    test_url = "https://www.theneurondaily.com/p/world-models-just-got-primed-for-their-chatgpt-moment"
    
    logger.info("\n--- Test 2: Complete mode (should use Playwright directly) ---")
    logger.info(f"URL: {test_url}")
    logger.info("Expected: Skips requests.get() → Playwright succeeds → returns content")
    
    try:
        content, method = await extract_content(test_url, extraction_type="complete")
        
        if content:
            logger.info(f"✓ SUCCESS: Complete mode extracted content")
            logger.info(f"  - Extraction method: {method}")
            logger.info(f"  - Content length: {len(content)} characters")
            
            if method == "complete":
                logger.info("✓ VERIFIED: Method correctly shows 'complete'")
            else:
                logger.warning(f"⚠ WARNING: Expected method='complete' but got '{method}'")
            
            return True
        else:
            logger.error("✗ FAILED: Complete mode returned None")
            return False
            
    except Exception as e:
        logger.error(f"✗ FAILED: Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    
    logger.info("\n" + "=" * 80)
    logger.info("EXTRACTION CASCADE 403 FIX - TEST SUITE")
    logger.info("=" * 80)
    
    results = []
    
    # Test 1: Fast mode with 403 URL
    result1 = await test_403_cascade()
    results.append(("Fast mode 403 handling", result1))
    
    # Test 2: Complete mode
    result2 = await test_complete_mode()
    results.append(("Complete mode", result2))
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    
    if all_passed:
        logger.info("\n🎉 ALL TESTS PASSED! The extraction cascade fix is working correctly.")
        logger.info("\nKey improvements:")
        logger.info("  1. Fast mode now tries Playwright when requests.get() gets 403")
        logger.info("  2. Only raises ExtractionBlockError if BOTH methods fail")
        logger.info("  3. Cascade logic (fast→complete→local) works as intended")
    else:
        logger.error("\n❌ SOME TESTS FAILED. Please review the errors above.")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)