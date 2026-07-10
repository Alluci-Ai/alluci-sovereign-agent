import yaml  # type: ignore
import os
from .logging_config import get_logger
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from datetime import datetime
from .security.vault import VaultManager

logger = get_logger("ToolManager")


class ToolManifest(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: str = Field(default="TOOL")
    parameters: Optional[Dict[str, Any]] = None
    capabilities: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None
    verified: bool = False
    source: str = "vault"
    last_active: Optional[str] = None
    error: Optional[str] = None
    reference_docs: Optional[List[str]] = None

class ToolManager:
    def __init__(self, vault: VaultManager, tools_dir: Optional[str] = None, workspace_tools_dir: Optional[str] = "alluci_vault/tools"):
        self.vault = vault
        self.tools_dir = tools_dir or os.path.expanduser("~/.polytope/tools")
        if not os.path.exists(self.tools_dir):
            os.makedirs(self.tools_dir, mode=0o700, exist_ok=True)
        self.workspace_tools_dir = workspace_tools_dir
            
        self.registry_id = "tool_registry"
        self.review_queue_id = "tool_review_queue"

    async def list_tools(self) -> List[Dict[str, Any]]:
        """Retrieve all active tools from both the vault and the local disk (P1-012)."""
        # 1. Load from Vault
        data = await self.vault.retrieve_secret(self.registry_id)
        vault_tools = data.get("tools", [])
        
        # 2. Load from Disk (both user ~/.polytope/tools and workspace alluci_vault/tools)
        disk_tools = []
        dirs_to_scan = [self.tools_dir]
        if self.workspace_tools_dir:
            dirs_to_scan.append(self.workspace_tools_dir)
        seen_ids = set()
        
        for s in vault_tools:
            if "id" in s:
                seen_ids.add(s["id"])
                
        for d in dirs_to_scan:
            if not os.path.exists(d):
                continue
            try:
                for filename in os.listdir(d):
                    file_path = os.path.join(d, filename)
                    tool_data = None
                    if filename.endswith((".yaml", ".yml")):
                        with open(file_path, "r") as f:
                            tool_data = yaml.safe_load(f)
                    elif filename.endswith(".json"):
                        import json
                        with open(file_path, "r") as f:
                            tool_data = json.load(f)
                            
                    if tool_data and "id" in tool_data:
                        if tool_data["id"] not in seen_ids:
                            try:
                                # Strict Pydantic Validation
                                tool_data["source"] = "disk"
                                if "verified" not in tool_data:
                                    tool_data["verified"] = True
                                validated_tool = ToolManifest(**tool_data).model_dump()
                                disk_tools.append(validated_tool)
                                seen_ids.add(tool_data["id"])
                            except Exception as ve:
                                logger.warning(f"Tool {tool_data['id']} failed schema validation: {ve}")
            except Exception as e:
                logger.error(f"Failed to load tools from disk dir {d}: {e}")
            
        all_tools = vault_tools + disk_tools
        from .state_manager import StateManager
        toggles = StateManager.get_tool_toggles()
        for tool in all_tools:
            if tool.get("id") in toggles:
                tool["enabled"] = toggles[tool["id"]]
            else:
                tool["enabled"] = True
                
        return all_tools

    async def get_review_queue(self) -> List[Dict[str, Any]]:
        """Retrieve tools pending review."""
        data = await self.vault.retrieve_secret(self.review_queue_id)
        return data.get("queue", [])

    async def import_package(self, package: Dict[str, Any]) -> Dict[str, Any]:
        """
        Imports a raw package into the review queue.
        Uses the internal ModelRouter to perform a genuine AI Critic Scan.
        """
        from .config import Settings
        from .inference.router import ModelRouter
        import json
        
        settings = Settings()  # type: ignore
        router = ModelRouter(settings)
        
        # Genuine Critic Scan
        prompt = f"""
        You are an AI Security Critic for the Polytope Sovereign OS.
        Analyze the following execution tool payload for security risks, remote execution vulnerabilities, and malicious patterns.
        
        Analyze this package:
        {json.dumps(package, indent=2)[:5000]} # Truncate if too long
        
        Return ONLY valid JSON with this schema:
        {{
            "risk_score": <integer from 0 to 100, where 100 is highly dangerous>,
            "notes": ["<specific observation 1>", "<specific observation 2>"]
        }}
        """
        try:
            res_text = await router.get_response(prompt, complexity="MEDIUM")
            # Extract JSON if wrapped in markdown
            if "```json" in res_text:
                res_text = res_text.split("```json")[1].split("```")[0].strip()
            elif "```" in res_text:
                res_text = res_text.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(res_text)
            risk_score = analysis.get("risk_score", 50)
            critic_notes = analysis.get("notes", ["Critic provided no specific notes."])
        except Exception as e:
            logger.error(f"Critic scan failed: {e}")
            risk_score = 100
            critic_notes = ["CRITICAL: LLM Critic scan failed to execute, assigning maximum risk score."]

        if not package.get("signature"):
            risk_score = min(100, risk_score + 30)
            critic_notes.append("WARNING: Unsigned package.")

        annotated_package = {
            **package,
            "import_timestamp": datetime.now().isoformat(),
            "critic_scan": {
                "risk_score": risk_score,
                "notes": critic_notes
            }
        }

        # Store in review queue
        data = await self.vault.retrieve_secret(self.review_queue_id)
        queue = data.get("queue", [])
        queue.append(annotated_package)
        await self.vault.store_secret(self.review_queue_id, {"queue": queue})
        
        logger.info(f"Tool {package.get('name')} imported to Review Queue. Risk: {risk_score}")
        return {"status": "queued", "risk_score": risk_score, "notes": critic_notes}

    async def promote_from_queue(self, tool_id: str) -> bool:
        """Moves a tool from review queue to active registry."""
        data = await self.vault.retrieve_secret(self.review_queue_id)
        queue = data.get("queue", [])
        
        target = next((s for s in queue if s.get("id") == tool_id), None)
        if not target:
            return False
            
        # Remove from queue
        new_queue = [s for s in queue if s.get("id") != tool_id]
        await self.vault.store_secret(self.review_queue_id, {"queue": new_queue})
        
        # Add to active registry
        # Clean up temporary fields
        if "import_timestamp" in target:
            del target["import_timestamp"]
        if "critic_scan" in target:
            del target["critic_scan"]
        target["verified"] = True
        
        await self.save_tool(target)
        logger.info(f"Tool {tool_id} PROMOTED to Active Registry.")
        return True

    async def save_tool(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """Create or Update a tool manifest."""
        try:
            validated_tool = ToolManifest(**tool).model_dump()
        except Exception as ve:
            logger.error(f"Failed to save tool: {ve}")
            raise ValueError(f"Invalid Tool Schema: {ve}")
            
        tool = validated_tool
        
        data = await self.vault.retrieve_secret(self.registry_id)
        current_tools = data.get("tools", [])
        
        # Check if exists (update) or create
        existing_idx = next((i for i, s in enumerate(current_tools) if s.get("id") == tool.get("id")), -1)
        
        # Inject metadata if missing
        if "verified" not in tool:
            tool["verified"] = True
        
        # Initialize monitoring fields
        if "last_active" not in tool:
            tool["last_active"] = datetime.now().isoformat()
        if "error" not in tool:
            tool["error"] = None
        
        if existing_idx >= 0:
            current_tools[existing_idx] = tool
            action = "UPDATED"
        else:
            current_tools.append(tool)
            action = "CREATED"
            
        await self.vault.store_secret(self.registry_id, {"tools": current_tools})
        logger.info(f"Tool {tool.get('id', 'unknown')} {action} in Simplicial Vault.")
        return tool

    async def get_tool(self, tool_id: str) -> Optional[Dict[str, Any]]:
        tools = await self.list_tools()
        return next((s for s in tools if s.get("id") == tool_id), None)

    async def delete_tool(self, tool_id: str) -> bool:
        """Remove a tool from the registry."""
        data = await self.vault.retrieve_secret(self.registry_id)
        current_tools = data.get("tools", [])
        
        new_tools = [s for s in current_tools if s.get("id") != tool_id]
        if len(new_tools) == len(current_tools):
            return False
            
        await self.vault.store_secret(self.registry_id, {"tools": new_tools})
        logger.info(f"Tool {tool_id} DELETED from Simplicial Vault.")
        return True

    async def get_tools_for_runtime(self, active_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Retrieves selected tools for injection into the LCE execution (function calling).
        """
        all_tools = await self.registry_list()
        selected = [s for s in all_tools if s.get("id") in active_ids]
        
        try:
            import importlib
            import asyncio
            import os
            services = importlib.import_module("backend.services")
            hlsm = getattr(services, "hlsm_manager", None)
            if hlsm:
                for tool in selected:
                    ref_docs = tool.get("reference_docs", [])
                    tool_id = tool.get("id")
                    if ref_docs and tool_id:
                        for doc_path in ref_docs:
                            if doc_path.startswith("http://") or doc_path.startswith("https://"):
                                asyncio.create_task(self._quarantine_and_ingest_url(doc_path, tool_id, hlsm))
                            else:
                                full_path = doc_path
                                if not os.path.isabs(full_path):
                                    full_path = os.path.join(os.path.expanduser("~/Downloads/alluci-sovereign-agent-main"), doc_path)
                                asyncio.create_task(self._quarantine_and_ingest_local(full_path, doc_path, tool_id, hlsm))
        except Exception as e:
            logger.error(f"Failed to dispatch reference_docs ingestion for tools: {e}")
            
        return selected

    async def _quarantine_and_ingest_url(self, url: str, tool_id: str, hlsm: Any):
        import httpx
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(url, timeout=15.0)
                resp.raise_for_status()
                content = resp.text
            await self._quarantine_and_ingest(url, content, tool_id, hlsm, is_remote=True)
        except Exception as e:
            logger.error(f"Failed to fetch remote reference doc {url}: {e}")

    async def _quarantine_and_ingest_local(self, full_path: str, doc_path: str, tool_id: str, hlsm: Any):
        import os
        if not os.path.exists(full_path):
            logger.warning(f"Local reference doc not found: {full_path}")
            return
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            await self._quarantine_and_ingest(doc_path, content, tool_id, hlsm, is_remote=False)
        except Exception as e:
            logger.error(f"Failed to read local reference doc {full_path}: {e}")

    async def _quarantine_and_ingest(self, source_path: str, content: str, component_id: str, hlsm: Any, is_remote: bool):
        from backend.security.guardrail import GuardrailScanner
        from backend.inference.router import ModelRouter
        from backend.config import settings
        from backend import services
        import hashlib
        import os
        import zlib
        
        doc_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        cache_key = f"doc_hash_{source_path}"
        cached_hash = await self.get_tool_key(component_id, cache_key)
        
        if cached_hash == doc_hash:
            if services.ws_gw:
                await services.ws_gw.broadcast_event('doc.ingest.status', {'source_path': source_path, 'status': 'Already Ingested', 'component_id': component_id})
            return  # Already ingested

        if services.ws_gw:
            await services.ws_gw.broadcast_event('doc.ingest.status', {'source_path': source_path, 'status': 'Quarantined / Scanning...', 'component_id': component_id})

        # 1. Quarantine Buffer Validation
        scanner = GuardrailScanner(ModelRouter(settings=settings, vault=self.vault))
        safe, msg = await scanner.scan_input(content[:15000]) # Scan head to prevent OOM
        if not safe:
            logger.critical(f"Topological Rupture Detected during ingestion of {source_path}: {msg}")
            if services.ws_gw:
                await services.ws_gw.broadcast_event('doc.ingest.status', {'source_path': source_path, 'status': 'Error: Topological Rupture Detected', 'component_id': component_id})
            return
            
        # 2. Store as Blob Cache
        blob_dir = os.path.expanduser("~/.polytope/alluci_vault/blobs")
        os.makedirs(blob_dir, mode=0o700, exist_ok=True)
        blob_path = os.path.join(blob_dir, f"{doc_hash}.blob")
        
        with open(blob_path, "wb") as f:
            f.write(zlib.compress(content.encode('utf-8')))
            
        # 3. Embed Topological Barcode Pointer into H-LSM
        logger.info(f"Ingesting Topological Barcode for {source_path} (Component: {component_id})...")
        await hlsm.store(
            content=f"Reference Document Barcode for {source_path}. Contains comprehensive architectural or API integration knowledge.",
            metadata={
                "source": source_path,
                "tool_id": component_id,
                "type": "reference_doc",
                "is_barcode": True,
                "uri": source_path,
                "blob_path": blob_path,
                "ttl": 86400.0 if is_remote else 0.0,
            }
        )
        await self.store_tool_key(component_id, cache_key, doc_hash)
        
        if services.ws_gw:
            await services.ws_gw.broadcast_event('doc.ingest.status', {'source_path': source_path, 'status': 'Embedded in H-LSM', 'component_id': component_id})

    async def registry_list(self) -> List[Dict[str, Any]]:
        """Internal helper to list tools from registry."""
        data = await self.vault.retrieve_secret(self.registry_id)
        return data.get("tools", [])

    async def get_tool_status(self, tool_id: str) -> Dict[str, Any]:
        """Dependency check, health, and error reporting for a skill."""
        tool = await self.get_tool(tool_id)
        if not tool:
            return {"status": "error", "message": "Tool not found"}

        # Dependency check
        dependencies = tool.get("dependencies", [])
        active_tools = await self.list_tools()
        active_ids = {s.get("id") for s in active_tools}
        
        missing = [dep for dep in dependencies if dep not in active_ids]
        
        health = "HEALTHY"
        if missing:
            health = "DEPENDENCY_MISSING"
        elif tool.get("error"):
            health = "UNHEALTHY"

        return {
            "id": tool_id,
            "status": health,
            "dependencies": {
                "total": len(dependencies),
                "missing": missing,
                "satisfied": [d for d in dependencies if d in active_ids]
            },
            "last_error": tool.get("error"),
            "last_active": tool.get("last_active", datetime.now().isoformat())
        }

    async def store_tool_key(self, tool_id: str, key_name: str, key_value: str):
        """Securely store a tool-specific secret in the vault."""
        vault_key = f"tool_secret_{tool_id}"
        current = await self.vault.retrieve_secret(vault_key)
        current[key_name] = key_value
        await self.vault.store_secret(vault_key, current)
        logger.info(f"Stored secret '{key_name}' for tool {tool_id}")

    async def get_tool_key(self, tool_id: str, key_name: str) -> Optional[str]:
        """Retrieve a tool-specific secret."""
        vault_key = f"tool_secret_{tool_id}"
        current = await self.vault.retrieve_secret(vault_key)
        return current.get(key_name)

    async def install_remote_package(self, download_url: str) -> Dict[str, Any]:
        """
        One-Click Install flow (Sovereign Spec §5.2).
        Flow: download → validate → critic scan → review queue
        If risk score is 0, auto-promote is possible (optional).
        """
        import httpx

        MAX_PACKAGE_SIZE = 10 * 1024 * 1024  # 10 MB
        REQUIRED_FIELDS = {"id", "name", "version"}
        DOWNLOAD_TIMEOUT = 30.0  # seconds

        logger.info(f"Downloading remote tool package from: {download_url}")

        # 1. Download the package over HTTP
        try:
            async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
                response = await client.get(download_url)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Tool download failed (HTTP {e.response.status_code}): {download_url}")
            return {"error": f"Download failed: HTTP {e.response.status_code}", "url": download_url}
        except httpx.RequestError as e:
            logger.error(f"Tool download network error: {e}")
            return {"error": f"Network error: {e}", "url": download_url}

        # 2. Enforce size limit
        content = response.content
        if len(content) > MAX_PACKAGE_SIZE:
            logger.warning(f"Tool package exceeds size limit ({len(content)} > {MAX_PACKAGE_SIZE})")
            return {"error": f"Package too large ({len(content)} bytes, max {MAX_PACKAGE_SIZE})", "url": download_url}

        # 3. Parse and validate package structure
        import json as _json
        try:
            package = _json.loads(content)
        except _json.JSONDecodeError as e:
            logger.error(f"Tool package is not valid JSON: {e}")
            return {"error": f"Invalid JSON: {e}", "url": download_url}

        if not isinstance(package, dict):
            return {"error": "Package must be a JSON object", "url": download_url}

        missing_fields = REQUIRED_FIELDS - set(package.keys())
        if missing_fields:
            return {"error": f"Missing required fields: {missing_fields}", "url": download_url}

        # 4. Ensure deterministic ID (prevent duplicates from re-download)
        if "id" not in package or not package["id"]:
            package["id"] = f"skill_{int(datetime.now().timestamp())}"

        logger.info(f"Package validated: {package.get('name', '?')} v{package.get('version', '?')}")

        # 5. Trigger the existing import flow (critic scan + queue)
        import_res = await self.import_package(package)
        return {
            **import_res,
            "id": package["id"],
            "url": download_url,
            "status": "QUEUED_FOR_REVIEW"
        }
