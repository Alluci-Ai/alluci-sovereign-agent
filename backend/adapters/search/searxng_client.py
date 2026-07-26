import logging
import httpx
from typing import List, Dict, Any, Optional

logger = logging.getLogger("SearXNGClient")

class SearXNGClient:
    def __init__(self, base_url: Optional[str] = None):
        if not base_url:
            try:
                from ...config import settings
                base_url = getattr(settings, "SEARXNG_URL", "http://localhost:8080")
            except Exception:
                base_url = "http://localhost:8080"
        self.base_url = base_url.rstrip("/")

    async def search(self, queries: List[str], max_results_per_query: int = 5) -> Dict[str, Any]:
        """
        Asynchronously queries the local SearXNG JSON endpoint.
        Returns a normalized dict payload: {"status": "success", "queries": queries, "urls": List[str]}
        """
        urls = set()
        endpoints = [self.base_url, "https://searx.be", "https://searxng.site", "https://searx.prvcy.eu"]
        # Filter out duplicates while preserving order
        unique_endpoints = []
        for ep in endpoints:
            if ep and ep not in unique_endpoints:
                unique_endpoints.append(ep)

        async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
            for q in queries:
                q_success = False
                for ep in unique_endpoints:
                    try:
                        resp = await client.get(
                            f"{ep}/search",
                            params={"q": q, "format": "json", "language": "en"}
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            results = data.get("results", [])
                            count = 0
                            for item in results:
                                url = item.get("url") or item.get("link")
                                if url and url.startswith("http"):
                                    urls.add(url)
                                    count += 1
                                    if count >= max_results_per_query:
                                        break
                            q_success = True
                            break
                    except Exception as e:
                        logger.debug(f"SearXNG endpoint '{ep}' query notice for '{q}': {e}")
                if not q_success:
                    logger.warning(f"All SearXNG endpoints failed for query '{q}'")

        if urls:
            return {
                "status": "success",
                "queries": queries,
                "urls": list(urls)
            }
        return {
            "status": "error",
            "message": "SearXNG unreachable or returned 0 results.",
            "queries": queries,
            "urls": []
        }
