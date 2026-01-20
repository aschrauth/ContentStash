"""
Test script to verify YouTube preview and extraction fixes.
Tests the new YouTube-aware preview endpoint and yt-dlp fallback.
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.youtube import (
    is_youtube_url,
    extract_video_id,
    get_youtube_preview_metadata,
    get_video_metadata_from_ytdlp
)

async def test_youtube_preview():
    """Test YouTube preview metadata extraction."""
    print("=" * 80)
    print("TESTING YOUTUBE PREVIEW METADATA EXTRACTION")
    print("=" * 80)
    
    # Test URL
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print(f"\n1. Testing URL detection:")
    print(f"   URL: {test_url}")
    print(f"   Is YouTube URL: {is_youtube_url(test_url)}")
    
    print(f"\n2. Testing video ID extraction:")
    video_id = extract_video_id(test_url)
    print(f"   Video ID: {video_id}")
    
    print(f"\n3. Testing yt-dlp metadata extraction:")
    ytdlp_metadata = get_video_metadata_from_ytdlp(video_id)
    if ytdlp_metadata:
        print(f"   ✓ Success!")
        print(f"   Title: {ytdlp_metadata.get('title')}")
        print(f"   Channel: {ytdlp_metadata.get('channel_name')}")
        print(f"   Description length: {len(ytdlp_metadata.get('description', ''))} chars")
        print(f"   Thumbnail: {ytdlp_metadata.get('thumbnail_url')[:50]}...")
    else:
        print(f"   ✗ Failed to extract metadata with yt-dlp")
    
    print(f"\n4. Testing get_youtube_preview_metadata (full function):")
    preview_metadata = get_youtube_preview_metadata(test_url, api_key=None)
    if preview_metadata:
        print(f"   ✓ Success!")
        print(f"   Title: {preview_metadata.get('title')}")
        print(f"   Channel: {preview_metadata.get('channel_name')}")
        print(f"   Description length: {len(preview_metadata.get('description', ''))} chars")
        print(f"   Thumbnail: {preview_metadata.get('thumbnail')[:50] if preview_metadata.get('thumbnail') else 'None'}...")
    else:
        print(f"   ✗ Failed to extract preview metadata")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_youtube_preview())