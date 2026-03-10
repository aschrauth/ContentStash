"""
AI service for Gemini-powered metadata, tags, and topic generation.
"""
from typing import List, Optional
import json
import logging

from app.services.gemini import (
    GEMINI_MODEL_TEXT_FAST,
    GeminiServiceError,
    gemini_service,
)

logger = logging.getLogger(__name__)


def generate_tags_and_topic(
    content: str,
    existing_tags: Optional[List[str]] = None,
    max_tags: int = 7,
    min_tags: int = 3
) -> dict:
    """
    Generate suggested tags and a topic label using Gemini.

    Returns empty suggestions if Gemini is unavailable or the response is invalid.
    """
    if not gemini_service.is_available():
        logger.warning("Gemini API key not configured, returning empty suggestions")
        return {
            "tags": [],
            "topic": None,
        }

    try:
        truncated_content = content[:4000] if len(content) > 4000 else content
        prompt = _build_tags_prompt(
            truncated_content,
            existing_tags,
            max_tags,
            min_tags,
        )

        response = gemini_service.generate_content(
            prompt=prompt,
            model=GEMINI_MODEL_TEXT_FAST,
        )

        if not response:
            raise GeminiServiceError("Empty response from Gemini")

        parsed = _parse_json_dict(response)
        tags = parsed.get("tags", [])
        topic = parsed.get("topic")

        if not isinstance(tags, list):
            tags = []
        tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        tags = [tag[:50] for tag in tags][:max_tags]

        if len(tags) < min_tags:
            logger.warning("Gemini returned too few tags, falling back to empty suggestions")
            return {
                "tags": [],
                "topic": None,
            }

        if not isinstance(topic, str) or not topic.strip():
            topic = None
        elif len(topic) > 100:
            topic = topic[:100]
        else:
            topic = topic.strip()

        result = {
            "tags": tags,
            "topic": topic,
        }

        logger.info("Generated %s tags and topic: %s", len(tags), topic)
        return result
    except Exception as e:
        logger.error("Error generating AI suggestions: %s", str(e))
        return {
            "tags": [],
            "topic": None,
        }


def _build_tags_prompt(
    content: str,
    existing_tags: Optional[List[str]],
    max_tags: int,
    min_tags: int
) -> str:
    prompt = f"""Analyze the following content and respond with JSON only.

Content:
{content}

Return this exact shape:
{{
  "tags": ["tag1", "tag2", "tag3"],
  "topic": "main topic label"
}}

Rules:
- Return between {min_tags} and {max_tags} tags
- Tags must be short, specific, and relevant
- Topic must be a concise descriptive label
- Avoid generic tags like "article" or "content"
"""

    if existing_tags:
        prompt += f"\nExisting user tags to reuse when relevant: {', '.join(existing_tags)}\n"

    return prompt


def generate_tags(content: str, existing_tags: Optional[List[str]] = None) -> List[str]:
    """Generate only tags."""
    result = generate_tags_and_topic(content, existing_tags)
    return result["tags"]


def generate_topic(content: str) -> Optional[str]:
    """Generate only a topic label."""
    result = generate_tags_and_topic(content)
    return result["topic"]


def generate_metadata_from_content(content: str) -> dict:
    """
    Generate title, description, and tags from pasted content.

    Uses Gemini when available and falls back to deterministic text processing.
    """
    if gemini_service.is_available():
        try:
            return _generate_metadata_with_gemini(content)
        except Exception as e:
            logger.error(
                "Error generating metadata with Gemini: %s, falling back to text processing",
                str(e),
            )

    logger.info("Gemini unavailable or failed, using fallback text processing")
    return _generate_metadata_fallback(content)


def _generate_metadata_with_gemini(content: str) -> dict:
    """Generate metadata using Gemini."""
    truncated_content = content[:1500] if len(content) > 1500 else content

    prompt = f"""Analyze this content and provide metadata in JSON format.

Content: {truncated_content}

Respond with JSON only:
{{
  "title": "concise title (max 100 chars)",
  "description": "brief description (max 200 chars)",
  "tags": ["tag1", "tag2", "tag3"]
}}"""

    response = gemini_service.generate_content(
        prompt=prompt,
        model=GEMINI_MODEL_TEXT_FAST,
    )

    if not response:
        raise GeminiServiceError("Empty response from Gemini")

    metadata = _parse_json_dict(response)
    title = metadata.get("title", "Untitled")
    description = metadata.get("description", "")
    tags = metadata.get("tags", [])

    if not isinstance(title, str) or not title.strip():
        title = "Untitled"
    title = title.strip()[:100]

    if not isinstance(description, str):
        description = ""
    description = description.strip()[:200]

    if not isinstance(tags, list):
        tags = []
    tags = [str(tag).strip() for tag in tags if str(tag).strip()][:7]

    result = {
        "title": title,
        "description": description,
        "tags": tags,
    }

    logger.info(
        "Generated metadata with Gemini: title length=%s, tags=%s",
        len(result["title"]),
        len(result["tags"]),
    )
    return result


def _parse_json_dict(response_text: str) -> dict:
    """Parse Gemini JSON output, tolerating code fences and wrapper prose."""
    cleaned = response_text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    candidates = [cleaned]
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        candidates.append(cleaned[first_brace:last_brace + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            continue

    raise GeminiServiceError("Invalid JSON response from Gemini")


def _generate_metadata_fallback(content: str) -> dict:
    """
    Fallback metadata generation using basic text processing.
    """
    if not content or len(content.strip()) == 0:
        return {
            "title": "Untitled",
            "description": "",
            "tags": [],
        }

    clean_content = content.strip()
    lines = clean_content.split("\n")
    first_line = lines[0].strip() if lines else clean_content

    title = first_line.replace("#", "").replace("*", "").replace("_", "").strip()

    if len(title) > 100:
        title = title[:97] + "..."
    elif len(title) == 0:
        title = clean_content[:50] + ("..." if len(clean_content) > 50 else "")

    paragraphs = clean_content.split("\n\n")
    first_paragraph = paragraphs[0] if paragraphs else clean_content

    description = first_paragraph.replace("#", "").replace("*", "").replace("_", "").strip()
    if len(description) > 200:
        description = description[:197] + "..."

    tags = []
    lower_content = clean_content.lower()

    keyword_map = {
        "development": ["code", "programming", "developer", "software"],
        "design": ["design", "ui", "ux", "interface"],
        "ai": ["ai", "artificial intelligence", "machine learning", "llm"],
        "product": ["product", "feature", "roadmap"],
        "research": ["research", "study", "analysis"],
        "tutorial": ["tutorial", "guide", "how to", "learn"],
        "article": ["article", "blog", "post"],
    }

    for tag, keywords in keyword_map.items():
        if any(keyword in lower_content for keyword in keywords):
            tags.append(tag)

    return {
        "title": title or "Untitled",
        "description": description,
        "tags": tags[:5],
    }
