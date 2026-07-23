import asyncio
import httpx
import trafilatura
from typing import Dict, Any, List
from duckduckgo_search import DDGS
from .base import Adapter
from ..logging_config import get_logger

logger = get_logger("DeepResearchAdapters")

class DeepResearchQueryExpansionAdapter(Adapter):
    name = "deep_research_query_expansion"
    description = "Uses DuckDuckGo Search to fetch initial URLs based on expanded queries across web, YouTube, and Podcasts."
    
    async def execute(self, args: Dict[str, Any]) -> Any:
        queries = args.get("queries", [])
        raw_objective = args.get("query", "") or args.get("context", "") or args.get("objective", "")
        if not queries:
            if raw_objective:
                from .. import services
                if services.router:
                    try:
                        exp_prompt = f"Deconstruct this research objective into 3-5 specific search queries for web articles, YouTube videos, and podcasts: {raw_objective}. Return ONLY a JSON list of strings, e.g. [\"query 1\", \"query 2\"]"
                        resp = await services.router.get_response(
                            prompt=exp_prompt,
                            system_instruction="You are a specialized multi-media research query expansion engine.",
                            complexity="MEDIUM",
                            privacy_level="PUBLIC",
                            inference_mode="TACTICAL"
                        )
                        import json, re
                        clean_json = re.sub(r'```[a-z]*', '', resp).strip()
                        parsed = json.loads(clean_json)
                        if isinstance(parsed, list) and len(parsed) > 0:
                            queries = [str(q) for q in parsed]
                    except Exception as e:
                        logger.warning(f"Query expansion via LLM failed: {e}. Falling back to objective query.")
                if not queries:
                    queries = [raw_objective, f"{raw_objective} youtube", f"{raw_objective} podcast"]
            else:
                return {"status": "error", "message": "No queries provided."}
                
        max_results = args.get("max_results_per_query", 5)
        urls = set()
        
        def _search(search_queries):
            local_urls = []
            with DDGS() as ddgs:
                for q in search_queries:
                    try:
                        results = list(ddgs.text(q, max_results=max_results))
                        for r in results:
                            href = r.get('href') or r.get('url') or r.get('link')
                            if href:
                                local_urls.append(href)
                    except Exception as e:
                        logger.error(f"DDGS error for query '{q}': {e}")
            return local_urls

        try:
            results = await asyncio.to_thread(_search, queries)
            for url in results:
                urls.add(url)
                
            # Fallback 1: If site-restricted queries yielded 0 results, retry unconstrained plain text queries
            if not urls and raw_objective:
                plain_queries = [raw_objective, f"{raw_objective} youtube", f"{raw_objective} podcast"]
                logger.info(f"Site-restricted queries yielded 0 URLs. Retrying plain queries: {plain_queries}")
                fallback_results = await asyncio.to_thread(_search, plain_queries)
                for url in fallback_results:
                    urls.add(url)
                    
            # Fallback 2: Direct DuckDuckGo HTML scraper fallback if DDGS library returns empty
            if not urls and raw_objective:
                logger.info("DDGS library returned 0 URLs. Executing direct HTML scraper fallback...")
                headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
                async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                    try:
                        search_url = f"https://html.duckduckgo.com/html/?q={httpx.URL(raw_objective).raw_path.decode('utf-8') if hasattr(httpx.URL(raw_objective), 'raw_path') else raw_objective}"
                        resp = await client.post("https://html.duckduckgo.com/html/", data={"q": raw_objective})
                        if resp.status_code == 200:
                            import re
                            found = re.findall(r'href="(https?://[^"]+)"', resp.text)
                            for u in found:
                                if "duckduckgo.com" not in u:
                                    urls.add(u)
                    except Exception as he:
                        logger.warning(f"HTML scraper fallback failed: {he}")

            logger.info(f"Query expansion found {len(urls)} unique URLs for queries: {queries}")
            return {"status": "success", "queries": queries, "urls": list(urls)}
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return {"status": "error", "message": str(e)}

class DeepResearchHarvestAdapter(Adapter):
    name = "deep_research_harvest"
    description = "Asynchronously harvests web pages, YouTube transcripts, and Podcast metadata into Markdown."
    
    async def execute(self, args: Dict[str, Any]) -> Any:
        dependency_output = args.get("dependency_output", "")
        urls = args.get("urls", [])
        
        if not urls and isinstance(dependency_output, dict):
            for v in dependency_output.values():
                if isinstance(v, dict) and "urls" in v:
                    urls.extend(v["urls"])
                elif isinstance(v, list):
                    urls.extend(v)
        
        if not urls and dependency_output:
            import re
            search_text = str(dependency_output)
            urls = re.findall(r'https?://[^\s\'"<>]+', search_text)
            
        urls = list(set(urls))
        if not urls:
            return {"status": "error", "message": "No URLs provided for harvesting."}
            
        logger.info(f"Harvesting {len(urls)} URLs (Web, YouTube, Podcast)...")
        
        results = []
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "cross-site",
            "Sec-Fetch-User": "?1",
            "Referer": "https://www.google.com/",
            "Upgrade-Insecure-Requests": "1"
        }
        
        async def fetch_youtube_transcript(url: str) -> str:
            import re
            video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11})', url)
            if not video_id_match:
                return ""
            video_id = video_id_match.group(1)
            try:
                from youtube_transcript_api import YouTubeTranscriptApi
                transcript_list = await asyncio.to_thread(YouTubeTranscriptApi.get_transcript, video_id)
                transcript_text = " ".join([t['text'] for t in transcript_list])
                return f"--- SOURCE: YouTube Video ({url}) ---\n<youtube_transcript>\n{transcript_text}\n</youtube_transcript>\n"
            except Exception as e:
                logger.warning(f"youtube-transcript-api unavailable/failed for {url}: {e}")
                return ""

        async def fetch_pdf_text(url: str, content_bytes: bytes) -> str:
            try:
                import io
                pdf_text = ""
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(io.BytesIO(content_bytes))
                    for page in reader.pages:
                        t = page.extract_text()
                        if t: pdf_text += t + "\n"
                except Exception:
                    try:
                        from PyPDF2 import PdfReader
                        reader = PdfReader(io.BytesIO(content_bytes))
                        for page in reader.pages:
                            t = page.extract_text()
                            if t: pdf_text += t + "\n"
                    except Exception:
                        pass
                if not pdf_text:
                    import re
                    text_parts = re.findall(r'\(([^()]{4,})\)', content_bytes.decode('latin1', errors='ignore'))
                    if text_parts:
                        pdf_text = " ".join([tp for tp in text_parts if len(tp) > 4 and not tp.startswith('/')])
                        
                if pdf_text and len(pdf_text.strip()) > 50:
                    return f"--- SOURCE: PDF Document ({url}) ---\n<pdf_document_data>\n{pdf_text.strip()}\n</pdf_document_data>\n"
            except Exception as pe:
                logger.warning(f"PDF extraction failed for {url}: {pe}")
            return ""

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
            async def fetch_and_distill(url: str):
                try:
                    if "youtube.com" in url or "youtu.be" in url:
                        yt_transcript = await fetch_youtube_transcript(url)
                        if yt_transcript:
                            return yt_transcript

                    resp = await client.get(url)
                    resp.raise_for_status()
                    
                    is_pdf = url.lower().split("?")[0].endswith(".pdf") or "application/pdf" in resp.headers.get("Content-Type", "").lower()
                    if is_pdf:
                        pdf_data = await fetch_pdf_text(url, resp.content)
                        if pdf_data:
                            return pdf_data

                    html = resp.text
                    
                    def _extract():
                        return trafilatura.extract(html, output_format="markdown", include_links=True)
                    markdown = await asyncio.to_thread(_extract)
                    
                    is_podcast = any(k in url.lower() for k in ["podcast", "spotify.com/episode", "apple.com/podcast"]) or "<rss" in html.lower()
                    prefix = "--- SOURCE: Podcast Feed/Episode" if is_podcast else "--- SOURCE:"
                    
                    if markdown:
                        return f"{prefix} {url} ---\n<inert_web_data>\n{markdown}\n</inert_web_data>\n"
                        
                    try:
                        from playwright.async_api import async_playwright
                        async with async_playwright() as p:
                            browser = await p.chromium.launch(headless=True)
                            page = await browser.new_page()
                            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                            await page.wait_for_timeout(2000)
                            text_content = await page.evaluate("document.body.innerText")
                            await browser.close()
                            if text_content and text_content.strip():
                                return f"{prefix} {url} (PLAYWRIGHT FALLBACK) ---\n<inert_web_data>\n{text_content.strip()}\n</inert_web_data>\n"
                    except ImportError:
                        pass
                    except Exception as pe:
                        logger.warning(f"Playwright fallback failed for {url}: {pe}")
                        
                    return ""
                except Exception as e:
                    logger.warning(f"Failed to harvest {url}: {e}")
                    return ""
                    
            tasks = [fetch_and_distill(url) for url in urls]
            harvested = await asyncio.gather(*tasks)
            
            for content in harvested:
                if content:
                    results.append(content)
                    
        if not results:
            return {"status": "error", "message": "All URL harvesting failed or returned empty content."}
            
        combined_markdown = "\n".join(results)
        
        from .. import services
        if services.orchestrator and hasattr(services.orchestrator, "avl") and hasattr(services.orchestrator, "_perform_ppn_check"):
            _, polytope_state = services.orchestrator._perform_ppn_check(
                objective="DeepResearch Harvest Evaluation",
                autonomy="RESTRICTED",
                origin="deep_research_adapter"
            )
            if polytope_state is not None:
                is_safe, avl_reason = services.orchestrator.avl.verify(combined_markdown, polytope_state)
                if not is_safe:
                    return {"status": "error", "message": f"Harvested content rejected by AVL: {avl_reason}"}

        return {"status": "success", "harvested_content": combined_markdown}

class DeepResearchEvaluateAdapter(Adapter):
    name = "deep_research_evaluate"
    description = "Evaluates harvested data, synthesizes report via single-pass or dynamic Map-Reduce, and triggers artifact broadcast."
    
    async def execute(self, args: Dict[str, Any]) -> Any:
        dependency_output = args.get("dependency_output", "")
        report = args.get("synthesis_report", "")
        
        if not report:
            if isinstance(dependency_output, dict):
                for val in dependency_output.values():
                    if isinstance(val, dict) and "harvested_content" in val:
                        report += val["harvested_content"] + "\n"
                    elif isinstance(val, str) and "SOURCE:" in val:
                        report += val + "\n"
            elif isinstance(dependency_output, str):
                report = dependency_output
                
        # Input Validation Guardrail: Ensure report contains meaningful text before calling LLM
        clean_report_check = report.strip()
        if not clean_report_check or "All URL harvesting failed" in clean_report_check or len(clean_report_check) < 50:
            logger.warning("Harvested data is empty or invalid. Returning structured fallback report without LLM invocation.")
            return "# Deep Research Analysis Report\n\n> ⚠️ **Notice:** Web harvesting was unable to retrieve external pages for this objective. Please verify search queries or network availability.\n\n### Objective Context\n" + str(args.get("context", "No context provided."))
            
        from .. import services
        if services.router:
            try:
                import psutil
                ram_gb = psutil.virtual_memory().total / (1024**3)
            except Exception:
                ram_gb = 16.0
                
            single_pass_limit = 800000 if ram_gb >= 32 else 360000
            
            if len(report) <= single_pass_limit:
                logger.info(f"Executing Single-Pass Synthesis on {len(report)} characters (RAM: {ram_gb:.1f}GB)...")
                single_pass_prompt = f"Synthesize all of the following harvested research data (including articles, YouTube transcripts, and podcast notes) into a single, cohesive, comprehensive final deep research report with clear sections, links, and detailed citations.\n\n{report}"
                try:
                    final_report = await services.router.get_response(
                        prompt=single_pass_prompt,
                        system_instruction="You are a senior research analyst. Produce a well-structured, detailed final report with links and citations.",
                        complexity="HIGH",
                        privacy_level="PUBLIC",
                        inference_mode="LOCAL"
                    )
                    report = final_report
                except Exception as e:
                    logger.error(f"Single-pass synthesis failed: {e}")
            else:
                chunk_size = 320000  # ~80k tokens per chunk
                chunks = [report[i:i + chunk_size] for i in range(0, len(report), chunk_size)]
                logger.info(f"Report exceeds single-pass boundary. Chunking into {len(chunks)} pieces for Map-Reduce evaluation.")
                summaries = []
                for idx, chunk in enumerate(chunks):
                    map_prompt = f"Summarize the following research data chunk ({idx+1}/{len(chunks)}). Extract key insights, facts, quotes, YouTube/podcast links, and conclusions.\n\n{chunk}"
                    try:
                        summary = await services.router.get_response(
                            prompt=map_prompt,
                            system_instruction="You are a meticulous research analyst.",
                            complexity="MEDIUM",
                            privacy_level="PUBLIC",
                            inference_mode="TACTICAL"
                        )
                        summaries.append(summary)
                    except Exception as e:
                        logger.error(f"Failed to summarize chunk {idx+1}: {e}")
                        summaries.append(f"[Failed to process chunk {idx+1}]")
                
                combined_summaries = "\n\n---\n\n".join(summaries)
                reduce_prompt = f"Synthesize the following chunk summaries into a single, cohesive, comprehensive final deep research report with links and citations.\n\n{combined_summaries}"
                try:
                    final_report = await services.router.get_response(
                        prompt=reduce_prompt,
                        system_instruction="You are a senior research analyst. Produce a well-structured, detailed final report.",
                        complexity="HIGH",
                        privacy_level="PUBLIC",
                        inference_mode="LOCAL"
                    )
                    report = final_report
                except Exception as e:
                    logger.error(f"Failed to reduce summaries: {e}")
                    report = combined_summaries

        # Flush Metal Cache after long context evaluation
        try:
            import mlx.core as mx
            mx.metal.clear_cache()
            logger.info("Cleared Metal cache after deep research evaluation.")
        except Exception:
            pass

        # Push to PCL (Proactive Cognitive Loop)
        if services.pcl:
            asyncio.create_task(self._notify_pcl(services.pcl, report))
            
        return report

    async def _notify_pcl(self, pcl, report: str):
        try:
            from .. import services
            if services.hlsm_manager:
                await services.hlsm_manager.encode_message(
                    content=report,
                    source="deep_research",
                    session_key="background_research",
                    psi=0.5
                )
                logger.info("Successfully ingested deep research report into H-LSM semantic memory.")
            else:
                summary = report[:1000] + ("..." if len(report) > 1000 else "")
                pcl.world_model.recent_learnings.append(f"Deep Research Insight: {summary}")
                if len(pcl.world_model.recent_learnings) > 10:
                    pcl.world_model.recent_learnings = pcl.world_model.recent_learnings[-10:]
        except Exception as e:
            logger.error(f"Failed to ingest deep research into PCL/H-LSM: {e}")

class DeepResearchChatReportAdapter(Adapter):
    name = "deep_research_report_chat"
    description = "Condenses the final deep research report into a chat-friendly summary and broadcasts it to the UI chat window."
    
    async def execute(self, args: Dict[str, Any]) -> Any:
        dep_output = args.get("dependency_output", "")
        report = ""
        if isinstance(dep_output, dict):
            report = "\n".join([str(v) for v in dep_output.values()])
        else:
            report = str(dep_output)
            
        if not report or not report.strip():
            logger.warning("No deep research report available to summarize for chat.")
            return "No findings to report."

        summary = "I have completed the deep research objective! The full comprehensive report, along with supporting context, is now available in your side window artifact buffer."
        
        # Try to extract a brief tl;dr using the router if available
        from .. import services
        if services.router:
            prompt = f"Provide a very brief 2-3 sentence executive summary of the following research report to be sent in a chat message to the user:\n\n{report[:10000]}"
            try:
                llm_summary = await services.router.get_response(
                    prompt=prompt,
                    system_instruction="You are an assistant reporting back in chat.",
                    complexity="LOW",
                    privacy_level="PUBLIC",
                    inference_mode="LOCAL"
                )
                if llm_summary:
                    summary += f"\n\n**TL;DR:** {llm_summary}"
            except Exception as e:
                logger.error(f"Failed to generate TL;DR for chat: {e}")
                
        if services.orchestrator and hasattr(services.orchestrator, "ws_gateway") and services.orchestrator.ws_gateway:
            import uuid
            msg_id = str(uuid.uuid4())
            try:
                await services.orchestrator.ws_gateway.broadcast_event('chat.message.received', {
                    "id": msg_id,
                    "sender": "rocco",
                    "role": "assistant",
                    "content": summary,
                    "channel": "local"
                })
                logger.info("Successfully broadcasted deep research chat report to UI.")
            except Exception as e:
                logger.error(f"Failed to broadcast chat message: {e}")
                
        return {"status": "success", "chat_summary": summary}
