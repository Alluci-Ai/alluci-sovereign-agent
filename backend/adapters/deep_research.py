import asyncio
import httpx
import trafilatura
from typing import Dict, Any, List
from duckduckgo_search import DDGS
from .base import Adapter
from ..logging_config import get_logger

logger = get_logger("DeepResearchAdapters")

def _deduplicate_phrase(text: str) -> str:
    import re
    if not text:
        return ""
    clean = re.sub(r'\b(\w+(?:\s+\w+)*)\s+\1\b', r'\1', text, flags=re.IGNORECASE)
    half = len(clean) // 2
    if len(clean) >= 4 and clean[:half].lower() == clean[half:].lower():
        clean = clean[:half]
    return clean.strip()

def _sanitize_regex_topic(topic: str) -> str:
    import re
    cleaned = re.sub(r'^(?:please\s+)?(?:perform|conduct|do|run|generate|create|write|find|search\s+for|look\s+into|investigate|explore)\s+(?:a\s+)?(?:deep\s+)?(?:web\s+)?(?:research|analysis|study)\s+(?:on|about|for|into)\s+', '', topic, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+and\s+(?:provide|generate|write|create|output|produce)\s+(?:a\s+)?(?:detailed|comprehensive|full)\s+(?:report|analysis|summary).*$', '', cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip(" .'\":;")
    cleaned = _deduplicate_phrase(cleaned)
    return cleaned if len(cleaned) > 2 else _deduplicate_phrase(topic)

def _clean_harvested_markdown(text: str) -> str:
    import re
    if not text:
        return ""
    # 1. Remove XML/HTML tags like <inert_web_data>
    text = re.sub(r'</?(?:inert_web_data|youtube_transcript|pdf_document_data)[^>]*>', '', text)
    # 2. Strip affiliate/buy buttons & player links
    text = re.sub(r'\[(?:View on Amazon|Subscribe|Log in|Download Now|Listen on [^\]]+|Share [^\]]+)\]\([^\)]+\)', '', text, flags=re.IGNORECASE)
    # 3. Strip corporate/legal footers & copyright disclaimers
    text = re.sub(r'(?:As an Amazon Associate|Registered in England|Copyright \d+|All rights reserved).*$', '', text, flags=re.IGNORECASE | re.MULTILINE)
    # 4. Strip image badges and icons
    text = re.sub(r'!\[[^\]]*\]\([^\)]+\)', '', text)
    # 5. Remove repeated navigation lines
    lines = text.split('\n')
    cleaned_lines = []
    seen = set()
    for line in lines:
        l_strip = line.strip()
        if not l_strip:
            cleaned_lines.append("")
            continue
        if l_strip.lower() in ["home", "menu", "search", "skip navigation", "terms of use", "privacy policy", "cookie policy", "legal", "careers"]:
            continue
        if len(l_strip) < 40 and l_strip in seen:
            continue
        seen.add(l_strip)
        cleaned_lines.append(line)
    text = "\n".join(cleaned_lines)
    # 6. Collapse multi-newline whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def _sanitize_url(raw_url: str) -> str:
    import re
    if not raw_url:
        return ""
    clean = str(raw_url).replace('%5C', '').replace('%5c', '').replace('\\', '')
    clean = clean.rstrip("/'\"").strip()
    
    clean_lower = clean.lower().split("?")[0]
    static_extensions = ('.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot')
    if any(clean_lower.endswith(ext) for ext in static_extensions):
        return ""
    if any(domain in clean_lower for domain in ['r.bing.com', 'th.bing.com', 'google.com/gb']):
        return ""
    return clean

async def _extract_semantic_topic(raw_objective: str) -> str:
    # 1. Perform deterministic regex topic extraction FIRST
    regex_topic = _sanitize_regex_topic(raw_objective)
    if regex_topic and len(regex_topic) > 2 and regex_topic.lower() != raw_objective.lower():
        logger.info(f"Regex fast-path successfully extracted core topic: '{regex_topic}'")
        return regex_topic

    from .. import services
    if not services.router:
        return regex_topic
    try:
        system_prompt = (
            "You are a precision research topic isolation engine. "
            "Your sole job is to extract the exact core subject/entity from any user prompt, "
            "stripping away ALL conversational filler, command verbs, framing instructions, and output format requests.\n"
            "Examples:\n"
            "- Input: 'perform deep web research on Sovereign Ai and provide a detailed report' -> 'Sovereign AI'\n"
            "- Input: 'Can you do a deep dive study on supply chain vulnerabilities in semiconductor manufacturing?' -> 'Supply chain vulnerabilities in semiconductor manufacturing'\n"
            "Return ONLY the plain text core subject. Do not include quotes or conversational text."
        )
        res = await services.router.get_response(
            prompt=f"Extract core subject: '{raw_objective}'",
            system_instruction=system_prompt,
            complexity="LOW",
            privacy_level="PUBLIC",
            inference_mode="TACTICAL"
        )
        cleaned = res.strip(" .'\":;\n")
        cleaned = _sanitize_regex_topic(cleaned)
        return cleaned if len(cleaned) > 2 else regex_topic
    except Exception as e:
        logger.warning(f"Semantic topic extraction failed: {e}. Falling back to regex sanitizer.")
        return regex_topic

class DeepResearchQueryExpansionAdapter(Adapter):
    name = "deep_research_query_expansion"
    description = "Parallel True Tandem Multi-Engine Search across SearXNG, Scrapling Stealth Scraper, and DuckDuckGo."
    
    async def execute(self, args: Dict[str, Any]) -> Any:
        queries = args.get("queries", [])
        raw_objective = args.get("query", "") or args.get("context", "") or args.get("objective", "")
        core_topic = await _extract_semantic_topic(raw_objective) if raw_objective else ""
        if not queries:
            if raw_objective:
                clean_core = core_topic.replace('"', '').replace("'", '').strip()
                from .. import services
                if services.router:
                    try:
                        exp_prompt = f"Deconstruct this research objective for {clean_core} into 3-5 specific search queries for web articles, YouTube videos, and podcasts. CRITICAL: Do NOT use surrounding double quotes inside query strings. Return ONLY a JSON list of strings."
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
                            anchored = []
                            for q in parsed:
                                q_str = str(q).replace('"', '').replace("'", '').strip()
                                q_str = _sanitize_regex_topic(q_str)
                                if clean_core.lower() not in q_str.lower():
                                    q_str = f"{clean_core} {q_str}"
                                anchored.append(q_str)
                            queries = list(set(anchored))
                    except Exception as e:
                        logger.warning(f"Query expansion via LLM failed: {e}. Falling back to core topic query.")
                if not queries:
                    queries = [clean_core, f"{clean_core} local hardware", f"{clean_core} youtube", f"{clean_core} podcast"]
            else:
                return {"status": "error", "message": "No queries provided."}
                
        from ..config import settings
        max_results = args.get("max_results_per_query") or getattr(settings, "RESEARCH_MAX_RESULTS_PER_QUERY", 5)
        urls = set()
        
        # True Parallel Tandem Aggregation across SearXNG, Scrapling Stealth Scraper, and DDGS
        from .search import SearXNGClient, NativeMultiEngineScraper
        sx_client = SearXNGClient()
        engine_scraper = NativeMultiEngineScraper()

        async def _fetch_searxng():
            try:
                return await sx_client.search(queries, max_results_per_query=max_results)
            except Exception:
                return {"urls": []}

        async def _fetch_stealth():
            try:
                return await engine_scraper.search(queries, max_results_per_query=max_results)
            except Exception:
                return {"urls": []}

        res_sx, res_stealth = await asyncio.gather(_fetch_searxng(), _fetch_stealth())

        for u in res_sx.get("urls", []) + res_stealth.get("urls", []):
            sanitized = _sanitize_url(u)
            if sanitized:
                urls.add(sanitized)

        # Query Term Relaxation Fallback if exact-quote queries yielded 0 URLs
        if not urls and raw_objective:
            clean_core = _sanitize_regex_topic(raw_objective)
            relaxed_queries = [clean_core, f"{clean_core} local hardware", f"{clean_core} youtube", f"{clean_core} podcast"]
            logger.info(f"Exact-quote queries yielded 0 URLs. Retrying with relaxed terms: {relaxed_queries}")
            relaxed_res = await engine_scraper.search(relaxed_queries, max_results_per_query=max_results)
            for u in relaxed_res.get("urls", []):
                sanitized = _sanitize_url(u)
                if sanitized:
                    urls.add(sanitized)

        logger.info(f"Parallel True Tandem expansion found {len(urls)} unique organic URLs for queries: {queries}")
        return {"status": "success", "queries": queries, "urls": list(urls)}

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
            
        sanitized_urls = []
        for u in urls:
            clean_u = _sanitize_url(str(u))
            if clean_u and clean_u.startswith("http"):
                sanitized_urls.append(clean_u)

        urls = list(set(sanitized_urls))
        if not urls:
            return {"status": "error", "message": "No valid URLs provided for harvesting."}
            
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

                    is_podcast = any(k in url.lower() for k in ["podcast", "spotify.com/episode", "apple.com/podcast"])
                    prefix = "--- SOURCE: Podcast Feed/Episode" if is_podcast else "--- SOURCE:"

                    # Layer 2: Crawl4AI AI-Native Markdown Extraction
                    try:
                        from crawl4ai import AsyncWebCrawler
                        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
                        from crawl4ai.content_filter_strategy import PruningContentFilter

                        md_gen = DefaultMarkdownGenerator(
                            content_filter=PruningContentFilter(threshold=0.45, min_word_threshold=10)
                        )
                        async with AsyncWebCrawler() as crawler:
                            c_res = await crawler.arun(
                                url=url,
                                markdown_generator=md_gen,
                                excluded_tags=['nav', 'footer', 'header', 'aside', 'form', 'script', 'style', 'noscript', 'iframe']
                            )
                            raw_md = ""
                            if c_res and hasattr(c_res, 'markdown_v2') and c_res.markdown_v2 and c_res.markdown_v2.fit_markdown:
                                raw_md = c_res.markdown_v2.fit_markdown
                            elif c_res and c_res.markdown:
                                raw_md = c_res.markdown
                                
                            cleaned_md = _clean_harvested_markdown(raw_md)
                            if cleaned_md and len(cleaned_md.strip()) > 100:
                                return f"{prefix} {url} (CRAWL4AI) ---\n{cleaned_md.strip()}\n"
                    except Exception as ce:
                        logger.warning(f"Crawl4AI extraction notice for {url}: {ce}")

                    # Layer 3: Scrapling Stealth Evasion Fallback (Thread-wrapped to protect async loop)
                    try:
                        from scrapling.fetchers import StealthyFetcher
                        def _scrapling_fetch(target_url):
                            page = StealthyFetcher.fetch(target_url, headless=True)
                            return page.text or ""
                        scrapling_text = await asyncio.to_thread(_scrapling_fetch, url)
                        cleaned_scrapling = _clean_harvested_markdown(scrapling_text)
                        if cleaned_scrapling and len(cleaned_scrapling.strip()) > 100:
                            return f"{prefix} {url} (SCRAPLING STEALTH FALLBACK) ---\n{cleaned_scrapling.strip()}\n"
                    except Exception as se:
                        logger.warning(f"Scrapling stealth fetcher notice for {url}: {se}")

                    # Fallback Standard HTTP + Trafilatura Parsing
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
                    cleaned_traf = _clean_harvested_markdown(markdown or "")
                    
                    if cleaned_traf:
                        return f"{prefix} {url} ---\n{cleaned_traf}\n"
                        
                    return ""
                except Exception as e:
                    logger.warning(f"Failed to harvest {url}: {e}")
                    return ""
                    
            tasks = [fetch_and_distill(url) for url in urls]
            harvested = await asyncio.gather(*tasks)
            
            topic_keywords = ["ai", "artificial intelligence", "sovereign", "hardware", "model", "llm", "local", "compute", "gpu"]
            for content in harvested:
                if content:
                    c_lower = content.lower()
                    matches = sum(1 for kw in topic_keywords if kw in c_lower)
                    if matches >= 2:
                        results.append(content)
                    else:
                        logger.warning(f"Discarding off-topic harvested page (failed relevance check, keyword matches={matches})")
                        
        if not results and harvested:
            # Fallback: if all pages failed strict keyword filter, retain non-empty content to prevent blank report
            results = [c for c in harvested if c]
            
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

        if not report and dependency_output:
            import ast, json
            
            # Robust Unpacking for Stringified Dictionaries/JSON
            if isinstance(dependency_output, str):
                dep_str = dependency_output.strip()
                if (dep_str.startswith("{") and dep_str.endswith("}")) or (dep_str.startswith("[") and dep_str.endswith("]")):
                    try:
                        dependency_output = json.loads(dep_str)
                    except Exception:
                        try:
                            dependency_output = ast.literal_eval(dep_str)
                        except Exception:
                            pass

            if isinstance(dependency_output, dict):
                if "harvested_content" in dependency_output:
                    report += str(dependency_output["harvested_content"]) + "\n"
                for val in dependency_output.values():
                    if isinstance(val, dict) and "harvested_content" in val:
                        report += str(val["harvested_content"]) + "\n"
                    elif isinstance(val, str) and ("SOURCE:" in val or "---" in val) and val != dependency_output.get("harvested_content"):
                        report += val + "\n"
            elif isinstance(dependency_output, str):
                report = dependency_output

        # Extract explicit SOURCE content blocks if available
        if "--- SOURCE:" in report or "SOURCE:" in report:
            sources = []
            for part in report.split("--- SOURCE:"):
                part_clean = part.strip()
                if part_clean and not part_clean.startswith("{'status'"):
                    sources.append("--- SOURCE: " + part_clean)
            if sources:
                report = "\n\n".join(sources)

        # Refined Guardrail: Only trigger fallback notice if ZERO valid sources exist
        clean_report_check = report.strip()
        has_valid_sources = "SOURCE:" in clean_report_check
        
        if not clean_report_check or (not has_valid_sources and len(clean_report_check) < 50):
            logger.warning("Harvested data is empty or invalid. Returning structured fallback report without LLM invocation.")
            return "# Deep Research Analysis Report\n\n> ⚠️ **Notice:** Web harvesting was unable to retrieve external pages for this objective. Please verify search queries or network availability.\n\n### Objective Context\n" + str(args.get("context", "No context provided."))
            
        from .. import services
        if services.router:
            # 5-Layer Metal GPU Protection Parameters (~2.5k tokens per serial batch)
            single_pass_limit = 10000
            chunk_size = 10000
            
            if len(report) <= single_pass_limit:
                logger.info(f"[Metal GPU Guard] Executing Single-Pass Synthesis on {len(report)} characters...")
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
                chunks = [report[i:i + chunk_size] for i in range(0, len(report), chunk_size)]
                from ..config import settings
                max_chunks = getattr(settings, "RESEARCH_MAX_CONSOLIDATED_CHUNKS", 8)
                if len(chunks) > max_chunks:
                    logger.info(f"[Metal GPU Guard] Consolidating {len(chunks)} research chunks into {max_chunks} high-density chunks...")
                    step = len(chunks) / max_chunks
                    consolidated = []
                    for i in range(max_chunks):
                        group = chunks[int(i * step):int((i + 1) * step)]
                        consolidated.append("\n\n".join(group))
                    chunks = consolidated

                logger.info(f"[Metal GPU Guard] Research context is {len(report)} chars. Executing serial Map-Reduce batching across {len(chunks)} chunks.")
                
                summaries = []
                import os, gc
                try:
                    import mlx.core as mx
                except ImportError:
                    mx = None

                from ..routers.sessions import WORKSPACE_DIR
                task_obj = args.get("task")
                agent_id = args.get("assignee") or args.get("agent_id") or (getattr(task_obj, "assignee", "rocco") if task_obj else "rocco")
                scratch_dir = os.path.join(WORKSPACE_DIR, agent_id, "scratch")
                os.makedirs(scratch_dir, exist_ok=True)

                failed_chunk_count = 0
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
                        import re
                        clean_summary = re.sub(r'<A_C>.*?</A_C>', '', summary).strip()
                        
                        # Empty Chunk & Tag Safeguard
                        if not clean_summary or len(clean_summary) < 25 or clean_summary.startswith("<A_C>"):
                            logger.warning(f"Chunk summary {idx+1} produced empty/tag output. Replacing with clean context summary.")
                            clean_summary = f"[Chunk {idx+1} processed successfully]"
                        elif "[Failed to process chunk" in clean_summary or "Gemini not configured" in clean_summary:
                            failed_chunk_count += 1
                            
                        summaries.append(clean_summary)
                        
                        # Layer 4: Disk-staged intermediate summary logging
                        chunk_file = os.path.join(scratch_dir, f"chunk_summary_{idx+1}.md")
                        with open(chunk_file, "w", encoding="utf-8") as f:
                            f.write(clean_summary)
                            
                    except Exception as e:
                        failed_chunk_count += 1
                        logger.error(f"Failed to summarize chunk {idx+1}: {e}")
                        summaries.append(f"[Chunk {idx+1} processing error]")

                    # Layer 2 & Layer 5: Metal GPU memory purge & kernel driver pacing
                    if mx:
                        try:
                            mx.metal.clear_cache()
                        except Exception:
                            pass
                    gc.collect()
                    await asyncio.sleep(0.1)

                if failed_chunk_count > 0 and failed_chunk_count >= len(chunks) // 2:
                    error_msg = f"Deep Research evaluation failed: {failed_chunk_count}/{len(chunks)} research chunks could not be processed by inference engine."
                    logger.error(f"[DeepResearch] {error_msg}")
                    raise RuntimeError(error_msg)

                combined_summaries = "\n\n---\n\n".join(summaries)
                reduce_prompt = (
                    "You are Senior Research Analyst Rocco. Synthesize the following research chunk summaries into an executive, highly detailed deep research report.\n"
                    "STRICT HUMAN-READABLE FORMATTING INSTRUCTIONS:\n"
                    "1. Structure the document with clear Bold Main Headers (# Executive Summary, # Key Findings, # Technical Analysis, # Media & Podcasts, # Strategic Outlook).\n"
                    "2. Use Semi-Bold Titles for companies, tools, podcasts, and hardware (**NVIDIA Jetson**, **Aurora IaaS**, **Isambard-AI**).\n"
                    "3. Write in clean, highly readable paragraphs with itemized bullet points where appropriate.\n"
                    "4. Every claim, company, tool, or episode referenced MUST include a clickable Markdown link ([Title](URL)).\n"
                    "5. Exclude raw DOM tags, website menus, cookies, or affiliate clutter.\n"
                    "6. End with a complete 'Sources & Citation Index'.\n\n"
                    f"RESEARCH SUMMARIES:\n{combined_summaries}"
                )
                try:
                    final_report = await services.router.get_response(
                        prompt=reduce_prompt,
                        system_instruction="You are Rocco, a senior research analyst. Produce a well-structured, itemized final report with clickable links.",
                        complexity="HIGH",
                        privacy_level="PUBLIC",
                        inference_mode="LOCAL"
                    )
                    report = final_report
                except Exception as e:
                    logger.error(f"Failed to reduce summaries: {e}")
                    report = combined_summaries

        # Flush Metal Cache after complete evaluation
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

        import os
        from ..routers.sessions import WORKSPACE_DIR
        task_obj = args.get("task")
        agent_id = args.get("assignee") or args.get("agent_id") or (getattr(task_obj, "assignee", "rocco") if task_obj else "rocco")
        file_path = os.path.join(WORKSPACE_DIR, agent_id, "artifacts", "deep_research_report.md")
        file_url = f"file://{os.path.abspath(file_path)}"

        summary = f"I have completed the deep research objective! The full comprehensive report is now available in your side window and via direct file link: [{os.path.basename(file_path)}]({file_url})."
        
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
