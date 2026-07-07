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
            query = args.get("query", "")
            if query:
                queries = [query]
            else:
                return {"status": "error", "message": "No queries provided."}
                
        max_results = args.get("max_results_per_query", 3)
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
            return {"status": "success", "urls": list(urls)}
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
            import re
            # Extract basic http/https URLs
            urls = re.findall(r'https?://[^\s\'"<>]+', str(dependency_output))
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
                    
                    # Distill with trafilatura
                    markdown = trafilatura.extract(html, output_format="markdown", include_links=True)
                    if markdown:
                        return f"--- SOURCE: {url} ---\n<inert_web_data>\n{markdown}\n</inert_web_data>\n"
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
            # If the LCE just passed the raw text to be evaluated here, we could call the LCE,
            # but standard DAGTasks use the LLM to generate the args (including the report).
            report = dependency_output
            
        # Push to PCL (Proactive Cognitive Loop)
        from .. import services
        if services.pcl:
            # We asynchronously notify the PCL about this recent learning
            asyncio.create_task(self._notify_pcl(services.pcl, report))
            
        return report

    async def _notify_pcl(self, pcl, report: str):
        try:
            # Limit the size for the world model
            summary = report[:1000] + ("..." if len(report) > 1000 else "")
            pcl.world_model.recent_learnings.append(f"Deep Research Insight: {summary}")
            if len(pcl.world_model.recent_learnings) > 10:
                pcl.world_model.recent_learnings = pcl.world_model.recent_learnings[-10:]
        except Exception as e:
            logger.error(f"Failed to ingest deep research into PCL: {e}")
