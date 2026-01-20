"""
Test script to diagnose YouTube extraction issues in production.
This will help identify where the problem occurs.
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.youtube import is_youtube_url, extract_video_id, get_video_transcript, get_video_metadata_from_api
from app.services.metadata import fetch_metadata
from app.services.extraction import extract_content
from app.config import settings

async def test_youtube_flow():
    """Test the complete YouTube extraction flow."""
    
    # Test URL
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print("=" * 80)
    print("YOUTUBE EXTRACTION DIAGNOSTIC TEST")
    print("=" * 80)
    print()
    
    # Test 1: Check if YouTube URL is detected
    print("TEST 1: YouTube URL Detection")
    print(f"URL: {test_url}")
    is_yt = is_youtube_url(test_url)
    print(f"✓ is_youtube_url() = {is_yt}")
    print()
    
    # Test 2: Extract video ID
    print("TEST 2: Video ID Extraction")
    video_id = extract_video_id(test_url)
    print(f"✓ extract_video_id() = {video_id}")
    print()
    
    # Test 3: Check if youtube-transcript-api is installed
    print("TEST 3: Package Import Check")
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        print("✓ youtube-transcript-api is installed")
        print(f"  Module location: {YouTubeTranscriptApi.__module__}")
    except ImportError as e:
        print(f"✗ youtube-transcript-api import failed: {e}")
    print()
    
    # Test 4: Check if google-api-python-client is installed
    print("TEST 4: Google API Client Check")
    try:
        from googleapiclient.discovery import build
        print("✓ google-api-python-client is installed")
    except ImportError as e:
        print(f"✗ google-api-python-client import failed: {e}")
    print()
    
    # Test 5: Check YouTube API key configuration
    print("TEST 5: YouTube API Key Configuration")
    if settings.youtube_api_key:
        print(f"✓ YouTube API key is configured")
        print(f"  Key prefix: {settings.youtube_api_key[:10]}...")
    else:
        print("✗ YouTube API key is NOT configured")
    print()
    
    # Test 6: Try to get transcript
    print("TEST 6: Transcript Extraction")
    if video_id:
        transcript = get_video_transcript(video_id)
        if transcript:
            print(f"✓ Transcript extracted successfully")
            print(f"  Length: {len(transcript)} characters")
            print(f"  Preview: {transcript[:200]}...")
        else:
            print("✗ Transcript extraction failed")
    else:
        print("✗ Cannot test - no video ID")
    print()
    
    # Test 7: Try YouTube Data API fallback
    print("TEST 7: YouTube Data API Fallback")
    if video_id:
        metadata = get_video_metadata_from_api(video_id, settings.youtube_api_key)
        if metadata:
            print(f"✓ YouTube API metadata fetched successfully")
            print(f"  Title: {metadata.get('title', 'N/A')}")
            print(f"  Channel: {metadata.get('channel_name', 'N/A')}")
            print(f"  Description length: {len(metadata.get('description', ''))} characters")
        else:
            print("✗ YouTube API metadata fetch failed")
    else:
        print("✗ Cannot test - no video ID")
    print()
    
    # Test 8: Test the preview endpoint flow (metadata service)
    print("TEST 8: Preview Endpoint Flow (metadata.fetch_metadata)")
    metadata = fetch_metadata(test_url)
    print(f"Metadata returned:")
    print(f"  title: {metadata.get('title', 'None')}")
    print(f"  description: {metadata.get('description', 'None')}")
    print(f"  image_url: {metadata.get('image_url', 'None')}")
    print(f"  favicon_url: {metadata.get('favicon_url', 'None')}")
    print()
    
    # Test 9: Test the full extraction flow
    print("TEST 9: Full Extraction Flow (extraction.extract_content)")
    content = await extract_content(test_url, extraction_type="fast")
    if content:
        print(f"✓ Content extracted successfully")
        print(f"  Length: {len(content)} characters")
        print(f"  Preview: {content[:200]}...")
    else:
        print("✗ Content extraction failed")
    print()
    
    print("=" * 80)
    print("DIAGNOSTIC TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_youtube_flow())