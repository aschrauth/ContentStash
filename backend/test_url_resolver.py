"""
Smoke tests for intermediary URL resolution.

Run with:
    python test_url_resolver.py
"""
from app.services.url_resolver import _extract_from_html, is_intermediary_url, looks_like_intermediary_title


def test_apple_news_open_story_link():
    html = """
    <html>
      <body>
        <h1>Opening story...</h1>
        <a href="https://www.cnbc.com/2026/04/21/example-story.html">Click here Tap here</a>
        <a href="https://www.apple.com/apple-news/">Learn more about Apple News</a>
      </body>
    </html>
    """

    resolved = _extract_from_html(html, "https://apple.news/Aje359rm2R-CwOnJCHxrFNA", "https://apple.news/Aje359rm2R-CwOnJCHxrFNA")
    assert resolved == "https://www.cnbc.com/2026/04/21/example-story.html"


def test_flipboard_script_source_url():
    html = """
    <html>
      <body>
        <script>
          window.__DATA__ = {"sourceUrl":"https:\\/\\/www.example.com\\/news\\/real-article"};
        </script>
      </body>
    </html>
    """

    resolved = _extract_from_html(html, "https://flip.it/BLmDMT", "https://flip.it/BLmDMT")
    assert resolved == "https://www.example.com/news/real-article"


def test_intermediary_detection_helpers():
    assert is_intermediary_url("https://apple.news/Aje359rm2R-CwOnJCHxrFNA")
    assert is_intermediary_url("https://flip.it/BLmDMT")
    assert not is_intermediary_url("https://www.cnbc.com/2026/04/21/example-story.html")
    assert looks_like_intermediary_title("Opening story...")
    assert looks_like_intermediary_title("Apple News")
    assert not looks_like_intermediary_title("Real Article Headline")


if __name__ == "__main__":
    test_apple_news_open_story_link()
    test_flipboard_script_source_url()
    test_intermediary_detection_helpers()
    print("URL resolver tests passed")
