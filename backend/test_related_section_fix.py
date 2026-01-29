"""
Test script to verify the related section detection fix.
Tests that:
1. Related sections in the middle are removed
2. Article content after related sections is preserved
3. Final "Read More" sections are still removed
"""
import asyncio
from app.services.extraction import extract_content

async def test_indiewire_extraction():
    """Test extraction with the IndieWire article that has a mid-article related section."""
    url = 'https://www.indiewire.com/news/breaking-news/san-francisco-castro-theatre-reopen-a24-pillion-1235176128/'
    
    print(f"Testing extraction for: {url}\n")
    print("=" * 80)
    
    # Extract content
    content, method = await extract_content(url, extraction_type="complete")
    
    if not content:
        print("❌ FAILED: No content extracted")
        return False
    
    print(f"✓ Extracted {len(content)} characters using {method} method\n")
    
    # Check for key indicators
    checks = {
        "Has substantial content": len(content) > 2000,
        "Contains article beginning": "Castro Theatre" in content or "San Francisco" in content,
        "Contains article middle": "A24" in content or "Pillion" in content,
        "Contains article end": "theater" in content.lower() or "venue" in content.lower(),
        "No 'Related Stories' heading": "## Related Stories" not in content and "### Related Stories" not in content,
        "No 'Read More' section": "## Read More" not in content and "### Read More" not in content,
    }
    
    print("Content checks:")
    print("-" * 80)
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "❌"
        print(f"{status} {check}: {passed}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 80)
    print("\nFirst 500 characters of extracted content:")
    print("-" * 80)
    print(content[:500])
    
    print("\n" + "=" * 80)
    print("\nLast 500 characters of extracted content:")
    print("-" * 80)
    print(content[-500:])
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✓ ALL CHECKS PASSED")
    else:
        print("❌ SOME CHECKS FAILED")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(test_indiewire_extraction())
    exit(0 if success else 1)