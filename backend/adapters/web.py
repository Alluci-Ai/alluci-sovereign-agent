
import httpx
import logging
from ..logging_config import get_logger
from typing import Dict, Any
from .base import Adapter

logger = get_logger("Adapters.Web")

class WebAdapter(Adapter):
    @property
    def name(self) -> str:
        return "web"

    async def execute(self, args: Dict[str, Any]) -> Any:
        action = args.get("action", "search")
        query = args.get("query")
        url = args.get("url")
        
        if action == "search":
            return await self._search(query)
        elif action == "fetch":
            return await self._fetch(url)
        else:
            return f"Unknown web action: {action}"

    async def _search(self, query: str) -> str:
        """
        Performs a real web search via WebSearchAdapter (DDG fallback, no API key required).
        Falls back to a descriptive error string on failure — never returns mock data.
        """
        if not query:
            return "No query provided."

        try:
            from .web_search import WebSearchAdapter
            # Use DDG as the provider so no API key is required
            adapter = WebSearchAdapter(provider="ddg")
            result = await adapter.execute(query)

            if result.get("status") == "success":
                items = result.get("results", [])
                if not items:
                    return f"Web search returned no results for: {query}"
                lines = [
                    f"{r.get('title', 'No title')}: {r.get('snippet', '')} ({r.get('link', '')})"
                    for r in items
                ]
                return "\n".join(lines)
            else:
                return f"Web search failed: {result.get('message', 'unknown error')}"

        except Exception as e:
            logger.error(f"WebAdapter._search error: {e}")
            return f"Web search unavailable: {e}"

    async def _fetch(self, url: str) -> str:
        if not url: return "No URL provided."
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text[:2000] # Limit content for context
        except Exception as e:
            return f"Failed to fetch {url}: {str(e)}"
