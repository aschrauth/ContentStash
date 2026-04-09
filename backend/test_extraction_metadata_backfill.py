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

    result = asyncio.run(extraction.extract_content_with_metadata(test_url, extraction_type="fast"))

    assert result["text"] == "This is the transcript"
    assert result["title"] == "Video Title"
    assert result["description"] == "Video Description"
    assert result["image_url"] == "https://img.youtube.com/test.jpg"
    assert result["favicon_url"] == "https://www.youtube.com/favicon.ico"
    assert result["source"] == "YouTube | Channel Name"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
