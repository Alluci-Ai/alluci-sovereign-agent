import yaml  # type: ignore
import os
from .logging_config import get_logger
from typing import List, Dict, Any, Optional
from datetime import datetime
from .security.vault import VaultManager

logger = get_logger("SkillManager")

class SkillManager:
    def __init__(self, vault: VaultManager, skills_dir: Optional[str] = None, workspace_skills_dir: Optional[str] = "alluci_vault/skills"):
        self.vault = vault
        self.skills_dir = skills_dir or os.path.expanduser("~/.polytope/skills")
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir, mode=0o700, exist_ok=True)
        self.workspace_skills_dir = workspace_skills_dir
            
        self.registry_id = "cognitive_registry"
        self.review_queue_id = "skill_review_queue"

    async def list_skills(self) -> List[Dict[str, Any]]:
        """Retrieve all active skills from both the vault and the local disk (P1-012)."""
        # 1. Load from Vault
        data = await self.vault.retrieve_secret(self.registry_id)
        vault_skills = data.get("skills", [])
        
        # 2. Load from Disk (user ~/.polytope/skills, workspace alluci_vault/skills, and core_skills)
        disk_skills = []
        dirs_to_scan = [self.skills_dir]
        if self.workspace_skills_dir:
            dirs_to_scan.append(self.workspace_skills_dir)
        core_skills_dir = os.path.join(os.getcwd(), "core_skills")
        if os.path.exists(core_skills_dir):
            dirs_to_scan.append(core_skills_dir)
            
        seen_ids = set()
        
        for s in vault_skills:
            if "id" in s:
                seen_ids.add(s["id"])
                
        for d in dirs_to_scan:
            if not os.path.exists(d):
                continue
            try:
                for filename in os.listdir(d):
                    file_path = os.path.join(d, filename)
                    skill_data = None
                    if filename.endswith((".yaml", ".yml")):
                        with open(file_path, "r") as f:
                            skill_data = yaml.safe_load(f)
                    elif filename.endswith(".json"):
                        import json
                        with open(file_path, "r") as f:
                            skill_data = json.load(f)
                            
                    if skill_data and "id" in skill_data:
                        if skill_data["id"] not in seen_ids:
                            skill_data["source"] = "disk"
                            if "verified" not in skill_data:
                                skill_data["verified"] = True
                            disk_skills.append(skill_data)
                            seen_ids.add(skill_data["id"])
            except Exception as e:
                logger.error(f"Failed to load skills from disk dir {d}: {e}")
            
        all_skills = vault_skills + disk_skills
        from .state_manager import StateManager
        toggles = StateManager.get_skill_toggles()
        for skill in all_skills:
            if skill.get("id") in toggles:
                skill["verified"] = toggles[skill["id"]]
            elif "verified" not in skill:
                skill["verified"] = True
                
        return all_skills

    def list_skills_sync(self) -> List[Dict[str, Any]]:
        """Synchronously scan disk skills for high-performance prompt resolution."""
        disk_skills = []
        dirs_to_scan = [self.skills_dir]
        if self.workspace_skills_dir:
            dirs_to_scan.append(self.workspace_skills_dir)
        core_skills_dir = os.path.join(os.getcwd(), "core_skills")
        if os.path.exists(core_skills_dir):
            dirs_to_scan.append(core_skills_dir)
            
        seen_ids = set()
        for d in dirs_to_scan:
            if not os.path.exists(d):
                continue
            try:
                for filename in os.listdir(d):
                    file_path = os.path.join(d, filename)
                    skill_data = None
                    if filename.endswith((".yaml", ".yml")):
                        with open(file_path, "r") as f:
                            skill_data = yaml.safe_load(f)
                    elif filename.endswith(".json"):
                        import json
                        with open(file_path, "r") as f:
                            skill_data = json.load(f)
                            
                    if skill_data and "id" in skill_data:
                        if skill_data["id"] not in seen_ids:
                            skill_data["source"] = "disk"
                            disk_skills.append(skill_data)
                            seen_ids.add(skill_data["id"])
            except Exception as e:
                logger.error(f"Sync load failed for dir {d}: {e}")
        return disk_skills

    def resolve_skill_context_for_prompt(self, prompt: str) -> Optional[str]:
        """
        Dynamically matches single or multiple active skills from user prompt tokens,
        including natural language skill titles, internal methodologies, mindsets, and concepts.
        Formats a structured <COGNITIVE_SKILL_CONTEXT> block for LLM system injection.
        """
        if not prompt or not prompt.strip():
            return None
            
        prompt_lower = prompt.lower()
        skills = self.list_skills_sync()
        matched_skills = []
        
        for skill in skills:
            skill_id = str(skill.get("id", "")).lower()
            skill_name = str(skill.get("name", "")).lower()
            methodologies = [str(m) for m in skill.get("methodologies", [])]
            frameworks = [str(f) for f in skill.get("frameworks", [])]
            knowledge = [str(k) for k in skill.get("knowledge", [])]
            capabilities = [str(c) for c in skill.get("capabilities", [])]
            mindsets = [str(m) for m in skill.get("mindsets", [])]
            
            concept_terms = methodologies + frameworks + knowledge + capabilities + mindsets
            
            is_match = False
            
            # 1. Direct ID match (e.g., hcd_01) or full natural name match (e.g., human centered design)
            if (skill_id and skill_id in prompt_lower) or (skill_name and skill_name in prompt_lower):
                is_match = True
            elif skill_name:
                # 2. Multi-word title matching (e.g. "human centered" or "design thinking")
                name_words = [w for w in skill_name.split() if len(w) > 3]
                if name_words and all(w in prompt_lower for w in name_words):
                    is_match = True
            
            # 3. Methodological concept & keyword matching (e.g., "journey mapping", "usability testing", "ethnographic", "user research")
            if not is_match:
                for term in concept_terms:
                    spaced_term = "".join([f" {c.lower()}" if c.isupper() else c for c in term]).replace("_", " ").strip().lower()
                    clean_term = term.replace("_", " ").strip().lower()
                    term_lower = term.lower()
                    
                    if (term_lower and len(term_lower) > 3 and term_lower in prompt_lower) or \
                       (clean_term and len(clean_term) > 3 and clean_term in prompt_lower) or \
                       (spaced_term and len(spaced_term) > 3 and spaced_term in prompt_lower):
                        is_match = True
                        break
                        
            # 4. Common conversational aliases for core skills
            if not is_match and skill_id == "hcd_01":
                hcd_aliases = ["user experience", "user research", "empathy mapping", "design thinking", "human-centered", "human centered"]
                if any(alias in prompt_lower for alias in hcd_aliases):
                    is_match = True

            if not is_match and skill_id == "codi_01":
                codi_aliases = ["opencode", "codi", "ast diff", "lsp diagnose", "lsp", "checkpoint", "rollback", "refactor", "software engineer", "codebase", "unit test", "type safety", "coding"]
                if any(alias in prompt_lower for alias in codi_aliases):
                    is_match = True
                    
            if is_match and skill not in matched_skills:
                matched_skills.append(skill)
                    
        if not matched_skills:
            return None
            
        context_blocks = []
        for s in matched_skills:
            m_list = s.get("mindsets", [])
            meth_list = s.get("methodologies", [])
            chains = s.get("chainsOfThought", [])
            logic = s.get("logic", [])
            logic_str = logic[0] if isinstance(logic, list) and logic else str(logic)
            best_practices = s.get("bestPractices", [])
            
            block = (
                f"<COGNITIVE_SKILL_CONTEXT id=\"{s.get('id')}\" name=\"{s.get('name')}\">\n"
                f"Description: {s.get('description', '')}\n"
                f"Mindsets: {', '.join(m_list) if m_list else 'N/A'}\n"
                f"Methodologies: {', '.join(meth_list) if meth_list else 'N/A'}\n"
                f"Chains of Thought:\n" + ("\n".join([f"  - {c}" for c in chains]) if chains else "  - N/A") + "\n"
                f"Logic: {logic_str}\n"
                f"Best Practices:\n" + ("\n".join([f"  - {bp}" for bp in best_practices]) if best_practices else "  - N/A") + "\n"
                f"</COGNITIVE_SKILL_CONTEXT>"
            )
            context_blocks.append(block)
            
        return "\n\n".join(context_blocks)

    def detect_context_switch(self, current_prompt: str, active_skill_ids: List[str]) -> bool:
        """
        Detects if the current prompt signals a context switch away from previously active skills.
        """
        if not current_prompt or not active_skill_ids:
            return False
            
        prompt_lower = current_prompt.lower()
        switch_indicators = ["switch to", "new topic", "different task", "forget skills", "clear skills", "move on to", "next task"]
        if any(ind in prompt_lower for ind in switch_indicators):
            return True
            
        return False


    async def get_review_queue(self) -> List[Dict[str, Any]]:
        """Retrieve skills pending review."""
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
        Analyze the following cognitive package payload for security risks, remote execution vulnerabilities, and malicious patterns.
        
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
        
        logger.info(f"Skill {package.get('name')} imported to Review Queue. Risk: {risk_score}")
        return {"status": "queued", "risk_score": risk_score, "notes": critic_notes}

    async def promote_from_queue(self, skill_id: str) -> bool:
        """Moves a skill from review queue to active registry."""
        data = await self.vault.retrieve_secret(self.review_queue_id)
        queue = data.get("queue", [])
        
        target = next((s for s in queue if s.get("id") == skill_id), None)
        if not target:
            return False
            
        # Remove from queue
        new_queue = [s for s in queue if s.get("id") != skill_id]
        await self.vault.store_secret(self.review_queue_id, {"queue": new_queue})
        
        # Add to active registry
        # Clean up temporary fields
        if "import_timestamp" in target:
            del target["import_timestamp"]
        if "critic_scan" in target:
            del target["critic_scan"]
        target["verified"] = True
        
        await self.save_skill(target)
        logger.info(f"Skill {skill_id} PROMOTED to Active Registry.")
        return True

    async def save_skill(self, skill: Dict[str, Any]) -> Dict[str, Any]:
        """Create or Update a skill manifest."""
        data = await self.vault.retrieve_secret(self.registry_id)
        current_skills = data.get("skills", [])
        
        # Check if exists (update) or create
        existing_idx = next((i for i, s in enumerate(current_skills) if s.get("id") == skill.get("id")), -1)
        
        # Inject metadata if missing
        if "verified" not in skill:
            skill["verified"] = True
        
        # Initialize monitoring fields
        if "last_active" not in skill:
            skill["last_active"] = datetime.now().isoformat()
        if "error" not in skill:
            skill["error"] = None
        
        if existing_idx >= 0:
            current_skills[existing_idx] = skill
            action = "UPDATED"
        else:
            current_skills.append(skill)
            action = "CREATED"
            
        await self.vault.store_secret(self.registry_id, {"skills": current_skills})
        logger.info(f"Skill {skill.get('id', 'unknown')} {action} in Simplicial Vault.")
        return skill

    async def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        skills = await self.list_skills()
        return next((s for s in skills if s.get("id") == skill_id), None)

    async def delete_skill(self, skill_id: str) -> bool:
        """Remove a skill from the registry."""
        data = await self.vault.retrieve_secret(self.registry_id)
        current_skills = data.get("skills", [])
        
        new_skills = [s for s in current_skills if s.get("id") != skill_id]
        if len(new_skills) == len(current_skills):
            return False
            
        await self.vault.store_secret(self.registry_id, {"skills": new_skills})
        logger.info(f"Skill {skill_id} DELETED from Simplicial Vault.")
        return True

    async def merge_skills_for_runtime(self, active_ids: List[str]) -> Dict[str, Any]:
        """
        Merges selected skills into a unified cognitive context.
        """
        all_skills = await self.registry_list() # Helper method to retrieve skills
        active = [s for s in all_skills if s.get("id") in active_ids]
        
        merged = {
            "knowledge": [],
            "mindsets": [],
            "frameworks": [],
            "logic": [],
            "chainsOfThought": [],
            "vectors": {
                "toneShift": 0.0,
                "creativityShift": 0.0,
                "assertivenessShift": 0.0,
                "empathyShift": 0.0
            }
        }
        
        for s in active:
            merged["knowledge"].extend(s.get("knowledge", []))  # type: ignore
            merged["mindsets"].extend(s.get("mindsets", []))  # type: ignore
            merged["frameworks"].extend(s.get("frameworks", []))  # type: ignore
            merged["logic"].extend(s.get("logic", []))  # type: ignore
            merged["chainsOfThought"].extend(s.get("chainsOfThought", []))  # type: ignore
            
            mapping = s.get("personalityMapping", {})
            merged["vectors"]["toneShift"] += mapping.get("toneShift", 0)  # type: ignore
            merged["vectors"]["creativityShift"] += mapping.get("creativityShift", 0)  # type: ignore
            merged["vectors"]["assertivenessShift"] += mapping.get("assertivenessShift", 0)  # type: ignore
            merged["vectors"]["empathyShift"] += mapping.get("empathyShift", 0)  # type: ignore

            # H-LSM Semantic Memory Ingestion for Hybrid RAG-Skills
            ref_docs = s.get("reference_docs", [])
            skill_id = s.get("id")
            if ref_docs and skill_id is not None:
                try:
                    import importlib
                    import asyncio
                    services = importlib.import_module("backend.services")
                    hlsm = getattr(services, "hlsm_manager", None)
                    if hlsm:
                        for doc_path in ref_docs:
                            if doc_path.startswith("http://") or doc_path.startswith("https://"):
                                asyncio.create_task(self._quarantine_and_ingest_url(doc_path, skill_id, hlsm))
                            else:
                                full_path = doc_path
                                if not os.path.isabs(full_path):
                                    full_path = os.path.join(os.path.expanduser("~/Downloads/alluci-sovereign-agent-main"), doc_path)
                                asyncio.create_task(self._quarantine_and_ingest_local(full_path, doc_path, skill_id, hlsm))
                except Exception as e:
                    logger.error(f"Failed to dispatch reference_docs ingestion for skill {skill_id}: {e}")
            
        return merged
        
    async def _quarantine_and_ingest_url(self, url: str, skill_id: str, hlsm: Any):
        import httpx
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                resp = await client.get(url, timeout=15.0)
                resp.raise_for_status()
                content = resp.text
            await self._quarantine_and_ingest(url, content, skill_id, hlsm, is_remote=True)
        except Exception as e:
            logger.error(f"Failed to fetch remote reference doc {url}: {e}")

    async def _quarantine_and_ingest_local(self, full_path: str, doc_path: str, skill_id: str, hlsm: Any):
        import os
        if not os.path.exists(full_path):
            logger.warning(f"Local reference doc not found: {full_path}")
            return
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            await self._quarantine_and_ingest(doc_path, content, skill_id, hlsm, is_remote=False)
        except Exception as e:
            logger.error(f"Failed to read local reference doc {full_path}: {e}")

    async def _quarantine_and_ingest(self, source_path: str, content: str, component_id: str, hlsm: Any, is_remote: bool):
        from backend.security.guardrail import GuardrailScanner
        from backend.inference.router import ModelRouter
        from backend.config import Settings
        from backend import services
        import hashlib
        import os
        import zlib
        
        doc_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
        cache_key = f"doc_hash_{source_path}"
        cached_hash = await self.get_skill_key(component_id, cache_key)
        
        if cached_hash == doc_hash:
            if services.ws_gw:
                await services.ws_gw.broadcast_event('doc.ingest.status', {'source_path': source_path, 'status': 'Already Ingested', 'component_id': component_id})
            return  # Already ingested

        if services.ws_gw:
            await services.ws_gw.broadcast_event('doc.ingest.status', {'source_path': source_path, 'status': 'Quarantined / Scanning...', 'component_id': component_id})

        # 1. Quarantine Buffer Validation
        settings = Settings()  # type: ignore
        scanner = GuardrailScanner(ModelRouter(settings, vault=self.vault))
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
            content=f"Reference Document Barcode for {source_path}. Contains comprehensive architectural or integration knowledge.",
            metadata={
                "source": source_path,
                "skill_id": component_id,
                "type": "reference_doc",
                "is_barcode": True,
                "uri": source_path,
                "blob_path": blob_path,
                "ttl": 86400.0 if is_remote else 0.0,
            }
        )
        await self.store_skill_key(component_id, cache_key, doc_hash)
        
        if services.ws_gw:
            await services.ws_gw.broadcast_event('doc.ingest.status', {'source_path': source_path, 'status': 'Embedded in H-LSM', 'component_id': component_id})

    async def registry_list(self) -> List[Dict[str, Any]]:
        """Internal helper to list skills from registry."""
        data = await self.vault.retrieve_secret(self.registry_id)
        return data.get("skills", [])

    async def get_skill_status(self, skill_id: str) -> Dict[str, Any]:
        """Dependency check, health, and error reporting for a skill."""
        skill = await self.get_skill(skill_id)
        if not skill:
            return {"status": "error", "message": "Skill not found"}

        # Dependency check
        dependencies = skill.get("dependencies", [])
        active_skills = await self.list_skills()
        active_ids = {s.get("id") for s in active_skills}
        
        missing = [dep for dep in dependencies if dep not in active_ids]
        
        health = "HEALTHY"
        if missing:
            health = "DEPENDENCY_MISSING"
        elif skill.get("error"):
            health = "UNHEALTHY"

        return {
            "id": skill_id,
            "status": health,
            "dependencies": {
                "total": len(dependencies),
                "missing": missing,
                "satisfied": [d for d in dependencies if d in active_ids]
            },
            "last_error": skill.get("error"),
            "last_active": skill.get("last_active", datetime.now().isoformat())
        }

    async def store_skill_key(self, skill_id: str, key_name: str, key_value: str):
        """Securely store a skill-specific secret in the vault."""
        vault_key = f"skill_secret_{skill_id}"
        current = await self.vault.retrieve_secret(vault_key)
        current[key_name] = key_value
        await self.vault.store_secret(vault_key, current)
        logger.info(f"Stored secret '{key_name}' for skill {skill_id}")

    async def get_skill_key(self, skill_id: str, key_name: str) -> Optional[str]:
        """Retrieve a skill-specific secret."""
        vault_key = f"skill_secret_{skill_id}"
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

        logger.info(f"Downloading remote skill package from: {download_url}")

        # 1. Download the package over HTTP
        try:
            async with httpx.AsyncClient(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True) as client:
                response = await client.get(download_url)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error(f"Skill download failed (HTTP {e.response.status_code}): {download_url}")
            return {"error": f"Download failed: HTTP {e.response.status_code}", "url": download_url}
        except httpx.RequestError as e:
            logger.error(f"Skill download network error: {e}")
            return {"error": f"Network error: {e}", "url": download_url}

        # 2. Enforce size limit
        content = response.content
        if len(content) > MAX_PACKAGE_SIZE:
            logger.warning(f"Skill package exceeds size limit ({len(content)} > {MAX_PACKAGE_SIZE})")
            return {"error": f"Package too large ({len(content)} bytes, max {MAX_PACKAGE_SIZE})", "url": download_url}

        # 3. Parse and validate package structure
        import json as _json
        try:
            package = _json.loads(content)
        except _json.JSONDecodeError as e:
            logger.error(f"Skill package is not valid JSON: {e}")
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

    async def get_skill_key(self, skill_id: str, key: str) -> Optional[str]:
        cache_id = f"skill_cache_{skill_id}"
        data = await self.vault.retrieve_secret(cache_id)
        return data.get(key)

    async def store_skill_key(self, skill_id: str, key: str, value: str) -> None:
        cache_id = f"skill_cache_{skill_id}"
        data = await self.vault.retrieve_secret(cache_id)
        data[key] = value
        await self.vault.store_secret(cache_id, data)
