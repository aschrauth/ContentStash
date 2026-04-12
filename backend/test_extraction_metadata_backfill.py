"""
Regression test for metadata fields in extract_content_with_metadata().

Ensures non-YouTube extraction returns description/image metadata so background
processing can backfill missing shortcut metadata.
"""
import asyncio

from app.services import extraction


class StubDocument:
    def __init__(self, _html: str):
        pass

    def summary(self) -> str:
        return "<div><p>" + ("content " * 250) + "</p></div>"

    def title(self) -> str:
        return "Fallback Document Title"


class StubResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self) -> None:
        return None


async def _stub_playwright_metadata(_url: str):
    return {
        "title": "Rendered Title",
        "description": "Rendered Description",
        "image_url": "https://example.com/rendered.jpg",
        "favicon_url": "https://example.com/rendered.ico",
    }


def test_extract_content_with_metadata_returns_page_metadata(monkeypatch):
    test_url = "https://example.com/article"

    monkeypatch.setattr(
        extraction,
        "fetch_metadata",
        lambda _url: {
            "title": "OG Title",
            "description": "OG Description",
            "image_url": "https://example.com/cover.jpg",
            "favicon_url": "https://example.com/favicon.ico",
        },
    )
    monkeypatch.setattr(extraction.requests, "get", lambda *_args, **_kwargs: StubResponse("<html></html>"))
    monkeypatch.setattr(extraction, "Document", StubDocument)

    result = asyncio.run(extraction.extract_content_with_metadata(test_url, extraction_type="fast"))

    assert result["text"]
    assert result["title"] == "OG Title"
    assert result["description"] == "OG Description"
    assert result["image_url"] == "https://example.com/cover.jpg"
    assert result["favicon_url"] == "https://example.com/favicon.ico"


def test_extract_content_with_metadata_uses_playwright_metadata_when_requests_metadata_missing(monkeypatch):
    test_url = "https://example.com/blocked"

    monkeypatch.setattr(
        extraction,
        "fetch_metadata",
        lambda _url: {
            "title": None,
            "description": None,
            "image_url": None,
            "favicon_url": None,
        },
    )
    monkeypatch.setattr(extraction, "_extract_page_metadata_with_playwright", _stub_playwright_metadata)
    monkeypatch.setattr(extraction, "_extract_with_playwright", lambda _url: asyncio.sleep(0, result="Rendered content"))
    monkeypatch.setattr(extraction.requests, "get", lambda *_args, **_kwargs: StubResponse("<html></html>"))
    monkeypatch.setattr(extraction, "Document", StubDocument)

    result = asyncio.run(extraction.extract_content_with_metadata(test_url, extraction_type="complete"))

    assert result["text"]
    assert result["title"] == "Rendered Title"
    assert result["description"] == "Rendered Description"
    assert result["image_url"] == "https://example.com/rendered.jpg"
    assert result["favicon_url"] == "https://example.com/rendered.ico"


def test_extract_content_with_metadata_youtube_returns_transcript_and_metadata(monkeypatch):
    test_url = "https://www.youtube.com/watch?v=abc123xyz00"

    monkeypatch.setattr(extraction, "extract_video_id", lambda _url: "abc123xyz00")
    monkeypatch.setattr(extraction, "get_video_transcript", lambda _vid: "This is the transcript")
    monkeypatch.setattr(extraction, "get_transcript_from_ytdlp", lambda _vid: None)
    monkeypatch.setattr(
        extraction,
        "get_video_metadata_from_api",
        lambda _vid, _api_key: {
            "title": "Video Title",
            "description": "Video Description",
            "thumbnail_url": "https://img.youtube.com/test.jpg",
            "channel_name": "Channel Name",
            "published_at": "2026-01-01T00:00:00Z",
        },
    )
    monkeypatch.setattr(extraction, "get_video_metadata_from_ytdlp", lambda _vid: None)
    monkeypatch.setattr(extraction, "settings", type("S", (), {"youtube_api_key": None})())

    result = asyncio.run(extraction.extract_content_with_metadata(test_url, extraction_type="fast"))

    assert result["text"] == "This is the transcript"
    assert result["title"] == "Video Title"
    assert result["description"] == "Video Description"
    assert result["image_url"] == "https://img.youtube.com/test.jpg"
    assert result["favicon_url"] == "https://www.youtube.com/favicon.ico"
    assert result["source"] == "YouTube | Channel Name"


def test_merge_metadata_ignores_block_page_values():
    merged = extraction._merge_metadata(
        {
            "title": "Just a moment...",
            "description": "Enable JavaScript and cookies to continue",
            "image_url": None,
            "favicon_url": None,
        },
        {
            "title": "OG Title",
            "description": "OG Description",
            "image_url": "https://example.com/cover.jpg",
            "favicon_url": "https://example.com/favicon.ico",
        },
    )

    assert merged["title"] == "OG Title"
    assert merged["description"] == "OG Description"
    assert merged["image_url"] == "https://example.com/cover.jpg"
    assert merged["favicon_url"] == "https://example.com/favicon.ico"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
