"""
YouTube transcript extraction service with YouTube Data API v3 fallback and yt-dlp support.
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

from app.services.exceptions import ExtractionBlockError

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
        
    Raises:
        ExtractionBlockError: When YouTube blocks the request (bot detection, sign-in required)
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
        
    except TranscriptsDisabled as e:
        error_msg = str(e).lower()
        # Check if this is a blocking error (bot detection, sign-in required)
        if any(keyword in error_msg for keyword in ['sign in', 'bot', 'confirm', 'cookies', 'blocked']):
            logger.warning(f"YouTube blocking detected for video ID {video_id}: {str(e)}")
            raise ExtractionBlockError(f"YouTube blocked transcript access: {str(e)}")
        logger.warning(f"Transcripts are disabled for video ID: {video_id}")
        return None
    except NoTranscriptFound:
        logger.warning(f"No transcript found for video ID: {video_id}")
        return None
    except VideoUnavailable as e:
        error_msg = str(e).lower()
        # Check if this is a blocking error
        if any(keyword in error_msg for keyword in ['sign in', 'bot', 'confirm', 'cookies', 'blocked']):
            logger.warning(f"YouTube blocking detected for video ID {video_id}: {str(e)}")
            raise ExtractionBlockError(f"YouTube blocked video access: {str(e)}")
        logger.warning(f"Video unavailable for video ID: {video_id}")
        return None
    except YouTubeRequestFailed as e:
        error_msg = str(e).lower()
        # Check if this is a blocking error (403, 429, or blocking messages)
        if any(keyword in error_msg for keyword in ['sign in', 'bot', 'confirm', 'cookies', 'blocked', '403', '429']):
            logger.warning(f"YouTube blocking detected for video ID {video_id}: {str(e)}")
            raise ExtractionBlockError(f"YouTube request blocked: {str(e)}")
        logger.error(f"YouTube request failed for video ID {video_id}: {str(e)}")
        return None
    except Exception as e:
        error_msg = str(e).lower()
        # Check if this is a blocking error in any unexpected exception
        if any(keyword in error_msg for keyword in ['sign in', 'bot', 'confirm', 'cookies', 'blocked', '403', '429']):
            logger.warning(f"YouTube blocking detected for video ID {video_id}: {str(e)}")
            raise ExtractionBlockError(f"YouTube blocked request: {str(e)}")
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


def get_video_metadata_from_ytdlp(video_id: str) -> Optional[Dict]:
    """
    Fetch video metadata using yt-dlp as a robust fallback.
    This is more resilient to IP blocking and rate limiting than the transcript API.
    
    Args:
        video_id: YouTube video ID
        
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
    try:
        import yt_dlp
        
        logger.info(f"Attempting to fetch metadata from yt-dlp for video ID: {video_id}")
        
        # Configure yt-dlp to extract metadata only (no download)
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
        }
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                logger.warning(f"No video info found for video ID: {video_id}")
                return None
            
            # Extract metadata from yt-dlp response
            metadata = {
                'title': info.get('title', ''),
                'description': info.get('description', ''),
                'thumbnail_url': info.get('thumbnail', ''),
                'channel_name': info.get('uploader', ''),
                'published_at': info.get('upload_date', '')
            }
            
            logger.info(f"Successfully fetched metadata from yt-dlp for video ID: {video_id}")
            logger.debug(f"Metadata: title='{metadata['title']}', channel='{metadata['channel_name']}'")
            
            return metadata
            
    except ImportError:
        logger.error("yt-dlp not installed. Install with: pip install yt-dlp")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching metadata from yt-dlp for video ID {video_id}: {str(e)}")
        return None

def get_transcript_from_ytdlp(video_id: str) -> Optional[str]:
    """
    Fetch video transcript using yt-dlp as a robust fallback.
    This is more resilient to IP blocking and rate limiting than youtube_transcript_api.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Formatted transcript as markdown or None if unavailable
        
    Raises:
        ExtractionBlockError: When YouTube blocks the request (bot detection, sign-in required)
    """
    try:
        import yt_dlp
        import re
        
        logger.info(f"Attempting to fetch transcript from yt-dlp for video ID: {video_id}")
        
        # Configure yt-dlp to extract subtitles
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'subtitlesformat': 'vtt',
        }
        
        url = f"https://www.youtube.com/watch?v={video_id}"
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if not info:
                logger.warning(f"No video info found for video ID: {video_id}")
                return None
            
            # Check if subtitles are available
            subtitles = info.get('subtitles', {})
            automatic_captions = info.get('automatic_captions', {})
            
            # Prefer manual subtitles over automatic captions
            subtitle_data = None
            if 'en' in subtitles:
                subtitle_data = subtitles['en']
                logger.info(f"Found manual English subtitles for video ID: {video_id}")
            elif 'en' in automatic_captions:
                subtitle_data = automatic_captions['en']
                logger.info(f"Found automatic English captions for video ID: {video_id}")
            else:
                logger.warning(f"No English subtitles or captions found for video ID: {video_id}")
                return None
            
            # Find the VTT format subtitle
            vtt_subtitle = None
            for sub in subtitle_data:
                if sub.get('ext') == 'vtt':
                    vtt_subtitle = sub
                    break
            
            if not vtt_subtitle:
                logger.warning(f"No VTT format subtitle found for video ID: {video_id}")
                return None
            
            # Download the subtitle content
            import urllib.request
            subtitle_url = vtt_subtitle.get('url')
            if not subtitle_url:
                logger.warning(f"No subtitle URL found for video ID: {video_id}")
                return None
            
            logger.info(f"Downloading subtitle from: {subtitle_url}")
            with urllib.request.urlopen(subtitle_url) as response:
                vtt_content = response.read().decode('utf-8')
            
            # Parse VTT content to extract text
            # VTT format has timestamps and text, we only want the text
            lines = vtt_content.split('\n')
            transcript_lines = []
            
            for line in lines:
                line = line.strip()
                # Skip VTT headers, timestamps, and empty lines
                if (line.startswith('WEBVTT') or
                    line.startswith('Kind:') or
                    line.startswith('Language:') or
                    '-->' in line or
                    not line or
                    re.match(r'^\d+$', line)):
                    continue
                
                # Remove VTT formatting tags like <c> </c>
                line = re.sub(r'<[^>]+>', '', line)
                
                # Skip duplicate lines (VTT often repeats lines)
                if transcript_lines and line == transcript_lines[-1]:
                    continue
                
                transcript_lines.append(line)
            
            if not transcript_lines:
                logger.warning(f"No transcript text extracted from VTT for video ID: {video_id}")
                return None
            
            # Format transcript as readable paragraphs
            # Group sentences into paragraphs (every 5-10 lines or at natural breaks)
            paragraphs = []
            current_paragraph = []
            
            for line in transcript_lines:
                current_paragraph.append(line)
                
                # Start new paragraph if we have enough lines or if line ends with punctuation
                if len(current_paragraph) >= 8 or (line.endswith(('.', '!', '?')) and len(current_paragraph) >= 3):
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
            
            # Add final paragraph
            if current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
            
            # Join paragraphs with double newlines for markdown formatting
            formatted_transcript = '\n\n'.join(paragraphs)
            
            logger.info(f"Successfully extracted transcript from yt-dlp for video ID: {video_id} ({len(formatted_transcript)} characters)")
            return formatted_transcript
            
    except ImportError:
        logger.error("yt-dlp not installed. Install with: pip install yt-dlp")
        return None
    except Exception as e:
        error_msg = str(e).lower()
        # Check if this is a blocking error
        if any(keyword in error_msg for keyword in ['sign in', 'bot', 'confirm', 'cookies', 'blocked', '403', '429']):
            logger.warning(f"YouTube blocking detected in yt-dlp for video ID {video_id}: {str(e)}")
            raise ExtractionBlockError(f"YouTube blocked yt-dlp request: {str(e)}")
        logger.error(f"Unexpected error fetching transcript from yt-dlp for video ID {video_id}: {str(e)}")
        return None



def get_youtube_preview_metadata(url: str, api_key: Optional[str] = None) -> Optional[Dict]:
    """
    Get YouTube video metadata for preview purposes.
    Tries multiple methods in order of preference:
    1. YouTube Data API (if key available)
    2. yt-dlp (robust fallback)
    
    This function is specifically designed for the preview endpoint to work
    reliably in production without requiring transcripts.
    
    Args:
        url: YouTube URL
        api_key: YouTube Data API v3 key (optional)
        
    Returns:
        Dictionary with metadata fields or None if all methods fail:
        {
            'title': str,
            'description': str,
            'thumbnail': str,
            'channel_name': str,
            'published_at': str
        }
    """
    video_id = extract_video_id(url)
    if not video_id:
        logger.error(f"Could not extract video ID from URL: {url}")
        return None
    
    logger.info(f"Getting YouTube preview metadata for video ID: {video_id}")
    
    # Try YouTube Data API first if key is available
    if api_key:
        logger.info("Attempting YouTube Data API for preview metadata")
        metadata = get_video_metadata_from_api(video_id, api_key)
        if metadata:
            logger.info("✓ Successfully fetched preview metadata from YouTube Data API")
            # Normalize field names for preview response
            return {
                'title': metadata.get('title'),
                'description': metadata.get('description'),
                'thumbnail': metadata.get('thumbnail_url'),
                'channel_name': metadata.get('channel_name'),
                'published_at': metadata.get('published_at')
            }
        logger.warning("YouTube Data API failed, trying yt-dlp fallback")
    else:
        logger.info("No YouTube API key configured, using yt-dlp directly")
    
    # Fallback to yt-dlp (more robust, works without API key)
    logger.info("Attempting yt-dlp for preview metadata")
    metadata = get_video_metadata_from_ytdlp(video_id)
    if metadata:
        logger.info("✓ Successfully fetched preview metadata from yt-dlp")
        # Normalize field names for preview response
        return {
            'title': metadata.get('title'),
            'description': metadata.get('description'),
            'thumbnail': metadata.get('thumbnail_url'),
            'channel_name': metadata.get('channel_name'),
            'published_at': metadata.get('published_at')
        }
    
    logger.error(f"✗ All methods failed to fetch preview metadata for {url}")
    return None