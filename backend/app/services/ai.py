"""
AI service for generating tags and topics using OpenAI.
"""
from openai import OpenAI
from typing import List, Optional
import logging
from app.config import settings

logger = logging.getLogger(__name__)


def generate_tags_and_topic(
    content: str,
    existing_tags: Optional[List[str]] = None,
    max_tags: int = 7,
    min_tags: int = 3
) -> dict:
    """
    Generate suggested tags and a topic label for content using OpenAI.
    
    Args:
        content: The text content to analyze
        existing_tags: Optional list of user's existing tags to consider
        max_tags: Maximum number of tags to generate
        min_tags: Minimum number of tags to generate
        
    Returns:
        Dictionary with 'tags' (list) and 'topic' (string)
        Returns empty suggestions if API key is missing or on error
    """
    # Check if API key is configured
    if not settings.openai_api_key:
        logger.warning("OpenAI API key not configured, returning empty suggestions")
        return {
            'tags': [],
            'topic': None
        }
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=settings.openai_api_key)
        
        # Truncate content if too long (to avoid token limits)
        max_content_length = 4000
        truncated_content = content[:max_content_length] if len(content) > max_content_length else content
        
        # Build the prompt
        prompt = _build_prompt(truncated_content, existing_tags, max_tags, min_tags)
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Using cost-effective model
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that analyzes content and generates relevant tags and topic labels."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=200
        )
        
        # Parse the response
        result = _parse_response(response.choices[0].message.content)
        
        logger.info(f"Generated {len(result['tags'])} tags and topic: {result['topic']}")
        return result
        
    except Exception as e:
        logger.error(f"Error generating AI suggestions: {str(e)}")
        return {
            'tags': [],
            'topic': None
        }


def _build_prompt(
    content: str,
    existing_tags: Optional[List[str]],
    max_tags: int,
    min_tags: int
) -> str:
    """Build the prompt for OpenAI."""
    prompt = f"""Analyze the following content and provide:
1. Between {min_tags} and {max_tags} relevant tags (single words or short phrases)
2. A single topic label that best describes the main subject

Content:
{content}

"""
    
    if existing_tags and len(existing_tags) > 0:
        prompt += f"\nThe user has previously used these tags: {', '.join(existing_tags)}\n"
        prompt += "Consider these existing tags when generating new ones, but feel free to suggest new tags if they're more relevant.\n"
    
    prompt += """
Please respond in the following format:
TAGS: tag1, tag2, tag3, ...
TOPIC: main topic label

Keep tags concise and relevant. The topic should be a clear, descriptive label."""
    
    return prompt


def _parse_response(response_text: str) -> dict:
    """Parse the OpenAI response into tags and topic."""
    tags = []
    topic = None
    
    try:
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('TAGS:'):
                # Extract tags
                tags_str = line.replace('TAGS:', '').strip()
                tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
            
            elif line.startswith('TOPIC:'):
                # Extract topic
                topic = line.replace('TOPIC:', '').strip()
        
        # Validate and clean tags
        tags = [tag for tag in tags if len(tag) > 0 and len(tag) <= 50]
        
        # Validate topic
        if topic and len(topic) > 100:
            topic = topic[:100]
        
    except Exception as e:
        logger.error(f"Error parsing AI response: {str(e)}")
    
    return {
        'tags': tags,
        'topic': topic
    }


def generate_tags(content: str, existing_tags: Optional[List[str]] = None) -> List[str]:
    """
    Generate only tags (convenience function).
    
    Args:
        content: The text content to analyze
        existing_tags: Optional list of user's existing tags
        
    Returns:
        List of suggested tags
    """
    result = generate_tags_and_topic(content, existing_tags)
    return result['tags']


def generate_topic(content: str) -> Optional[str]:
    """
    Generate only a topic label (convenience function).
    
    Args:
        content: The text content to analyze
        
    Returns:
        Suggested topic label or None
    """
    result = generate_tags_and_topic(content)
    return result['topic']