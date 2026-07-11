import httpx
import trafilatura
from urllib.parse import urlparse
import logging
import asyncio

logger = logging.getLogger("ScraperService")

async def fetch_and_extract_markdown(url: str, timeout: float = 15.0) -> str:
    """
    Fetches a URL and distills its content to clean Markdown using trafilatura.
    If the URL is a GitHub repo root, it attempts to fetch the README.md directly.
    """
    # Quick transformation for GitHub repos to grab the raw README.md
    parsed = urlparse(url)
    if parsed.hostname in ("github.com", "www.github.com"):
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) == 2:
            # It's a repo root e.g. /owner/repo
            raw_url = f"https://raw.githubusercontent.com/{path_parts[0]}/{path_parts[1]}/main/README.md"
            logger.info(f"GitHub repo detected. Attempting to fetch raw README: {raw_url}")
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    resp = await client.get(raw_url)
                    resp.raise_for_status()
                    return resp.text
            except Exception as e:
                logger.warning(f"Failed to fetch raw README from {raw_url}, falling back to HTML extraction: {e}")
                pass # Fall back to normal extraction

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
            
            # Distill with trafilatura
            markdown = await asyncio.to_thread(
                trafilatura.extract, 
                html, 
                output_format="markdown", 
                include_links=True,
                include_images=False,
                include_tables=True
            )
            
            if markdown:
                return markdown
            
            logger.warning(f"Trafilatura failed to extract markdown from {url}. Returning raw text fallback.")
            # Simple fallback strip tags if trafilatura yields nothing
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            return soup.get_text(separator="\n")[:10000]
            
    except Exception as e:
        logger.error(f"Failed to scrape {url}: {e}")
        raise ValueError(f"Unable to scrape documentation from {url}. Error: {str(e)}")

async def fetch_all_markdown(
    urls: list[str], 
    timeout: float = 15.0,
    deep_crawl: bool = False,
    progress_callback = None
) -> list[str]:
    """
    Fetches multiple URLs concurrently. If deep_crawl is True, performs a BFS within the same domain.
    """
    if not deep_crawl:
        tasks = [fetch_and_extract_markdown(url, timeout) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_results: list[str] = []
        for r in results:
            if isinstance(r, str):
                valid_results.append(r)
            else:
                logger.error(f"Error fetching a URL during gather: {r}")
                
        return valid_results

    # Deep Crawl Logic (BFS)
    MAX_PAGES = 15
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin, urlparse
    import httpx

    visited = set()
    queue = urls.copy()
    valid_results = []
    
    # Restrict crawling to the domains of the initial URLs
    allowed_domains = {urlparse(u).netloc for u in urls if urlparse(u).netloc}

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:
        while queue and len(visited) < MAX_PAGES:
            current_url = queue.pop(0)
            
            # Normalize URL to prevent dupes (e.g., removing hash fragments)
            parsed_current = urlparse(current_url)
            normalized_url = parsed_current._replace(fragment="").geturl()
            
            if normalized_url in visited:
                continue
                
            visited.add(normalized_url)
            
            if progress_callback:
                await progress_callback(f"Crawled {len(visited)}/{MAX_PAGES} pages: {normalized_url}")
            
            try:
                resp = await client.get(normalized_url)
                resp.raise_for_status()
                html = resp.text
                
                # Extract markdown
                markdown = await asyncio.to_thread(
                    trafilatura.extract, 
                    html, 
                    output_format="markdown", 
                    include_links=True,
                    include_images=False,
                    include_tables=True
                )
                
                if markdown:
                    valid_results.append(markdown)
                else:
                    soup = BeautifulSoup(html, "html.parser")
                    valid_results.append(soup.get_text(separator="\n")[:10000])
                    
                # Extract links for BFS
                soup = BeautifulSoup(html, "html.parser")
                for a_tag in soup.find_all("a", href=True):
                    href = a_tag["href"]
                    # Ignore mailto, javascript, tel, etc.
                    if href.startswith(("mailto:", "javascript:", "tel:", "#")):
                        continue
                        
                    full_url = urljoin(normalized_url, href)
                    parsed_full = urlparse(full_url)
                    normalized_full = parsed_full._replace(fragment="").geturl()
                    
                    if parsed_full.netloc in allowed_domains and normalized_full not in visited and normalized_full not in queue:
                        queue.append(normalized_full)
                        
            except Exception as e:
                logger.error(f"Deep crawl failed on {normalized_url}: {e}")
                
    return valid_results
