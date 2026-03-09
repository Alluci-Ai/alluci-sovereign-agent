
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from .security.vault import VaultManager

logger = logging.getLogger("SkillManager")

class SkillManager:
    """
    Manages the lifecycle, persistence, and retrieval of Cognitive Modules (Skills).
    Uses the Simplicial Vault for encrypted storage of skill manifests.
    Includes Review Queue for imported skills.
    """
    def __init__(self, vault: VaultManager):
        self.vault = vault
        # We use a dedicated identifier for the skill registry vault
        self.registry_id = "cognitive_registry"
        self.review_queue_id = "skill_review_queue"

    async def list_skills(self) -> List[Dict[str, Any]]:
        """Retrieve all active skills from the vault."""
        data = await self.vault.retrieve_secret(self.registry_id)
        return data.get("skills", [])

    async def get_review_queue(self) -> List[Dict[str, Any]]:
        """Retrieve skills pending review."""
        data = await self.vault.retrieve_secret(self.review_queue_id)
        return data.get("queue", [])

    async def import_package(self, package: Dict[str, Any]) -> Dict[str, Any]:
        """
        Imports a raw package into the review queue.
        In a real system, this would trigger an AI Critic scan.
        """
        # Simulated Critic Scan
        risk_score = 0
        critic_notes = []
        
        if "eval" in str(package):
            risk_score += 90
            critic_notes.append("CRITICAL: Detected 'eval' or unsafe execution pattern.")
        
        if not package.get("signature"):
            risk_score += 50
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
            merged["knowledge"].extend(s.get("knowledge", []))
            merged["mindsets"].extend(s.get("mindsets", []))
            merged["frameworks"].extend(s.get("frameworks", []))
            merged["logic"].extend(s.get("logic", []))
            merged["chainsOfThought"].extend(s.get("chainsOfThought", []))
            
            mapping = s.get("personalityMapping", {})
            merged["vectors"]["toneShift"] += mapping.get("toneShift", 0)
            merged["vectors"]["creativityShift"] += mapping.get("creativityShift", 0)
            merged["vectors"]["assertivenessShift"] += mapping.get("assertivenessShift", 0)
            merged["vectors"]["empathyShift"] += mapping.get("empathyShift", 0)
            
        return merged

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
