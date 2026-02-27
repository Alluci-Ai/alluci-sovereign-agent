
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

    def list_skills(self) -> List[Dict[str, Any]]:
        """Retrieve all active skills from the vault."""
        data = self.vault.retrieve_secret(self.registry_id)
        return data.get("skills", [])

    def get_review_queue(self) -> List[Dict[str, Any]]:
        """Retrieve skills pending review."""
        data = self.vault.retrieve_secret(self.review_queue_id)
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
        data = self.vault.retrieve_secret(self.review_queue_id)
        queue = data.get("queue", [])
        queue.append(annotated_package)
        self.vault.store_secret(self.review_queue_id, {"queue": queue})
        
        logger.info(f"Skill {package.get('name')} imported to Review Queue. Risk: {risk_score}")
        return {"status": "queued", "risk_score": risk_score, "notes": critic_notes}

    def promote_from_queue(self, skill_id: str) -> bool:
        """Moves a skill from review queue to active registry."""
        data = self.vault.retrieve_secret(self.review_queue_id)
        queue = data.get("queue", [])
        
        target = next((s for s in queue if s.get("id") == skill_id), None)
        if not target:
            return False
            
        # Remove from queue
        new_queue = [s for s in queue if s.get("id") != skill_id]
        self.vault.store_secret(self.review_queue_id, {"queue": new_queue})
        
        # Add to active registry
        # Clean up temporary fields
        if "import_timestamp" in target: del target["import_timestamp"]
        if "critic_scan" in target: del target["critic_scan"]
        target["verified"] = True
        
        self.save_skill(target)
        logger.info(f"Skill {skill_id} PROMOTED to Active Registry.")
        return True

    def save_skill(self, skill: Dict[str, Any]) -> Dict[str, Any]:
        """Create or Update a skill manifest."""
        data = self.vault.retrieve_secret(self.registry_id)
        current_skills = data.get("skills", [])
        
        # Check if exists (update) or create
        existing_idx = next((i for i, s in enumerate(current_skills) if s.get("id") == skill.get("id")), -1)
        
        # Inject metadata if missing
        if "verified" not in skill:
            skill["verified"] = True
        
        if existing_idx >= 0:
            current_skills[existing_idx] = skill
            action = "UPDATED"
        else:
            current_skills.append(skill)
            action = "CREATED"
            
        self.vault.store_secret(self.registry_id, {"skills": current_skills})
        logger.info(f"Skill {skill.get('id', 'unknown')} {action} in Simplicial Vault.")
        return skill

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        skills = self.list_skills()
        return next((s for s in skills if s.get("id") == skill_id), None)

    def delete_skill(self, skill_id: str) -> bool:
        """Remove a skill from the registry."""
        data = self.vault.retrieve_secret(self.registry_id)
        current_skills = data.get("skills", [])
        
        new_skills = [s for s in current_skills if s.get("id") != skill_id]
        if len(new_skills) == len(current_skills):
            return False
            
        self.vault.store_secret(self.registry_id, {"skills": new_skills})
        logger.info(f"Skill {skill_id} DELETED from Simplicial Vault.")
        return True

    def merge_skills_for_runtime(self, active_ids: List[str]) -> Dict[str, Any]:
        """
        Merges selected skills into a unified cognitive context.
        """
        all_skills = self.list_skills()
        active = [s for s in all_skills if s["id"] in active_ids]
        
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
