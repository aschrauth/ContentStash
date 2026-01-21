"""
Test script for yt-dlp transcript extraction.
This tests the new get_transcript_from_ytdlp function.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.services.youtube import get_transcript_from_ytdlp, extract_video_id

def test_ytdlp_transcript():
    """Test yt-dlp transcript extraction with a known video."""
    
    # Test with a popular video that should have transcripts
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Rick Astley - Never Gonna Give You Up
    
    print(f"\n{'='*80}")
    print(f"Testing yt-dlp transcript extraction")
    print(f"{'='*80}\n")
    
    # Extract video ID
    video_id = extract_video_id(test_url)
    print(f"Video ID: {video_id}")
    
    if not video_id:
        print("❌ Failed to extract video ID")
        return False
    
    # Try to get transcript using yt-dlp
    print(f"\nAttempting to extract transcript using yt-dlp...")
    transcript = get_transcript_from_ytdlp(video_id)
    
    if transcript:
        print(f"\n✅ SUCCESS: Extracted transcript from yt-dlp")
        print(f"Transcript length: {len(transcript)} characters")
        print(f"\nFirst 500 characters of transcript:")
        print("-" * 80)
        print(transcript[:500])
        print("-" * 80)
        return True
    else:
        print(f"\n❌ FAILED: Could not extract transcript from yt-dlp")
        return False

if __name__ == "__main__":
    success = test_ytdlp_transcript()
    sys.exit(0 if success else 1)