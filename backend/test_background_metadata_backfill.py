"""
Regression test for shortcut items whose initial title is just the URL.

Ensures background processing replaces the placeholder URL title and fills the
other metadata fields when extraction succeeds.
"""
import asyncio
from datetime import datetime

from bson import ObjectId

from app.services import background


class FakeSavedItemsCollection:
    def __init__(self, item_doc: dict):
        self.item_doc = item_doc

    async def find_one(self, query: dict):
        if query.get("_id") == self.item_doc["_id"]:
            return dict(self.item_doc)
        return None

    async def update_one(self, query: dict, update: dict):
        if query.get("_id") != self.item_doc["_id"]:
            return None

        for key, value in update.get("$set", {}).items():
            self.item_doc[key] = value

        class Result:
            modified_count = 1

        return Result()


class FakeDatabase:
    def __init__(self, item_doc: dict):
        self.saved_items = FakeSavedItemsCollection(item_doc)


async def _fake_extract_metadata_only(_url: str) -> dict:
    return {
        "text": None,
        "title": "Rendered Article Title",
        "description": "Rendered Article Description",
        "image_url": "https://example.com/rendered.jpg",
        "favicon_url": "https://example.com/favicon.ico",
        "source": "people.com",
    }


async def _fake_extract_content(_url: str, extraction_type: str = "fast"):
    return ("Rendered article body " * 80, extraction_type)


def test_process_item_background_replaces_placeholder_url_title(monkeypatch):
    user_id = ObjectId()
    item_id = ObjectId()
    test_url = "https://people.com/example-article"

    item_doc = {
        "_id": item_id,
        "owner_id": user_id,
        "url": test_url,
        "title": test_url,
        "description": None,
        "image_url": None,
        "favicon_url": None,
        "archived_text": None,
        "notes_markdown": None,
        "tags": [],
        "processing_status": "pending",
        "processing_error": None,
        "extraction_type": "complete",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    fake_db = FakeDatabase(item_doc)

    monkeypatch.setattr(background, "get_database", lambda: fake_db)
    monkeypatch.setattr(background, "extract_metadata_only", _fake_extract_metadata_only)
    monkeypatch.setattr(background, "extract_content", _fake_extract_content)
    monkeypatch.setattr(background, "generate_tags_and_topic", lambda *_args, **_kwargs: {"tags": [], "topic": None})
    monkeypatch.setattr(background, "generate_auto_categorization", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(background, "is_youtube_url", lambda _url: False)
    monkeypatch.setattr(background.gemini_service, "is_available", lambda: False)

    asyncio.run(background.process_item_background(str(item_id), str(user_id)))

    assert item_doc["processing_status"] == "processed"
    assert item_doc["title"] == "Rendered Article Title"
    assert item_doc["description"] == "Rendered Article Description"
    assert item_doc["image_url"] == "https://example.com/rendered.jpg"
    assert item_doc["favicon_url"] == "https://example.com/favicon.ico"
    assert item_doc["source"] == "people.com"
