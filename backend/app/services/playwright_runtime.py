"""
Shared Playwright runtime controls for memory-constrained deployments.
"""
import asyncio
import logging

from playwright.async_api import Route

from app.config import settings

logger = logging.getLogger(__name__)

_playwright_semaphore = asyncio.Semaphore(max(1, settings.playwright_max_concurrency))

LOW_MEMORY_CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-background-timer-throttling",
    "--disable-client-side-phishing-detection",
    "--disable-default-apps",
    "--disable-features=site-per-process,Translate,BackForwardCache",
    "--disable-hang-monitor",
    "--disable-popup-blocking",
    "--disable-prompt-on-repost",
    "--disable-renderer-backgrounding",
    "--disable-sync",
    "--metrics-recording-only",
    "--mute-audio",
    "--no-first-run",
    "--no-zygote",
]

BLOCKED_RESOURCE_TYPES = {"media", "font"}


def playwright_is_enabled() -> bool:
    return settings.server_playwright_enabled


def get_playwright_semaphore() -> asyncio.Semaphore:
    return _playwright_semaphore


async def abort_heavy_resources(route: Route) -> None:
    """Abort resource types that add memory without helping text extraction."""
    if settings.playwright_block_images and route.request.resource_type == "image":
        await route.abort()
        return

    if (
        settings.playwright_block_heavy_resources
        and route.request.resource_type in BLOCKED_RESOURCE_TYPES
    ):
        await route.abort()
        return

    await route.continue_()
