"""
Regression test for TownNews/BLOX article cleanup.

Verifies that the extractor keeps the headline, image captions, and article body
while dropping social links, tag chips, author promos, and post-article widgets.
"""
import os

from markdownify import markdownify as md

os.environ.setdefault("MONGODB_URI", "mongodb://localhost/test")
os.environ.setdefault("JWT_SECRET", "test")

from app.services.extraction import (
    _clean_extracted_content,
    _extract_static_article_content,
    _extract_townnews_article_html,
)


SAMPLE_HTML = """
<html>
  <head>
    <meta name="tncms-access-version" content="2026-02-12 15:44:11" />
  </head>
  <body>
    <article class="asset">
      <div class="asset-headline"><span>Fixes explored for Napa's Highway 29 traffic chokepoint</span></div>
      <div id="asset-photo-carousel">
        <div class="caption-text"><div class="subscriber-preview"><p>Traffic on southbound Highway 29 makes its way towards the intersection.</p></div></div>
        <div class="caption-text"><div class="subscriber-preview"><p>This diagram shows the displaced left turn option.</p></div></div>
      </div>
      <div class="share-container">
        <a href="https://facebook.example/share">Facebook</a>
        <a href="https://twitter.example/share">Twitter</a>
      </div>
      <div id="article-body" itemprop="articleBody">
        <div class="subscriber-preview"><p>Visions of a possible fix are becoming clearer.</p></div>
        <div class="subscriber-only" style="display:none"><p>All three keep traffic signals.</p></div>
      </div>
      <div class="asset-tagline"><p>You can reach Barry Eberling at 707-256-2253 or barry.eberling@napanews.com.</p></div>
      <div class="asset-tags"><h4>Tags</h4><a href="/search">Traffic</a></div>
      <div class="asset-author">Follow Barry Eberling</div>
      <div class="btm-of-article"><h3>Most Popular</h3></div>
    </article>
  </body>
</html>
"""


def test_townnews_article_cleanup():
    extracted_html = _extract_townnews_article_html(SAMPLE_HTML)

    assert extracted_html is not None
    markdown = md(extracted_html, heading_style="ATX", strip=["script", "style", "nav", "header", "footer"])
    cleaned = _clean_extracted_content(markdown)

    assert "Fixes explored for Napa's Highway 29 traffic chokepoint" in cleaned
    assert "Traffic on southbound Highway 29 makes its way towards the intersection." in cleaned
    assert "This diagram shows the displaced left turn option." in cleaned
    assert "Visions of a possible fix are becoming clearer." in cleaned
    assert "All three keep traffic signals." in cleaned

    assert "Facebook" not in cleaned
    assert "Twitter" not in cleaned
    assert "Tags" not in cleaned
    assert "Follow Barry Eberling" not in cleaned
    assert "Most Popular" not in cleaned
    assert "You can reach Barry Eberling" not in cleaned


def test_static_townnews_article_extraction():
    class StubResponse:
        text = SAMPLE_HTML.replace(
            "Visions of a possible fix are becoming clearer.",
            " ".join(["Visions of a possible fix are becoming clearer."] * 20),
        )

        def raise_for_status(self) -> None:
            return None

    from app.services import extraction

    original_get = extraction.requests.get
    extraction.requests.get = lambda *_args, **_kwargs: StubResponse()
    try:
        cleaned = _extract_static_article_content("https://example.com/article", townnews_only=True)
    finally:
        extraction.requests.get = original_get

    assert cleaned is not None
    assert "Fixes explored for Napa's Highway 29 traffic chokepoint" in cleaned
    assert "Visions of a possible fix are becoming clearer." in cleaned
    assert "Most Popular" not in cleaned


if __name__ == "__main__":
    test_townnews_article_cleanup()
    test_static_townnews_article_extraction()
    print("TownNews cleanup test passed")
