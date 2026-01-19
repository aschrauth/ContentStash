"""
Test to verify Playwright extraction works correctly for Substack articles.
Compares Fast mode (Readability) vs Complete mode (Playwright) extraction.
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.extraction import extract_content

async def test_substack_extraction():
    """Test extraction of a Substack article in both modes."""
    url = "https://creatoreconomy.so/p/curious-beginners-guide-to-ai-evaluations"
    
    print(f"\n{'='*80}")
    print(f"Testing Substack extraction for:")
    print(f"{url}")
    print(f"{'='*80}\n")
    
    # Test Fast mode (Readability)
    print("Testing FAST mode (Readability)...")
    fast_content = await extract_content(url, extraction_type="fast")
    
    if fast_content:
        print(f"✅ Fast mode extracted {len(fast_content)} characters")
        print(f"\nFirst 500 chars:\n{fast_content[:500]}")
        print(f"\nLast 500 chars:\n{fast_content[-500:]}")
    else:
        print("❌ Fast mode failed to extract content")
    
    print(f"\n{'-'*80}\n")
    
    # Test Complete mode (Playwright)
    print("Testing COMPLETE mode (Playwright)...")
    complete_content = await extract_content(url, extraction_type="complete")
    
    if complete_content:
        print(f"✅ Complete mode extracted {len(complete_content)} characters")
        print(f"\nFirst 500 chars:\n{complete_content[:500]}")
        print(f"\nLast 500 chars:\n{complete_content[-500:]}")
    else:
        print("❌ Complete mode failed to extract content")
    
    print(f"\n{'='*80}")
    print("COMPARISON:")
    print(f"{'='*80}")
    
    if fast_content and complete_content:
        fast_len = len(fast_content)
        complete_len = len(complete_content)
        
        print(f"Fast mode:     {fast_len:,} characters")
        print(f"Complete mode: {complete_len:,} characters")
        print(f"Difference:    {abs(fast_len - complete_len):,} characters")
        
        # Complete mode should extract at least as much as Fast mode
        if complete_len >= fast_len * 0.8:  # Allow 20% variance
            print(f"\n✅ PASS: Complete mode extracted sufficient content")
        else:
            print(f"\n❌ FAIL: Complete mode extracted significantly less content")
            print(f"   Expected at least {fast_len * 0.8:,.0f} chars, got {complete_len:,}")
        
        # Both should have substantial content (>2000 chars for this article)
        if complete_len > 2000:
            print(f"✅ PASS: Complete mode has substantial content (>{2000:,} chars)")
        else:
            print(f"❌ FAIL: Complete mode has insufficient content (<{2000:,} chars)")
            
    else:
        print("❌ FAIL: One or both extraction modes failed")
    
    print(f"{'='*80}\n")

if __name__ == "__main__":
    asyncio.run(test_substack_extraction())