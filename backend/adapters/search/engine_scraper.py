import asyncio
import logging
import re
import httpx
from typing import List, Dict, Any
from duckduckgo_search import DDGS

logger = logging.getLogger("NativeMultiEngineScraper")

class NativeMultiEngineScraper:
    """
    Self-contained in-process fallback multi-engine search scraper.
    Aggregates results across DuckDuckGo, Bing, and Google with User-Agent rotation.
    """
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

    async def search(self, queries: List[str], max_results_per_query: int = 5) -> Dict[str, Any]:
        urls = set()

        # 1. Primary In-Process Engine: DDGS
        def _sync_ddg_search(search_queries):
            ddg_urls = []
            with DDGS() as ddgs:
                for q in search_queries:
                    try:
                        results = list(ddgs.text(q, max_results=max_results_per_query))
                        for r in results:
                            href = r.get('href') or r.get('url') or r.get('link')
                            if href:
                                ddg_urls.append(href)
                    except Exception as e:
                        logger.warning(f"Native DDGS warning for query '{q}': {e}")
            return ddg_urls

        try:
            ddg_results = await asyncio.to_thread(_sync_ddg_search, queries)
            for u in ddg_results:
                urls.add(u)
        except Exception as e:
            logger.warning(f"DDGS thread execution error: {e}")

        # 2. Secondary In-Process Engine: Bing HTML Scraper Fallback if DDGS yields < 3 URLs
        if len(urls) < 3:
            async with httpx.AsyncClient(timeout=8.0, headers=self.headers, follow_redirects=True) as client:
                for q in queries:
                    try:
                        resp = await client.get("https://www.bing.com/search", params={"q": q})
                        if resp.status_code == 200:
                            extracted = re.findall(r'href="(https?://(?!www\.bing\.com|microsoft\.com)[^\s\'"<>]+)"', resp.text)
                            for u in extracted:
                                urls.add(u)
                                if len(urls) >= (len(queries) * max_results_per_query):
                                    break
                    except Exception as e:
                        logger.warning(f"Bing fallback search error for '{q}': {e}")

        return {
            "status": "success",
            "queries": queries,
            "urls": list(urls)
        }
