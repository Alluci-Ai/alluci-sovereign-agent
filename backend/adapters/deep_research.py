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
    description = "Uses DuckDuckGo Search to fetch initial URLs based on expanded queries."
    
    async def execute(self, args: Dict[str, Any]) -> Any:
        queries = args.get("queries", [])
        if not queries:
            query = args.get("query", "") or args.get("context", "") or args.get("objective", "")
            if query:
                from .. import services
                if services.router:
                    try:
                        exp_prompt = f"Deconstruct this research objective into 3-5 specific search queries for web search: {query}. Return ONLY a JSON list of strings, e.g. [\"query 1\", \"query 2\"]"
                        resp = await services.router.get_response(
                            prompt=exp_prompt,
                            system_instruction="You are a research query expansion engine.",
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
                    queries = [query]
            else:
                return {"status": "error", "message": "No queries provided."}
                
        max_results = args.get("max_results_per_query", 5)
        urls = set()
        
        # Note: DDGS is blocking, but we run it via asyncio.to_thread to prevent blocking the event loop
        def _search():
            local_urls = []
            with DDGS() as ddgs:
                for q in queries:
                    try:
                        results = list(ddgs.text(q, max_results=max_results))
                        for r in results:
                            if 'href' in r:
                                local_urls.append(r['href'])
                    except Exception as e:
                        logger.error(f"DDGS error for query '{q}': {e}")
            return local_urls

        try:
            results = await asyncio.to_thread(_search)
            for url in results:
                urls.add(url)
            logger.info(f"Query expansion found {len(urls)} unique URLs for queries: {queries}")
            return {"status": "success", "queries": queries, "urls": list(urls)}
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return {"status": "error", "message": str(e)}

class DeepResearchHarvestAdapter(Adapter):
    name = "deep_research_harvest"
    description = "Asynchronously harvests and distills URLs into Markdown."
    
    async def execute(self, args: Dict[str, Any]) -> Any:
        # Expecting urls from the previous task's output
        # If dependency_output is passed by executor, it might be in args
        dependency_output = args.get("dependency_output", "")
        urls = args.get("urls", [])
        
        # If urls are not explicitly passed, try to parse from dependency_output
        if not urls and dependency_output:
            if isinstance(dependency_output, dict):
                search_text = " ".join([str(v) for v in dependency_output.values()])
            else:
                search_text = str(dependency_output)
            import re
            # Extract basic http/https URLs
            urls = re.findall(r'https?://[^\s\'"<>]+', search_text)
            urls = list(set(urls))
            
        if not urls:
            return {"status": "error", "message": "No URLs provided for harvesting."}
            
        logger.info(f"Harvesting {len(urls)} URLs asynchronously...")
        
        results = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
            async def fetch_and_distill(url: str):
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    html = resp.text
                    
                    # Distill with trafilatura offloaded to thread to prevent blocking event loop
                    def _extract():
                        return trafilatura.extract(html, output_format="markdown", include_links=True)
                    markdown = await asyncio.to_thread(_extract)
                    if markdown:
                        return f"--- SOURCE: {url} ---\n<inert_web_data>\n{markdown}\n</inert_web_data>\n"
                        
                    # Playwright fallback for JS-heavy sites
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
                                return f"--- SOURCE: {url} (PLAYWRIGHT FALLBACK) ---\n<inert_web_data>\n{text_content.strip()}\n</inert_web_data>\n"
                    except ImportError:
                        logger.warning(f"Playwright not installed, skipping fallback for {url}")
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
        
        # The executor passes orchestrator services to the DAG tasks if needed, 
        # but here we rely on the Orchestrator's AVL hook if possible, or we return the markdown directly.
        # As per the plan, the harvested markdown must go through AVL. 
        # The executor executes adapters, so we can import services here to run AVL manually if needed.
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
    description = "Evaluates harvested data, synthesizes report, and triggers artifact broadcast."
    
    async def execute(self, args: Dict[str, Any]) -> Any:
        dependency_output = args.get("dependency_output", "")
        if not dependency_output:
            return "Error: No dependency output provided for evaluation."
            
        # The synthesis is normally performed by the LCE (Local Cognitive Engine) generating the args for this task
        # The args should contain a "synthesis_report" generated by the LCE.
        report = args.get("synthesis_report", "")
        if not report:
            if isinstance(dependency_output, dict):
                for val in dependency_output.values():
                    if isinstance(val, dict) and "harvested_content" in val:
                        report += val["harvested_content"] + "\n"
                    else:
                        report += str(val) + "\n"
            else:
                report = str(dependency_output)
            
        from .. import services
        if services.router:
            chunk_size = 32000
            chunks = [report[i:i + chunk_size] for i in range(0, len(report), chunk_size)]
            
            if len(chunks) > 1:
                logger.info(f"Report is large. Chunking into {len(chunks)} pieces for Map-Reduce evaluation.")
                summaries = []
                for idx, chunk in enumerate(chunks):
                    map_prompt = f"Summarize the following research data chunk ({idx+1}/{len(chunks)}). Extract key insights, facts, and conclusions.\n\n{chunk}"
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
                reduce_prompt = f"Synthesize the following chunk summaries into a single, cohesive, comprehensive final deep research report.\n\n{combined_summaries}"
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
            else:
                reduce_prompt = f"Synthesize the following raw research data into a cohesive, comprehensive final deep research report.\n\n{report}"
                try:
                    final_report = await services.router.get_response(
                        prompt=reduce_prompt,
                        system_instruction="You are a senior research analyst. Produce a well-structured, detailed final report with links and citations.",
                        complexity="HIGH",
                        privacy_level="PUBLIC",
                        inference_mode="HYBRID"
                    )
                    report = final_report
                except Exception as e:
                    logger.error(f"Failed to synthesize single chunk: {e}")

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
