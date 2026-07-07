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
            
        return vault_tools + disk_tools

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
        return [s for s in all_tools if s.get("id") in active_ids]

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
