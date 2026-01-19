"""
Test script for extraction_type feature
"""
import asyncio
from app.services.extraction import extract_content

async def test_extraction_types():
    """Test both fast and complete extraction types"""
    
    # Test URL - using a simple article
    test_url = "https://example.com"
    
    print("Testing extraction_type feature...")
    print("=" * 50)
    
    # Test 1: Fast extraction (default)
    print("\n1. Testing FAST extraction (default):")
    print(f"   URL: {test_url}")
    try:
        content_fast = await extract_content(test_url, extraction_type="fast")
        if content_fast:
            print(f"   ✓ Fast extraction successful ({len(content_fast)} chars)")
        else:
            print("   ✗ Fast extraction returned None")
    except Exception as e:
        print(f"   ✗ Fast extraction failed: {str(e)}")
    
    # Test 2: Complete extraction
    print("\n2. Testing COMPLETE extraction:")
    print(f"   URL: {test_url}")
    try:
        content_complete = await extract_content(test_url, extraction_type="complete")
        if content_complete:
            print(f"   ✓ Complete extraction successful ({len(content_complete)} chars)")
        else:
            print("   ✗ Complete extraction returned None")
    except Exception as e:
        print(f"   ✗ Complete extraction failed: {str(e)}")
    
    # Test 3: YouTube URL should always use transcript
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print(f"\n3. Testing YouTube URL (should use transcript regardless of type):")
    print(f"   URL: {youtube_url}")
    try:
        content_yt = await extract_content(youtube_url, extraction_type="complete")
        if content_yt:
            print(f"   ✓ YouTube extraction successful ({len(content_yt)} chars)")
        else:
            print("   ✗ YouTube extraction returned None (transcript may not be available)")
    except Exception as e:
        print(f"   ✗ YouTube extraction failed: {str(e)}")
    
    print("\n" + "=" * 50)
    print("Testing complete!")

if __name__ == "__main__":
    asyncio.run(test_extraction_types())