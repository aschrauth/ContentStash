"""
YouTube transcript extraction service with YouTube Data API v3 fallback.
"""
import re
import logging
from typing import Optional, Dict
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    YouTubeRequestFailed
)

logger = logging.getLogger(__name__)


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats.
    
    Supports:
    - youtube.com/watch?v=VIDEO_ID
    - youtu.be/VIDEO_ID
    - youtube.com/embed/VIDEO_ID
    - youtube.com/v/VIDEO_ID
    - youtube.com/shorts/VIDEO_ID
    
    Args:
        url: YouTube URL
        
    Returns:
        Video ID or None if not found
    """
    # Pattern to match various YouTube URL formats
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            logger.info(f"Extracted video ID: {video_id} from URL: {url}")
            return video_id
    
    logger.warning(f"Could not extract video ID from URL: {url}")
    return None


def get_video_transcript(video_id: str) -> Optional[str]:
    """
    Fetch and format YouTube video transcript.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Formatted transcript as markdown or None if unavailable
    """
    try:
        # Fetch transcript (prefer English, accept auto-generated)
        api = YouTubeTranscriptApi()
        result = api.fetch(video_id, languages=['en'])
        transcript_list = result.to_raw_data()
        
        if not transcript_list:
            logger.warning(f"Empty transcript for video ID: {video_id}")
            return None
        
        # Format transcript as readable paragraphs
        # Group sentences into paragraphs based on timing gaps
        paragraphs = []
        current_paragraph = []
        last_end_time = 0
        
        for entry in transcript_list:
            text = entry['text'].strip()
            start_time = entry['start']
            
            # Start new paragraph if there's a significant gap (>2 seconds)
            # or if current paragraph is getting long (>500 chars)
            current_length = sum(len(t) for t in current_paragraph)
            time_gap = start_time - last_end_time
            
            if current_paragraph and (time_gap > 2.0 or current_length > 500):
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
            
            current_paragraph.append(text)
            last_end_time = start_time + entry.get('duration', 0)
        
        # Add final paragraph
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        
        # Join paragraphs with double newlines for markdown formatting
        formatted_transcript = '\n\n'.join(paragraphs)
        
        logger.info(f"Successfully extracted transcript for video ID: {video_id} ({len(formatted_transcript)} characters)")
        return formatted_transcript
        
    except TranscriptsDisabled:
        logger.warning(f"Transcripts are disabled for video ID: {video_id}")
        return None
    except NoTranscriptFound:
        logger.warning(f"No transcript found for video ID: {video_id}")
        return None
    except VideoUnavailable:
        logger.warning(f"Video unavailable for video ID: {video_id}")
        return None
    except YouTubeRequestFailed as e:
        logger.error(f"YouTube request failed for video ID {video_id}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching transcript for video ID {video_id}: {str(e)}")
        return None


def is_youtube_url(url: str) -> bool:
    """
    Check if a URL is a YouTube URL.
    
    Args:
        url: URL to check
        
    Returns:
        True if URL is a YouTube URL, False otherwise
    """
    youtube_domains = ['youtube.com', 'youtu.be', 'www.youtube.com', 'm.youtube.com']
    return any(domain in url.lower() for domain in youtube_domains)


def get_video_metadata_from_api(video_id: str, api_key: Optional[str] = None) -> Optional[Dict]:
    """
    Fetch video metadata using YouTube Data API v3.
    This is used as a fallback when transcript extraction fails.
    
    Args:
        video_id: YouTube video ID
        api_key: YouTube Data API v3 key (optional, will gracefully fail if not provided)
        
    Returns:
        Dictionary with metadata fields or None if extraction fails:
        {
            'title': str,
            'description': str,
            'thumbnail_url': str,
            'channel_name': str,
            'published_at': str
        }
    """
    if not api_key:
        logger.warning(f"YouTube API key not configured, cannot fetch metadata for video ID: {video_id}")
        return None
    
    try:
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        
        logger.info(f"Attempting to fetch metadata from YouTube Data API for video ID: {video_id}")
        
        # Build the YouTube API client
        youtube = build('youtube', 'v3', developerKey=api_key)
        
        # Request video details
        request = youtube.videos().list(
            part='snippet',
            id=video_id
        )
        response = request.execute()
        
        if not response.get('items'):
            logger.warning(f"No video found for video ID: {video_id}")
            return None
        
        # Extract metadata from the response
        video_data = response['items'][0]['snippet']
        
        metadata = {
            'title': video_data.get('title', ''),
            'description': video_data.get('description', ''),
            'thumbnail_url': video_data.get('thumbnails', {}).get('high', {}).get('url', ''),
            'channel_name': video_data.get('channelTitle', ''),
            'published_at': video_data.get('publishedAt', '')
        }
        
        logger.info(f"Successfully fetched metadata from YouTube API for video ID: {video_id}")
        logger.debug(f"Metadata: title='{metadata['title']}', channel='{metadata['channel_name']}'")
        
        return metadata
        
    except HttpError as e:
        logger.error(f"YouTube API HTTP error for video ID {video_id}: {str(e)}")
        return None
    except ImportError:
        logger.error("google-api-python-client not installed. Install with: pip install google-api-python-client")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching metadata from YouTube API for video ID {video_id}: {str(e)}")
        return None