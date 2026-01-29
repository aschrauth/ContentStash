"""
Test script to verify extraction improvements for all three methods.
Tests with the IndieWire article example.
"""
import asyncio
import sys
from app.services.extraction import extract_content, extract_content_with_metadata

# IndieWire test URL
TEST_URL = "https://www.indiewire.com/news/breaking-news/san-francisco-castro-theatre-reopen-a24-pillion-1235176128/"

async def test_extraction_methods():
    """Test all three extraction methods with the IndieWire article."""
    
    print("=" * 80)
    print("TESTING EXTRACTION IMPROVEMENTS")
    print("=" * 80)
    print(f"\nTest URL: {TEST_URL}\n")
    
    # Test 1: Fast extraction
    print("\n" + "=" * 80)
    print("TEST 1: FAST EXTRACTION (Readability with Playwright fallback)")
    print("=" * 80)
    try:
        content, method = await extract_content(TEST_URL, extraction_type="fast")
        if content:
            print(f"✓ Success! Method used: {method}")
            print(f"✓ Content length: {len(content)} characters")
            print(f"\nFirst 500 characters:")
            print("-" * 80)
            print(content[:500])
            print("-" * 80)
            
            # Check for common issues
            issues = []
            lower_content = content.lower()
            if 'you will be redirected' in lower_content:
                issues.append("❌ Contains redirect message")
            if 'skip ad' in lower_content:
                issues.append("❌ Contains ad text")
            if 'privacy policy' in lower_content:
                issues.append("⚠️  Contains privacy policy")
            if 'cookie policy' in lower_content:
                issues.append("⚠️  Contains cookie policy")
            if 'share' in lower_content and 'facebook' in lower_content:
                issues.append("⚠️  Contains sharing buttons")
            
            if issues:
                print("\nIssues detected:")
                for issue in issues:
                    print(f"  {issue}")
            else:
                print("\n✓ No common clutter patterns detected!")
        else:
            print("❌ Failed to extract content")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Test 2: Complete extraction
    print("\n" + "=" * 80)
    print("TEST 2: COMPLETE EXTRACTION (Playwright only)")
    print("=" * 80)
    try:
        content, method = await extract_content(TEST_URL, extraction_type="complete")
        if content:
            print(f"✓ Success! Method used: {method}")
            print(f"✓ Content length: {len(content)} characters")
            print(f"\nFirst 500 characters:")
            print("-" * 80)
            print(content[:500])
            print("-" * 80)
            
            # Check for common issues
            issues = []
            lower_content = content.lower()
            if 'you will be redirected' in lower_content:
                issues.append("❌ Contains redirect message")
            if 'skip ad' in lower_content:
                issues.append("❌ Contains ad text")
            if 'privacy policy' in lower_content:
                issues.append("⚠️  Contains privacy policy")
            if 'cookie policy' in lower_content:
                issues.append("⚠️  Contains cookie policy")
            if 'share' in lower_content and 'facebook' in lower_content:
                issues.append("⚠️  Contains sharing buttons")
            
            if issues:
                print("\nIssues detected:")
                for issue in issues:
                    print(f"  {issue}")
            else:
                print("\n✓ No common clutter patterns detected!")
        else:
            print("❌ Failed to extract content")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Test 3: Extract with metadata
    print("\n" + "=" * 80)
    print("TEST 3: EXTRACT WITH METADATA")
    print("=" * 80)
    try:
        result = await extract_content_with_metadata(TEST_URL, extraction_type="fast")
        if result.get('text'):
            print(f"✓ Success!")
            print(f"✓ Title: {result.get('title', 'N/A')}")
            print(f"✓ Source: {result.get('source', 'N/A')}")
            print(f"✓ Content length: {len(result['text'])} characters")
            print(f"\nFirst 500 characters:")
            print("-" * 80)
            print(result['text'][:500])
            print("-" * 80)
        else:
            print("❌ Failed to extract content")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_extraction_methods())