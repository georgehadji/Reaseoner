"""
Reasoner - Web Discovery Tool
Provides internal web search capabilities for context enrichment.
"""

from __future__ import annotations

import asyncio
import logging
import httpx
from typing import Any, Optional, Literal

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


class DiscoveryClient:
    """Client for interacting with the internal Web Discovery Engine."""

    def __init__(self, base_url: str = "http://localhost:8888"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def search(
        self,
        query: str,
        num_results: int = 10,
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
                content = r.get("content", "")[:500]
                refined_results.append({
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "content": content,
                    "snippet": content,  # Alias for compatibility
                    "source": r.get("engine"),
                    "full_content": r.get("content", ""),  # For deep reading
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


async def get_discovery_client(
    base_url: str = "http://localhost:8888",
    source_type: Optional[SourceType] = None,
) -> tuple[DiscoveryClient, Optional[SourceType]]:
    """
    Get or create a discovery client.
    
    Returns:
        Tuple of (client, source_type) - source_type is passed through for convenience
    """
    global _default_client
    if _default_client is None:
        _default_client = DiscoveryClient(base_url=base_url)
    return _default_client, source_type
