import logging
import httpx
from typing import List, Dict, Any

logger = logging.getLogger("SearXNGClient")

class SearXNGClient:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip("/")

    async def search(self, queries: List[str], max_results_per_query: int = 5) -> Dict[str, Any]:
        """
        Asynchronously queries the local SearXNG JSON endpoint.
        Returns a normalized dict payload: {"status": "success", "queries": queries, "urls": List[str]}
        """
        urls = set()
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for q in queries:
                try:
                    resp = await client.get(
                        f"{self.base_url}/search",
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
                    else:
                        logger.warning(f"SearXNG returned HTTP {resp.status_code} for query '{q}'")
                except Exception as e:
                    logger.warning(f"SearXNG connection error for query '{q}': {e}")

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
