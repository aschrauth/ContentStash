"""
Test script to verify Substack article extraction fix.
Tests the problematic URL: https://creatoreconomy.so/p/curious-beginners-guide-to-ai-evaluations
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.extraction import extract_content

async def test_substack_extraction():
    """Test extraction of the problematic Substack article."""
    
    test_url = "https://creatoreconomy.so/p/curious-beginners-guide-to-ai-evaluations"
    
    print(f"Testing Substack extraction for: {test_url}")
    print("=" * 80)
    
    # Test with "fast" extraction type (will use Playwright fallback)
    print("\n1. Testing with 'fast' extraction type (Readability → Playwright fallback)...")
    content_fast = await extract_content(test_url, extraction_type="fast")
    
    if content_fast:
        print(f"✅ Successfully extracted content (fast mode)")
        print(f"   Content length: {len(content_fast)} characters")
        print(f"\n   First 500 characters:")
        print(f"   {content_fast[:500]}")
        print(f"\n   Last 500 characters:")
        print(f"   {content_fast[-500:]}")
    else:
        print("❌ Failed to extract content (fast mode)")
    
    print("\n" + "=" * 80)
    
    # Test with "complete" extraction type (direct Playwright)
    print("\n2. Testing with 'complete' extraction type (direct Playwright)...")
    content_complete = await extract_content(test_url, extraction_type="complete")
    
    if content_complete:
        print(f"✅ Successfully extracted content (complete mode)")
        print(f"   Content length: {len(content_complete)} characters")
        print(f"\n   First 500 characters:")
        print(f"   {content_complete[:500]}")
        print(f"\n   Last 500 characters:")
        print(f"   {content_complete[-500:]}")
    else:
        print("❌ Failed to extract content (complete mode)")
    
    print("\n" + "=" * 80)
    
    # Summary
    print("\n📊 SUMMARY:")
    print(f"   Fast mode: {'✅ SUCCESS' if content_fast else '❌ FAILED'}")
    print(f"   Complete mode: {'✅ SUCCESS' if content_complete else '❌ FAILED'}")
    
    if content_fast or content_complete:
        print("\n✅ At least one extraction method succeeded!")
        
        # Check if we got meaningful content (not just footer)
        test_content = content_fast or content_complete
        if len(test_content) > 2000:  # Reasonable article length
            print("✅ Content length looks good (>2000 chars)")
        else:
            print("⚠️  Content seems short, may only be footer/header")
        
        # Check for common footer-only indicators
        if "archived" in test_content.lower() and len(test_content) < 500:
            print("⚠️  Content appears to be just an 'archived' notice")
        else:
            print("✅ Content does not appear to be just a footer")
    else:
        print("\n❌ Both extraction methods failed")
    
    return content_fast or content_complete

if __name__ == "__main__":
    result = asyncio.run(test_substack_extraction())
    sys.exit(0 if result else 1)