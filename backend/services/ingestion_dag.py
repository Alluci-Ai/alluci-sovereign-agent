import json
import logging
import asyncio
from typing import List, Dict, Any, AsyncGenerator
from pydantic import BaseModel, Field

logger = logging.getLogger("IngestionDAG")

class ExecutionSchema(BaseModel):
    type: str
    baseUrl: str = ""
    endpoint: str = ""
    method: str = ""
    sandboxed: bool = False

class ToolSchemaDefinition(BaseModel):
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)

class ToolManifestSchema(BaseModel):
    name: str
    description: str
    category: str
    execution: ExecutionSchema
    schema: ToolSchemaDefinition = Field(default_factory=ToolSchemaDefinition)

class IngestionDAG:
    def __init__(self, router, scraper_service):
        self.router = router
        self.scraper_service = scraper_service

    async def run(self, urls: List[str], user_prompt: str, deep_crawl: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        if not urls:
            yield {"type": "error", "message": "No URLs provided"}
            return

        yield {"type": "progress", "message": f"Scraping {len(urls)} link(s){' with Deep Crawl' if deep_crawl else ''}..."}
        
        import asyncio
        progress_queue = asyncio.Queue()
        
        async def on_progress(msg: str):
            await progress_queue.put({"type": "progress", "message": msg})

        async def scraper_worker():
            try:
                docs = await self.scraper_service.fetch_all_markdown(
                    urls, deep_crawl=deep_crawl, progress_callback=on_progress
                )
                await progress_queue.put({"type": "done", "docs": docs})
            except Exception as e:
                await progress_queue.put({"type": "error", "message": f"Scraping failed: {e}"})

        worker_task = asyncio.create_task(scraper_worker())
        
        markdown_docs = []
        while True:
            msg = await progress_queue.get()
            if msg["type"] == "done":
                markdown_docs = msg["docs"]
                break
            elif msg["type"] == "error":
                logger.error(msg["message"])
                yield msg
                return
            else:
                yield msg

        yield {"type": "progress", "message": "Classifying technical paradigms..."}
        classified_docs = []
        for i, md in enumerate(markdown_docs):
            if not md: continue
            
            yield {"type": "progress", "message": f"Classifying Link {i+1}..."}
            classification_prompt = (
                "Analyze this technical document. Categorize it into EXACTLY ONE of the following: "
                "REST_API, JSON_RPC, CLI_COMMAND, MCP_SERVER, GENERAL_SOP.\n\n"
                "Return ONLY the category name."
            )
            try:
                # Assuming router has a direct inference method. If it uses get_structured_plan, we adapt.
                # Since get_structured_plan enforces JSON, we can ask for JSON.
                res = await self.router.get_structured_plan(
                    prompt=f"Document:\n{md[:4000]}\n\nReturn JSON: {{'category': '...'}}",
                    system_instruction=classification_prompt,
                    agent_id="executive"
                )
                cat = res.get("category", "REST_API")
                classified_docs.append({"category": cat, "content": md})
            except Exception as e:
                logger.warning(f"Classification failed for doc {i}: {e}")
                classified_docs.append({"category": "REST_API", "content": md}) # fallback

        yield {"type": "progress", "message": "Extracting paradigm-specific rules..."}
        extracted_specs = []
        for i, doc in enumerate(classified_docs):
            cat = doc["category"]
            md = doc["content"]
            yield {"type": "progress", "message": f"Extracting {cat} specs for Link {i+1}..."}
            
            ext_sys_prompt = "Extract dense technical specifications. Discard fluff. Output as JSON."
            if cat in ("REST_API", "JSON_RPC"):
                ext_sys_prompt += " Focus on endpoints, methods, headers, and payload schemas."
            elif cat == "CLI_COMMAND":
                ext_sys_prompt += " Focus on commands, flags, arguments, and STDOUT formats."
            elif cat == "MCP_SERVER":
                ext_sys_prompt += " Focus on SSE/WebSocket endpoints, protocols, and exposed tools."
            else:
                ext_sys_prompt += " Focus on core logic, data structures, and operational rules."
                
            try:
                res = await self.router.get_structured_plan(
                    prompt=f"Document:\n{md[:8000]}\n\nReturn JSON: {{'specs': '...'}}",
                    system_instruction=ext_sys_prompt,
                    agent_id="executive"
                )
                specs = str(res.get("specs", res))
                extracted_specs.append(f"[{cat} Specs]: {specs}")
            except Exception as e:
                logger.warning(f"Extraction failed for doc {i}: {e}")
                extracted_specs.append(f"[{cat} Specs]: Extraction Failed")

        yield {"type": "progress", "message": "Synthesizing final Tool Configuration..."}
        
        combined_specs = "\n\n".join(extracted_specs)
        synth_prompt = (
            "You are an expert Tool Architect. Merge the following specifications into a single ToolManifest JSON object.\n"
            "Schema:\n"
            "{\n"
            "  \"name\": \"Tool Name\",\n"
            "  \"description\": \"Description of tool\",\n"
            "  \"category\": \"API or CLI or MCP\",\n"
            "  \"execution\": {\"type\": \"API/CLI/MCP\", \"baseUrl\": \"...\", \"endpoint\": \"...\", \"method\": \"...\", \"sandboxed\": true/false},\n"
            "  \"schema\": {\"type\": \"object\", \"properties\": {...}, \"required\": [...]}\n"
            "}\n\n"
        )
        if user_prompt:
            synth_prompt += f"\nUser specifically requested: {user_prompt}\n"
            
        try:
            manifest_res = await self.router.get_structured_plan(
                prompt=f"Aggregated Specs:\n{combined_specs}\n\nReturn ONLY valid JSON.",
                system_instruction=synth_prompt,
                agent_id="executive"
            )
            
            yield {"type": "progress", "message": "Validating Schema..."}
            # Validation node
            try:
                valid_manifest = ToolManifestSchema(**manifest_res)
                manifest_dict = valid_manifest.model_dump()
                # For compatibility with frontend
                if "schema" in manifest_dict and "properties" in manifest_dict["schema"]:
                    pass
                else:
                    manifest_dict["schema"] = {"type": "object", "properties": {}, "required": []}
            except Exception as ve:
                logger.warning(f"Initial validation failed: {ve}, attempting repair...")
                yield {"type": "progress", "message": "Schema validation failed, attempting repair..."}
                repair_prompt = f"The following JSON failed validation: {ve}\nFix the JSON to match the ToolManifestSchema and return it."
                repaired_res = await self.router.get_structured_plan(
                    prompt=f"JSON:\n{json.dumps(manifest_res)}\n\nError:\n{ve}",
                    system_instruction=repair_prompt,
                    agent_id="executive"
                )
                valid_manifest = ToolManifestSchema(**repaired_res)
                manifest_dict = valid_manifest.model_dump()

            yield {"type": "success", "manifest": manifest_dict}
            
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            yield {"type": "error", "message": f"Synthesis failed: {e}"}
