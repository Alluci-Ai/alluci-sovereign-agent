import asyncio
import logging
import re
import urllib.parse
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

logger = logging.getLogger("NativeMultiEngineScraper")

STATIC_ASSET_EXTENSIONS = ('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot')
EXCLUDED_DOMAINS = ('r.bing.com', 'th.bing.com', 'google.com', 'bing.com', 'microsoft.com', 'duckduckgo.com', 'youtube.com/watch')

class NativeMultiEngineScraper:
    """
    Self-contained in-process multi-engine search scraper.
    Uses Scrapling StealthyFetcher to bypass CAPTCHAs across Google, Bing, and DuckDuckGo.
    """
    def __init__(self):
        pass

    def _is_valid_organic_url(self, url: str) -> bool:
        if not url or not url.startswith("http"):
            return False
        u_lower = url.lower().split("?")[0]
        if any(u_lower.endswith(ext) for ext in STATIC_ASSET_EXTENSIONS):
            return False
        if any(domain in u_lower for domain in EXCLUDED_DOMAINS):
            return False
        return True

    def _fetch_stealth_search_urls(self, queries: List[str], max_results_per_query: int = 5) -> List[str]:
        found_urls = set()
        try:
            from scrapling.fetchers import StealthyFetcher
            for q in queries:
                # 1. Google Stealth Search
                try:
                    target_url = f"https://www.google.com/search?q={urllib.parse.quote(q)}"
                    page = StealthyFetcher.fetch(target_url, headless=True)
                    if page and page.text:
                        soup = BeautifulSoup(page.text, "html.parser")
                        for a in soup.find_all('a', href=True):
                            href = a['href']
                            if href.startswith("/url?q="):
                                href = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get('q', [''])[0]
                            if self._is_valid_organic_url(href):
                                found_urls.add(href)
                except Exception as ge:
                    logger.warning(f"Stealth Google search error for '{q}': {ge}")

                # 2. Bing Stealth Search
                try:
                    target_url = f"https://www.bing.com/search?q={urllib.parse.quote(q)}"
                    page = StealthyFetcher.fetch(target_url, headless=True)
                    if page and page.text:
                        soup = BeautifulSoup(page.text, "html.parser")
                        for link in soup.select("li.b_algo h2 a, li.b_algo a"):
                            href = link.get("href")
                            if href and self._is_valid_organic_url(href):
                                found_urls.add(href)
                except Exception as be:
                    logger.warning(f"Stealth Bing search error for '{q}': {be}")
        except Exception as se:
            logger.warning(f"Scrapling fetcher import/execution notice: {se}")

        return list(found_urls)

    async def search(self, queries: List[str], max_results_per_query: int = 5) -> Dict[str, Any]:
        urls = set()

        # 1. Primary Engine: DDGS
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

        # 2. Parallel Secondary Engine: Scrapling Stealth Search for Google & Bing
        try:
            stealth_urls = await asyncio.to_thread(self._fetch_stealth_search_urls, queries, max_results_per_query)
            for u in stealth_urls:
                urls.add(u)
        except Exception as e:
            logger.warning(f"Stealth search execution error: {e}")

        return {
            "status": "success",
            "queries": queries,
            "urls": list(urls)
        }
