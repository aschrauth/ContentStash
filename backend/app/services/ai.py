"""
AI service for generating tags and topics using OpenAI or Gemini.
"""
from openai import OpenAI
from typing import List, Optional
import logging
import json
from app.config import settings
from app.services.gemini import gemini_service, GeminiServiceError

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


def generate_metadata_from_content(content: str) -> dict:
    """
    Generate title, description, and tags from pasted content.
    
    This function provides a fallback mechanism:
    - If OpenAI is available, uses OpenAI to generate smart metadata
    - If Gemini is available, uses Gemini to generate smart metadata
    - Otherwise, uses basic text processing to extract metadata
    
    Args:
        content: The pasted text content
        
    Returns:
        Dictionary with 'title', 'description', and 'tags'
    """
    # Try OpenAI first if configured
    if settings.openai_api_key:
        try:
            return _generate_metadata_with_openai(content)
        except Exception as e:
            logger.error(f"Error generating metadata with OpenAI: {str(e)}, trying Gemini")
    
    # Try Gemini if available
    if gemini_service.is_available():
        try:
            return _generate_metadata_with_gemini(content)
        except Exception as e:
            logger.error(f"Error generating metadata with Gemini: {str(e)}, falling back to text processing")
    
    # Fallback to basic text processing
    logger.info("No AI service available, using fallback text processing")
    return _generate_metadata_fallback(content)


def _generate_metadata_with_openai(content: str) -> dict:
    """Generate metadata using OpenAI."""
    # Initialize OpenAI client
    client = OpenAI(api_key=settings.openai_api_key)
    
    # Truncate content if too long
    max_content_length = 4000
    truncated_content = content[:max_content_length] if len(content) > max_content_length else content
    
    # Build the prompt
    prompt = f"""Analyze the following content and generate:
1. A concise title (max 100 characters)
2. A brief description (max 200 characters)
3. 3-7 relevant tags (single words or short phrases)

Content:
{truncated_content}

Please respond in the following format:
TITLE: your generated title
DESCRIPTION: your generated description
TAGS: tag1, tag2, tag3, ...

Keep everything concise and relevant."""
    
    # Call OpenAI API
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant that analyzes content and generates metadata."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.7,
        max_tokens=300
    )
    
    # Parse the response
    result = _parse_metadata_response(response.choices[0].message.content)
    
    logger.info(f"Generated metadata with OpenAI: title length={len(result['title'])}, tags={len(result['tags'])}")
    return result


def _generate_metadata_with_gemini(content: str) -> dict:
    """Generate metadata using Gemini."""
    # Truncate content if too long
    max_content_length = 1500
    truncated_content = content[:max_content_length] if len(content) > max_content_length else content
    
    # Build the prompt for JSON output
    prompt = f"""Analyze this content and provide metadata in JSON format.

Content: {truncated_content}

Respond with JSON only:
{{
  "title": "concise title (max 100 chars)",
  "description": "brief description (max 200 chars)",
  "tags": ["tag1", "tag2", "tag3"]
}}"""
    
    logger.info("Generating metadata with Gemini")
    
    # Call Gemini with Flash-Lite model
    response = gemini_service.generate_content(
        prompt=prompt,
        model="gemini-2.5-flash-lite"
    )
    
    if not response:
        raise GeminiServiceError("Empty response from Gemini")
    
    # Parse JSON response
    response_text = response.strip()
    if response_text.startswith("```json"):
        response_text = response_text[7:]
    if response_text.startswith("```"):
        response_text = response_text[3:]
    if response_text.endswith("```"):
        response_text = response_text[:-3]
    response_text = response_text.strip()
    
    try:
        metadata = json.loads(response_text)
        
        # Validate and extract fields
        title = metadata.get("title", "Untitled")[:100]
        description = metadata.get("description", "")[:200]
        tags = metadata.get("tags", [])
        
        # Ensure tags is a list and limit to 7 tags
        if not isinstance(tags, list):
            tags = []
        tags = tags[:7]
        
        result = {
            'title': title,
            'description': description,
            'tags': tags
        }
        
        logger.info(f"Generated metadata with Gemini: title length={len(result['title'])}, tags={len(result['tags'])}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response from Gemini: {str(e)}")
        raise GeminiServiceError(f"Invalid JSON response: {str(e)}")


def _parse_metadata_response(response_text: str) -> dict:
    """Parse the OpenAI metadata response."""
    title = ""
    description = ""
    tags = []
    
    try:
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('TITLE:'):
                title = line.replace('TITLE:', '').strip()
            elif line.startswith('DESCRIPTION:'):
                description = line.replace('DESCRIPTION:', '').strip()
            elif line.startswith('TAGS:'):
                tags_str = line.replace('TAGS:', '').strip()
                tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()]
        
        # Validate and clean
        if not title:
            title = "Untitled"
        title = title[:100]  # Max 100 chars
        
        if description:
            description = description[:200]  # Max 200 chars
        
        tags = [tag for tag in tags if len(tag) > 0 and len(tag) <= 50][:7]  # Max 7 tags
        
    except Exception as e:
        logger.error(f"Error parsing metadata response: {str(e)}")
        return _generate_metadata_fallback("")
    
    return {
        'title': title,
        'description': description,
        'tags': tags
    }


def _generate_metadata_fallback(content: str) -> dict:
    """
    Fallback metadata generation using basic text processing.
    Used when OpenAI API is not available.
    """
    if not content or len(content.strip()) == 0:
        return {
            'title': 'Untitled',
            'description': '',
            'tags': []
        }
    
    # Clean content
    clean_content = content.strip()
    
    # Extract title from first line or first 50 characters
    lines = clean_content.split('\n')
    first_line = lines[0].strip() if lines else clean_content
    
    # Remove markdown formatting from title
    title = first_line.replace('#', '').replace('*', '').replace('_', '').strip()
    
    # Limit title length
    if len(title) > 100:
        title = title[:97] + '...'
    elif len(title) == 0:
        title = clean_content[:50] + ('...' if len(clean_content) > 50 else '')
    
    # Extract description from first paragraph or first 200 characters
    # Find first paragraph (text before double newline or first 200 chars)
    paragraphs = clean_content.split('\n\n')
    first_paragraph = paragraphs[0] if paragraphs else clean_content
    
    description = first_paragraph.replace('#', '').replace('*', '').replace('_', '').strip()
    if len(description) > 200:
        description = description[:197] + '...'
    
    # Extract basic tags from content (simple keyword extraction)
    tags = []
    lower_content = clean_content.lower()
    
    # Common topic keywords
    keyword_map = {
        'development': ['code', 'programming', 'developer', 'software'],
        'design': ['design', 'ui', 'ux', 'interface'],
        'ai': ['ai', 'artificial intelligence', 'machine learning', 'llm'],
        'product': ['product', 'feature', 'roadmap'],
        'research': ['research', 'study', 'analysis'],
        'tutorial': ['tutorial', 'guide', 'how to', 'learn'],
        'article': ['article', 'blog', 'post'],
    }
    
    for tag, keywords in keyword_map.items():
        if any(keyword in lower_content for keyword in keywords):
            tags.append(tag)
            if len(tags) >= 5:
                break
    
    return {
        'title': title,
        'description': description,
        'tags': tags
    }