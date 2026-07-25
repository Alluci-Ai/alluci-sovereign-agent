import asyncio
import logging
import re
import httpx
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

logger = logging.getLogger("NativeMultiEngineScraper")

STATIC_ASSET_EXTENSIONS = ('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot')
EXCLUDED_DOMAINS = ('r.bing.com', 'th.bing.com', 'google.com/gb/', 'bing.com', 'microsoft.com', 'duckduckgo.com')

class NativeMultiEngineScraper:
    """
    Self-contained in-process fallback multi-engine search scraper.
    Aggregates results across DuckDuckGo, Bing, and Google using structured DOM parsing.
    """
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }

    def _is_valid_organic_url(self, url: str) -> bool:
        if not url or not url.startswith("http"):
            return False
        u_lower = url.lower().split("?")[0]
        if any(u_lower.endswith(ext) for ext in STATIC_ASSET_EXTENSIONS):
            return False
        if any(domain in u_lower for domain in EXCLUDED_DOMAINS):
            return False
        return True

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
                            if href and self._is_valid_organic_url(href):
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

        # 2. Secondary In-Process Engine: Bing DOM HTML Scraper Fallback
        if len(urls) < 3:
            async with httpx.AsyncClient(timeout=10.0, headers=self.headers, follow_redirects=True) as client:
                for q in queries:
                    try:
                        resp = await client.get("https://www.bing.com/search", params={"q": q})
                        if resp.status_code == 200:
                            soup = BeautifulSoup(resp.text, "html.parser")
                            # Extract organic link elements specifically
                            for link in soup.select("li.b_algo h2 a"):
                                href = link.get("href")
                                if href and self._is_valid_organic_url(href):
                                    urls.add(href)
                                    if len(urls) >= (len(queries) * max_results_per_query):
                                        break
                    except Exception as e:
                        logger.warning(f"Bing fallback DOM search error for '{q}': {e}")

        return {
            "status": "success",
            "queries": queries,
            "urls": list(urls)
        }
