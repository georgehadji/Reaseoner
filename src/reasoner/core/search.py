"""
Reasoner - Web Discovery Tool
Provides internal web search capabilities for context enrichment.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import httpx
from urllib.parse import urlparse
from typing import Any, Optional, Literal

from reasoner.core.temperatures import NON_PHASE_TEMPERATURES
from reasoner.core.settings import settings
from reasoner.core.constants import (
    DEFAULT_SEARXNG_URL,
    TIMEOUTS,
    DEFAULT_MAX_DECOMPOSED_QUERIES,
    DEFAULT_SEARCH_RESULTS,
    TRUNCATION,
    MODEL_GPT4O_MINI,
    MODEL_GEMINI_FLASH,
)

# Deferred import to avoid circular dependencies at module load time
_build_provider = None

def _get_build_provider():
    global _build_provider
    if _build_provider is None:
        from reasoner.llm import build_provider
        _build_provider = build_provider
    return _build_provider

logger = logging.getLogger(__name__)

# Source type categories for specialized searches
SOURCE_TYPE_ENGINES: dict[str, list[str]] = {
    "general": [],  # Use default engines
    "academic": ["arxiv", "google_scholar", "crossref", "semantic_scholar", "pubmed"],
    "social": ["reddit", "twitter", "hackernews", "mastodon", "wikipedia"],
    "news": ["google_news", "bing_news", "newsapi", "ddg_news"],
    "code": ["github", "gitlab", "stackoverflow", "npm"],
}

SourceType = Literal["general", "academic", "social", "news", "code"]


# File extensions and URL patterns that are unlikely to yield readable article content
_REJECTED_EXTENSIONS = frozenset([".json", ".xml", ".csv", ".zip", ".pdf"])
_RAW_BLOB_RE = re.compile(r"/blob/[^/]+/.*\.(json|xml|csv|zip|pdf)", re.IGNORECASE)


# Known off-topic domains/patterns for high-collision acronyms
_OFF_TOPIC_PATTERNS = [
    ("nerdwallet.com", None),  # tax AGI
    ("wikipedia.org", "one big beautiful bill act"),
    ("huggingface.co", "vocab.txt"),
    ("huggingface.co", "tokenizer.json"),
    ("llm-guide.com", None),  # legal-degree LLM, not AI
    ("pluralsight.com", "best ai models"),  # generic roundup
]

# Low-signal title patterns (listicles, generic roundups, clickbait)
_LOW_SIGNAL_TITLE_RE = re.compile(
    r"(\b(top\s+(\d+\s+)?(programs|schools|universities|courses|colleges)|"
    r"top\s+\d+|best\s+\d+|\d+\s+best|\d+\s+ways?|\d+\s+ideas?|"
    r"discover\s+\d+|\d+\s+things?|\d+\s+tips?|\d+\s+reasons?)\b)",
    re.IGNORECASE,
)


def _should_include_result(result: dict[str, Any]) -> bool:
    """
    Gatekeeper for search results.
    Rejects raw data files, code blobs, off-topic domains, and snippets that are too short to be useful.
    """
    url = result.get("url", "")
    if not url:
        return False

    parsed = urlparse(url)
    path = parsed.path.lower()
    title = (result.get("title") or "").lower()

    # Reject known non-article file extensions
    if any(path.endswith(ext) for ext in _REJECTED_EXTENSIONS):
        return False

    # Reject GitHub / GitLab raw blob URLs for data files
    if _RAW_BLOB_RE.search(path):
        return False

    # Reject very short snippets (likely failed extraction or useless landing pages)
    content = (result.get("content") or "").strip()
    if len(content) < 20:
        return False

    # Reject low-signal listicles and generic roundups
    if _LOW_SIGNAL_TITLE_RE.search(title):
        return False

    # Reject known off-topic domain / pattern combinations
    netloc = parsed.netloc.lower()
    for domain_pat, title_pat in _OFF_TOPIC_PATTERNS:
        if domain_pat in netloc:
            if title_pat is None or title_pat in title:
                return False

    return True


class DiscoveryClient:
    """Client for interacting with the internal Web Discovery Engine."""

    def __init__(self, base_url: str = DEFAULT_SEARXNG_URL):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=TIMEOUTS.SEARCH_CLIENT)

    async def search(
        self,
        query: str,
        num_results: int = DEFAULT_SEARCH_RESULTS,
        categories: Optional[list[str]] = None,
        source_type: Optional[SourceType] = None,
        domain: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a discovery query and return parsed results.

        Args:
            query: The search query string
            num_results: Maximum number of results to return
            categories: Optional list of SearXNG categories to filter by
            source_type: Optional specialized source type (academic, social, news, code, general)
            domain: Optional domain to limit search to (e.g., "github.com", "stackoverflow.com")
        """
        # Handle domain-specific search using site: operator
        if domain:
            query = f"site:{domain} {query}"
        
        params: dict[str, Any] = {
            "q": query,
            "format": "json",
            "pageno": 1
        }

        # Handle source_type - map to engine filters
        if source_type and source_type != "general":
            engines = SOURCE_TYPE_ENGINES.get(source_type, [])
            if engines:
                params["engines"] = ",".join(engines)

        if categories:
            params["categories"] = ",".join(categories)

        try:
            response = await self.client.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            refined_results = []
            for r in results[:num_results]:
                content = r.get("content", "")[:TRUNCATION.SNIPPET]
                refined = {
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "content": content,
                    "snippet": content,  # Alias for compatibility
                    "source": r.get("engine"),
                    "full_content": r.get("content", ""),  # For deep reading
                }
                if _should_include_result(refined):
                    refined_results.append(refined)
                else:
                    logger.debug("Filtered out search result: %s", refined.get("url"))

            # Fallback: if strict filtering removed everything, return top unfiltered results
            if not refined_results and results:
                for r in results[:num_results]:
                    content = r.get("content", "")[:TRUNCATION.SNIPPET]
                    refined_results.append({
                        "title": r.get("title"),
                        "url": r.get("url"),
                        "content": content,
                        "snippet": content,
                        "source": r.get("engine"),
                        "full_content": r.get("content", ""),
                    })

            return refined_results
        except Exception as exc:
            logger.error("Web discovery failed: %s", exc)
            return []

    async def close(self):
        await self.client.aclose()


_default_client: Optional[DiscoveryClient] = None


def reset_discovery_client() -> None:
    """Reset the global discovery client. Call this if base_url changes.
    Schedules the old client's HTTP connection pool to be closed so that
    file descriptors are not leaked on repeated resets.
    """
    global _default_client
    old = _default_client
    _default_client = None
    if old is not None:
        # Schedule close on the running loop if one exists; otherwise best-effort.
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(old.close())
        except RuntimeError:
            # No running loop (e.g. called from synchronous context/tests).
            # Fall back to a new loop to drain the close coroutine.
            try:
                asyncio.run(old.close())
            except Exception:
                pass


_DECOMPOSITION_MODELS = [MODEL_GPT4O_MINI, MODEL_GEMINI_FLASH]


async def _decompose_query(query: str, model_id: str | None = None) -> list[str]:
    """Use a lightweight LLM to break a query into 2-3 focused sub-queries."""
    system_prompt = (
        "You are a search assistant. Given a user query, break it into 2-3 focused, "
        "standalone search queries that together cover the user's intent. "
        "Output ONLY a JSON array of strings. Do not include markdown, explanations, "
        "or code blocks.\n"
        'Example: ["query 1", "query 2"]'
    )
    build_provider = _get_build_provider()
    provider = build_provider(model_id or _DECOMPOSITION_MODELS[0])
    raw = await provider.complete_with_retry(
        system_prompt=system_prompt,
        user_prompt=query,
        max_tokens=TRUNCATION.SNIPPET,
        temperature=NON_PHASE_TEMPERATURES["search_query_generation"],
    )
    # Extract JSON array from the response
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[-1].strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    arr = json.loads(text)
    if not isinstance(arr, list):
        raise ValueError("LLM did not return a JSON array")
    # Filter out empty strings and cap at 3
    result = [str(item).strip() for item in arr if str(item).strip()]
    return result[:DEFAULT_MAX_DECOMPOSED_QUERIES]


async def smart_search(
    query: str,
    source_type: Optional[SourceType] = None,
    num_results: int = 10,
) -> list[dict[str, Any]]:
    """
    Decompose the query via a cheap LLM, run parallel SearXNG searches,
    deduplicate by URL, and return grouped results.
    Falls back to a single direct search on any failure.
    """
    client, _ = await get_discovery_client(source_type=source_type)

    sub_queries: list[str] = []
    last_error: Exception | None = None
    for model_id in _DECOMPOSITION_MODELS:
        try:
            sub_queries = await _decompose_query(query, model_id=model_id)
            if sub_queries:
                break
        except Exception as exc:
            last_error = exc
            logger.warning("Smart search decomposition with %s failed (%s). Trying fallback LLM.", model_id, exc)

    if not sub_queries:
        logger.warning(
            "Smart search decomposition failed for all LLMs (%s). Falling back to direct search.",
            last_error,
        )
        return await client.search(query, num_results=num_results, source_type=source_type)

    # Limit results per sub-query to keep total volume manageable
    per_query = max(3, num_results // len(sub_queries))

    async def _search_one(q: str) -> tuple[str, list[dict[str, Any]]]:
        results = await client.search(q, num_results=per_query, source_type=source_type)
        return q, results

    tasks = [_search_one(q) for q in sub_queries]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)

    seen_urls: set[str] = set()
    grouped_results: list[dict[str, Any]] = []

    for item in gathered:
        if isinstance(item, Exception):
            logger.warning("Smart search sub-query failed: %s", item)
            continue
        q, results = item
        for r in results:
            url = r.get("url", "")
            if url in seen_urls:
                continue
            seen_urls.add(url)
            grouped_results.append({**r, "group": q})

    # Final fallback if everything went wrong
    if not grouped_results:
        return await client.search(query, num_results=num_results, source_type=source_type)

    return grouped_results[:num_results]


def get_searxng_urls() -> list[str]:
    """Return the list of SearXNG URLs to try, respecting SEARXNG_URL env var."""
    base = os.environ.get("SEARXNG_URL", DEFAULT_SEARXNG_URL).rstrip("/")
    return [f"{base}/search", "http://127.0.0.1:8888/search"]


def get_searxng_base_url() -> str:
    """Return the configured SearXNG base URL."""
    return os.environ.get("SEARXNG_URL", DEFAULT_SEARXNG_URL).rstrip("/")


async def get_discovery_client(
    base_url: str | None = None,
    source_type: Optional[SourceType] = None,
) -> tuple[DiscoveryClient, Optional[SourceType]]:
    """
    Get or create a discovery client.
    
    Returns:
        Tuple of (client, source_type) - source_type is passed through for convenience
    """
    global _default_client
    if _default_client is None:
        resolved_base = (base_url or get_searxng_base_url()).rstrip("/")
        _default_client = DiscoveryClient(base_url=resolved_base)
    return _default_client, source_type
