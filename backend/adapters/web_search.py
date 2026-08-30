
import os
import json
import sqlite3
import time
import asyncio
import httpx
from ..logging_config import get_logger
from typing import Dict, Any, Optional, List
from .base import Adapter


class ResearchDossierCache:
    """
    Local SQLite Cache for Researched Dossiers.
    Stores query -> JSON results with a 24-hour Time-To-Live (TTL).
    Eliminates redundant external API calls and provides 0ms latency for repeated questions.
    """
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
            os.makedirs(base_dir, exist_ok=True)
            db_path = os.path.join(base_dir, "research_cache.db")
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS research_dossiers (
                        query_hash TEXT PRIMARY KEY,
                        raw_query TEXT NOT NULL,
                        results_json TEXT NOT NULL,
                        cached_at REAL NOT NULL
                    )
                """)
                conn.commit()
        except Exception:
            pass

    def get(self, query: str, ttl_seconds: float = 86400.0) -> Optional[List[Dict[str, Any]]]:
        import hashlib
        q_hash = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT results_json, cached_at FROM research_dossiers WHERE query_hash = ?", (q_hash,))
                row = cursor.fetchone()
                if row:
                    results_json, cached_at = row
                    if time.time() - cached_at < ttl_seconds:
                        return json.loads(results_json)
        except Exception:
            return None
        return None

    def set(self, query: str, results: List[Dict[str, Any]]) -> None:
        import hashlib
        q_hash = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
        try:
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO research_dossiers (query_hash, raw_query, results_json, cached_at)
                    VALUES (?, ?, ?, ?)
                """, (q_hash, query.strip(), json.dumps(results), time.time()))
                conn.commit()
        except Exception:
            pass


class WebSearchAdapter(Adapter):
    """
    Web Search Adapter.
    Supports SerpAPI, Brave Search API, and DuckDuckGo (no key required).
    Equipped with Multi-Query Parallel Harvesting (Rocco 2.0) and Local SQLite Dossier Caching.

    Provider priority:
      - provider="brave"  → Brave Search API (requires api_key); falls back to DDG on error.
      - provider="serpapi" → SerpAPI Google (requires api_key); no fallback.
      - provider="ddg"    → DuckDuckGo (free, no key required).
      - No api_key set    → DDG automatically.
    """
    name = "web_search"
    description = "Search the web for real-time information. Supports Brave, SerpAPI, and DDG."

    def __init__(self, api_key: Optional[str] = None, provider: str = "serpapi", db_path: Optional[str] = None):
        self.api_key = api_key
        self.provider = provider
        self.logger = get_logger("WebSearchAdapter")
        self.cache = ResearchDossierCache(db_path=db_path)

    async def execute(self, query: str) -> Dict[str, Any]:  # type: ignore
        """Route the query to the appropriate search provider."""
        if not query or not query.strip():
            return {"status": "error", "message": "No query provided."}

        query = query.strip()

        try:
            # Check local cache first for single queries
            cached = self.cache.get(query)
            if cached is not None:
                self.logger.info(f"[ResearchCache] Cache hit for: {query!r}")
                return {"status": "success", "provider": "cache", "query": query, "results": cached}

            # No API key → use DDG regardless of configured provider
            res = None
            if not self.api_key:
                self.logger.info(f"No API key set — using DDG fallback for: {query!r}")
                res = await self._search_ddg(query)

            elif self.provider == "serpapi":
                res = await self._search_serpapi(query)

            elif self.provider == "brave":
                try:
                    res = await self._search_brave(query)
                except Exception as brave_err:
                    self.logger.warning(f"Brave search failed ({brave_err}); falling back to DDG.")
                    res = await self._search_ddg(query)

            elif self.provider == "ddg":
                res = await self._search_ddg(query)

            else:
                return {"status": "error", "message": f"Unknown provider: {self.provider!r}. Use 'brave', 'serpapi', or 'ddg'."}

            if res and res.get("status") == "success" and res.get("results"):
                self.cache.set(query, res["results"])

            return res

        except Exception as e:
            self.logger.error(f"Web search failed for {query!r}: {e}")
            return {"status": "error", "message": str(e)}

    async def execute_multi_query(self, queries: List[str], timeout: float = 4.0) -> Dict[str, Any]:
        """
        Executes parallel searches across multiple query angles, deduplicating URLs.
        Each sub-query is strictly guarded by an async timeout.
        """
        if not queries:
            return {"status": "error", "message": "No queries provided", "results": []}

        tasks = []
        for q in queries:
            tasks.append(asyncio.wait_for(self.execute(q), timeout=timeout))

        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        seen_links = set()

        for resp in responses:
            if isinstance(resp, dict) and resp.get("status") == "success":
                for item in resp.get("results", []):
                    link = item.get("link", "")
                    if link and link not in seen_links:
                        seen_links.add(link)
                        all_results.append(item)
                    elif not link:
                        all_results.append(item)

        return {
            "status": "success",
            "provider": self.provider,
            "queries": queries,
            "results": all_results[:12]
        }

    async def expand_and_harvest(self, objective: str) -> Dict[str, Any]:
        """
        Deep Research Harvester (Rocco 2.0).
        Decomposes complex objectives into 2-3 focused search vectors,
        checks local SQLite cache, executes parallel searches, and updates cache.
        """
        cached = self.cache.get(objective)
        if cached is not None:
            self.logger.info(f"[ResearchCache] 0ms HIT for: {objective[:60]}...")
            return {
                "status": "success",
                "provider": "local_sqlite_cache",
                "query": objective,
                "results": cached
            }

        # Query decomposition
        clean_obj = objective.strip()
        queries = [clean_obj]
        
        # Add focused sub-query if complex
        if " vs " in clean_obj.lower():
            parts = clean_obj.lower().split(" vs ")
            queries.extend([f"{p.strip()} specifications" for p in parts[:2]])
        elif "compare" in clean_obj.lower():
            queries.append(f"{clean_obj} benchmarks comparison")
        elif "deep research on" in clean_obj.lower():
            topic = clean_obj.lower().replace("deep research on", "").strip()
            queries = [topic, f"{topic} latest documentation architecture", f"{topic} benchmarks analysis"]

        res = await self.execute_multi_query(queries[:3])
        if res.get("status") == "success" and res.get("results"):
            self.cache.set(objective, res["results"])

        return res

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
            "X-Subscription-Token": self.api_key or "",
        }
        params = {
            "q": query,
            "count": 5,
            "safesearch": "moderate",
            "search_lang": "en",
            "text_decorations": False,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers, params=params)  # type: ignore
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
            from duckduckgo_search import AsyncDDGS  # type: ignore
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

    # ── Playwright Subprocess (Privilege Separation) ──────────────────────────
    
    async def scrape_url(self, url: str) -> str:
        """
        Use an isolated Playwright subprocess to scrape a URL.
        By delegating this to a subprocess, the Core Agent remains completely firewalled 
        from untrusted HTML payloads, and the scraper has zero memory access to the Vault.
        """
        import asyncio
        
        script = f"""
import asyncio
from playwright.async_api import async_playwright

async def run():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto('{url}', timeout=10000)
            content = await page.evaluate('document.body.innerText')
            await browser.close()
            print(content)
    except Exception as e:
        print(f"Error: {{e}}")

asyncio.run(run())
"""
        proc = await asyncio.create_subprocess_exec(
            "python", "-c", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0 or not stdout:
            self.logger.error(f"Playwright scrape failed for {url}: {stderr.decode()}")
            return f"Failed to scrape {url}."
            
        return stdout.decode().strip()

