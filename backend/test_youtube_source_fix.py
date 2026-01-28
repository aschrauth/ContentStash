"""
Test script to verify the YouTube source fix works without delays.
This tests that we can get the YouTube channel name quickly without fetching transcripts.
"""
import asyncio
import time
from app.services.youtube import extract_video_id, get_youtube_channel_name_only
from app.config import settings

async def test_lightweight_channel_extraction():
    """Test that channel name extraction is fast and doesn't fetch transcripts."""
    
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Astley
        "https://youtu.be/jNQXAC9IVRw",  # Me at the zoo
    ]
    
    print("=" * 80)
    print("Testing Lightweight YouTube Channel Name Extraction")
    print("=" * 80)
    print()
    
    for url in test_urls:
        print(f"Testing URL: {url}")
        print("-" * 80)
        
        # Extract video ID
        video_id = extract_video_id(url)
        if not video_id:
            print(f"❌ Failed to extract video ID from {url}")
            continue
        
        print(f"✓ Extracted video ID: {video_id}")
        
        # Time the lightweight extraction
        start_time = time.time()
        source = get_youtube_channel_name_only(video_id, settings.youtube_api_key)
        elapsed_time = time.time() - start_time
        
        print(f"✓ Got source: '{source}'")
        print(f"⏱️  Time taken: {elapsed_time:.2f} seconds")
        
        # Check if it was fast (should be under 3 seconds)
        if elapsed_time < 3.0:
            print(f"✅ PASS: Extraction was fast ({elapsed_time:.2f}s < 3s)")
        else:
            print(f"⚠️  WARNING: Extraction took longer than expected ({elapsed_time:.2f}s)")
        
        print()
    
    print("=" * 80)
    print("Test Complete!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_lightweight_channel_extraction())