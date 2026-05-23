"""
Resolve article-wrapper URLs before content extraction.

Some share surfaces hand ContentStash a lightweight landing page instead of the
publisher page. Apple News and Flipboard are the common cases: their HTML often
contains a single "open/read story" link to the real article.
"""
from __future__ import annotations

import html
import logging
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import parse_qsl, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from app.services.playwright_runtime import (
    LOW_MEMORY_CHROMIUM_ARGS,
    abort_heavy_resources,
    get_playwright_semaphore,
    playwright_is_enabled,
)

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

INTERMEDIARY_DOMAINS = (
    "apple.news",
    "flip.it",
    "flipboard.com",
)

IGNORED_TARGET_DOMAINS = (
    "apple.com",
    "itunes.apple.com",
    "apps.apple.com",
    "flipboard.com",
    "flip.it",
    "facebook.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "pinterest.com",
)

URL_PARAMETER_KEYS = {
    "url",
    "u",
    "target",
    "target_url",
    "redirect",
    "redirect_url",
    "destination",
    "link",
    "link_url",
    "article",
    "article_url",
}

TARGET_LINK_TEXT = re.compile(
    r"\b(click|tap|open|read|continue|view|source|original|story|article)\b",
    re.IGNORECASE,
)

SCRIPT_URL_KEYS = re.compile(
    r"""
    (?:
        originalUrl|original_url|
        sourceUrl|sourceURL|source_url|
        articleUrl|article_url|
        canonicalUrl|canonical_url|
        targetUrl|target_url|
        externalUrl|external_url|
        redirectUrl|redirect_url
    )
    ["']?\s*[:=]\s*["']([^"']+)
    """,
    re.IGNORECASE | re.VERBOSE,
)

GENERIC_URL = re.compile(r"https?:\\?/\\?/[^\"'<>\s)]+", re.IGNORECASE)


@dataclass(frozen=True)
class URLResolution:
    original_url: str
    url: str
    was_resolved: bool
    method: str = "unchanged"


def _hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().removeprefix("www.")
    except Exception:
        return ""


def is_intermediary_url(url: Optional[str]) -> bool:
    if not url:
        return False

    host = _hostname(url)
    if not host:
        return False

    return any(host == domain or host.endswith(f".{domain}") for domain in INTERMEDIARY_DOMAINS)


def looks_like_intermediary_title(title: Optional[str], original_url: Optional[str] = None) -> bool:
    if not title:
        return True

    normalized = " ".join(title.split()).strip().lower()
    if not normalized:
        return True

    if original_url and normalized == original_url.lower():
        return True

    return any(
        marker in normalized
        for marker in (
            "opening story",
            "tap here if the story",
            "click here if the story",
            "apple news",
            "flipboard",
        )
    )


def _is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def _clean_candidate_url(value: str, base_url: str) -> Optional[str]:
    if not value:
        return None

    cleaned = html.unescape(value).replace("\\/", "/").strip().strip("'\"")
    cleaned = unquote(cleaned)
    absolute = urljoin(base_url, cleaned)

    if not _is_http_url(absolute):
        return None

    return absolute


def _is_ignored_target(url: str) -> bool:
    host = _hostname(url)
    if not host:
        return True

    return any(host == domain or host.endswith(f".{domain}") for domain in IGNORED_TARGET_DOMAINS)


def _is_candidate_target(candidate: Optional[str], original_url: str) -> bool:
    if not candidate:
        return False

    if candidate.rstrip("/") == original_url.rstrip("/"):
        return False

    if is_intermediary_url(candidate):
        return False

    if _is_ignored_target(candidate):
        return False

    parsed = urlparse(candidate)
    if parsed.path.lower().endswith((".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico")):
        return False

    return True


def _candidate_from_query(url: str, base_url: str) -> Optional[str]:
    parsed = urlparse(url)
    for key, value in parse_qsl(parsed.query, keep_blank_values=False):
        if key.lower() not in URL_PARAMETER_KEYS:
            continue

        candidate = _clean_candidate_url(value, base_url)
        if _is_candidate_target(candidate, url):
            return candidate

    return None


def _score_anchor(text: str, url: str) -> int:
    score = 0
    if TARGET_LINK_TEXT.search(text):
        score += 100

    parsed = urlparse(url)
    if len([part for part in parsed.path.split("/") if part]) >= 2:
        score += 20

    if re.search(r"\.(html?|amp)$", parsed.path, re.IGNORECASE):
        score += 10

    if len(text.strip()) > 25:
        score += 5

    return score


def _extract_from_html(page_html: str, page_url: str, original_url: str) -> Optional[str]:
    soup = BeautifulSoup(page_html or "", "html.parser")

    query_candidate = _candidate_from_query(page_url, page_url)
    if query_candidate:
        return query_candidate

    for meta in soup.find_all("meta", attrs={"http-equiv": re.compile("^refresh$", re.IGNORECASE)}):
        content = meta.get("content", "")
        match = re.search(r"url\s*=\s*([^;]+)", content, re.IGNORECASE)
        if match:
            candidate = _clean_candidate_url(match.group(1), page_url)
            if _is_candidate_target(candidate, original_url):
                return candidate

    for selector in (
        "meta[property='og:url']",
        "meta[name='twitter:url']",
        "link[rel='canonical']",
        "link[rel='amphtml']",
    ):
        element = soup.select_one(selector)
        value = element.get("content") or element.get("href") if element else None
        candidate = _clean_candidate_url(value or "", page_url)
        if _is_candidate_target(candidate, original_url):
            return candidate

    anchor_candidates: list[tuple[int, str]] = []
    for anchor in soup.find_all("a", href=True):
        candidate = _clean_candidate_url(anchor.get("href") or "", page_url)
        if not _is_candidate_target(candidate, original_url):
            continue

        text = anchor.get_text(" ", strip=True)
        anchor_candidates.append((_score_anchor(text, candidate), candidate))

    if anchor_candidates:
        anchor_candidates.sort(key=lambda item: item[0], reverse=True)
        return anchor_candidates[0][1]

    for script in soup.find_all("script"):
        script_text = script.string or script.get_text(" ", strip=True) or ""
        for match in SCRIPT_URL_KEYS.finditer(script_text):
            candidate = _clean_candidate_url(match.group(1), page_url)
            if _is_candidate_target(candidate, original_url):
                return candidate

        for match in GENERIC_URL.finditer(script_text):
            candidate = _clean_candidate_url(match.group(0), page_url)
            if _is_candidate_target(candidate, original_url):
                return candidate

    return None


async def _resolve_with_playwright(url: str, timeout_ms: int = 30000) -> Optional[str]:
    if not playwright_is_enabled():
        logger.info(f"Skipping Playwright intermediary URL resolution because server Playwright is disabled for {url}")
        return None

    try:
        async with get_playwright_semaphore():
            async with async_playwright() as p:
                browser = None
                context = None
                try:
                    browser = await p.chromium.launch(headless=True, args=LOW_MEMORY_CHROMIUM_ARGS)
                    context = await browser.new_context(
                        user_agent=HEADERS["User-Agent"],
                        locale="en-US",
                        viewport={"width": 1024, "height": 768},
                    )
                    await context.route("**/*", abort_heavy_resources)
                    page = await context.new_page()
                    await page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(750)

                    if page.url and not is_intermediary_url(page.url):
                        return page.url

                    page_html = await page.content()
                    candidate = _extract_from_html(page_html, page.url or url, url)
                    if candidate:
                        await page.goto(candidate, wait_until="domcontentloaded", timeout=20000)
                        await page.wait_for_timeout(250)
                        return page.url or candidate

                    return None
                finally:
                    if context:
                        await context.close()
                    if browser:
                        await browser.close()
    except Exception as e:
        logger.warning(f"Playwright intermediary URL resolution failed for {url}: {str(e)}")
        return None


async def resolve_intermediary_url(url: str, timeout: int = 10, use_playwright: bool = True) -> URLResolution:
    """
    Resolve known article-wrapper URLs to their publisher URL.

    The function is intentionally conservative: it only runs on known wrapper
    domains and ignores links back to Apple, Flipboard, social sites, or assets.
    """
    if not is_intermediary_url(url):
        return URLResolution(original_url=url, url=url, was_resolved=False)

    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)

        if response.url and not is_intermediary_url(response.url):
            logger.info(f"Resolved intermediary URL via HTTP redirect: {url} -> {response.url}")
            return URLResolution(original_url=url, url=response.url, was_resolved=True, method="http_redirect")

        response.raise_for_status()

        candidate = _extract_from_html(response.text, response.url or url, url)
        if candidate:
            logger.info(f"Resolved intermediary URL via HTML link: {url} -> {candidate}")
            return URLResolution(original_url=url, url=candidate, was_resolved=True, method="html_link")
    except requests.RequestException as e:
        logger.warning(f"HTTP intermediary URL resolution failed for {url}: {str(e)}")
    except Exception as e:
        logger.warning(f"Unexpected intermediary URL resolution error for {url}: {str(e)}")

    if use_playwright:
        candidate = await _resolve_with_playwright(url)
        if candidate and not is_intermediary_url(candidate):
            logger.info(f"Resolved intermediary URL via Playwright: {url} -> {candidate}")
            return URLResolution(original_url=url, url=candidate, was_resolved=True, method="playwright")

    return URLResolution(original_url=url, url=url, was_resolved=False)
