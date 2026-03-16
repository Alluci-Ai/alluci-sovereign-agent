
import os
import httpx
import logging
from ..logging_config import get_logger
from typing import Dict, Any, List
from .base import Adapter

class WebSearchAdapter(Adapter):
    """
    Web Search Adapter.
    Supports SerpAPI, Brave Search API, and DuckDuckGo (no key required).

    Provider priority:
      - provider="brave"  → Brave Search API (requires api_key); falls back to DDG on error.
      - provider="serpapi" → SerpAPI Google (requires api_key); no fallback.
      - provider="ddg"    → DuckDuckGo (free, no key required).
      - No api_key set    → DDG automatically.
    """
    name = "web_search"
    description = "Search the web for real-time information. Supports Brave, SerpAPI, and DDG."

    def __init__(self, api_key: str = None, provider: str = "serpapi"):
        self.api_key = api_key
        self.provider = provider
        self.logger = get_logger("WebSearchAdapter")

    async def execute(self, query: str) -> Dict[str, Any]:
        """Route the query to the appropriate search provider."""
        if not query or not str(query).strip():
            return {"status": "error", "message": "No query provided."}

        query = str(query).strip()

        try:
            # No API key → use DDG regardless of configured provider
            if not self.api_key:
                self.logger.info(f"No API key set — using DDG fallback for: {query!r}")
                return await self._search_ddg(query)

            if self.provider == "serpapi":
                return await self._search_serpapi(query)

            elif self.provider == "brave":
                # Attempt Brave; fall back to DDG if the API call fails
                try:
                    return await self._search_brave(query)
                except Exception as brave_err:
                    self.logger.warning(f"Brave search failed ({brave_err}); falling back to DDG.")
                    return await self._search_ddg(query)

            elif self.provider == "ddg":
                return await self._search_ddg(query)

            else:
                return {"status": "error", "message": f"Unknown provider: {self.provider!r}. Use 'brave', 'serpapi', or 'ddg'."}

        except Exception as e:
            self.logger.error(f"Web search failed for {query!r}: {e}")
            return {"status": "error", "message": str(e)}

    # ── SerpAPI ───────────────────────────────────────────────────────────────

    async def _search_serpapi(self, query: str) -> Dict[str, Any]:
        """Google search via SerpAPI. Requires SERPAPI_KEY."""
        url = "https://serpapi.com/search"
        params = {"q": query, "api_key": self.api_key, "engine": "google", "num": 5}

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("organic_results", [])
            return {
                "status": "success",
                "provider": "serpapi",
                "query": query,
                "results": [
                    {"title": r.get("title", ""), "link": r.get("link", ""), "snippet": r.get("snippet", "")}
                    for r in results[:5]
                ],
            }

    # ── Brave Search ──────────────────────────────────────────────────────────

    async def _search_brave(self, query: str) -> Dict[str, Any]:
        """
        Brave Search API — privacy-first web search.
        Docs: https://api.search.brave.com/app/documentation/web-search
        Requires: BRAVE_SEARCH_API_KEY (set as api_key on this adapter).
        """
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
        }
        params = {
            "q": query,
            "count": 5,
            "safesearch": "moderate",
            "search_lang": "en",
            "text_decorations": False,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("web", {}).get("results", [])
            return {
                "status": "success",
                "provider": "brave",
                "query": query,
                "results": [
                    {
                        "title": r.get("title", ""),
                        "link": r.get("url", ""),
                        "snippet": r.get("description", ""),
                    }
                    for r in items[:5]
                ],
            }

    # ── DuckDuckGo (free fallback) ─────────────────────────────────────────────

    async def _search_ddg(self, query: str) -> Dict[str, Any]:
        """
        DuckDuckGo search via duckduckgo-search library.
        No API key required. Install: pip install duckduckgo-search>=6.0.0
        """
        try:
            from duckduckgo_search import AsyncDDGS
            async with AsyncDDGS() as ddgs:
                raw = await ddgs.atext(query, max_results=5)
                if not raw:
                    return {"status": "success", "provider": "ddg", "query": query, "results": []}
                return {
                    "status": "success",
                    "provider": "ddg",
                    "query": query,
                    "results": [
                        {
                            "title": r.get("title", ""),
                            "link": r.get("href", ""),
                            "snippet": r.get("body", ""),
                        }
                        for r in raw
                    ],
                }

        except ImportError:
            self.logger.error("duckduckgo-search not installed. Run: pip install duckduckgo-search>=6.0.0")
            return {
                "status": "error",
                "provider": "ddg",
                "message": "duckduckgo-search package not installed. Add it to requirements.txt.",
            }
        except Exception as e:
            self.logger.error(f"DDG search failed: {e}")
            return {"status": "error", "provider": "ddg", "message": str(e)}
