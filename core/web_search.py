"""Small, optional public web search for questions beyond the PDFs."""

import asyncio
import logging
from urllib.parse import urlparse

import config

logger = logging.getLogger(__name__)


def _search(question: str) -> list[dict]:
    from ddgs import DDGS

    results = DDGS(timeout=5).text(question, max_results=4)
    sources = []
    for item in results:
        url = str(item.get("href") or "").strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            continue
        if parsed.hostname in {"localhost", "127.0.0.1"}:
            continue
        title = str(item.get("title") or parsed.hostname).strip()[:160]
        snippet = str(item.get("body") or "").strip()[:450]
        if not snippet:
            continue
        sources.append({
            "kind": "web", "index": len(sources) + 1,
            "title": title, "url": url, "text_preview": snippet,
        })
        if len(sources) == 3:
            break
    return sources


async def search_web(question: str) -> list[dict]:
    """Return a few attributed snippets; fail open when search is unavailable."""
    if not config.WEB_SEARCH_ENABLED:
        return []
    try:
        return await asyncio.wait_for(asyncio.to_thread(_search, question), timeout=8)
    except Exception as exc:
        logger.info("Web search unavailable: %s", type(exc).__name__)
        return []


def web_context(sources: list[dict]) -> str:
    return "\n".join(
        f"[{source['index']}] {source['title']} ({source['url']})\n"
        f"Excerpt: {source['text_preview']}"
        for source in sources
    )
