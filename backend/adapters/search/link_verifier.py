import asyncio, re, logging
import httpx
from typing import List, Dict, Tuple

logger = logging.getLogger("LinkVerifier")

async def verify_markdown_links(markdown_text: str, timeout: float = 3.0) -> Tuple[str, Dict[str, bool]]:
    """
    Parses Markdown links ([Title](URL)) and performs fast parallel HTTP HEAD checks.
    Returns (cleaned_markdown_text, status_dict) where broken links are annotated or flagged.
    """
    link_pattern = re.compile(r'\[([^\]]+)\]\((https?://[^\s\)]+)\)')
    matches = link_pattern.findall(markdown_text)
    if not matches:
        return markdown_text, {}

    unique_urls = list(set([m[1] for m in matches]))
    url_status: Dict[str, bool] = {}

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        async def _check_url(url: str):
            try:
                res = await client.head(url)
                if res.status_code < 400:
                    url_status[url] = True
                else:
                    # Fallback GET request if HEAD is rejected by web server
                    res_get = await client.get(url)
                    url_status[url] = res_get.status_code < 400
            except Exception as e:
                logger.debug(f"Link check notice for {url}: {e}")
                url_status[url] = False

        tasks = [_check_url(u) for u in unique_urls]
        await asyncio.gather(*tasks, return_exceptions=True)

    # Clean / annotate markdown text
    def replace_link(match):
        title, url = match.group(1), match.group(2)
        is_ok = url_status.get(url, True)
        if is_ok:
            return f"[{title}]({url})"
        else:
            return f"[{title}]({url}) *(Unverified)*"

    cleaned_text = link_pattern.sub(replace_link, markdown_text)
    return cleaned_text, url_status
