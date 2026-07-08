import os
import json
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Body
from ..logging_config import get_logger

logger = get_logger("SkillsRouter")
router = APIRouter(tags=["Skills Vault"])

SKILLS_DIR = "alluci_vault/skills"

@router.get("/skills")
async def get_all_skills():
    """Retrieve all dynamically loaded skills from the vault."""
    from .. import services
    if services.skill_manager:
        try:
            return await services.skill_manager.list_skills()
        except Exception as e:
            logger.error(f"Failed to list skills via SkillManager: {e}")
            
    skill_map = {}
    # Load core skills first
    CORE_DIR = "core_skills"
    if os.path.exists(CORE_DIR):
        for filename in os.listdir(CORE_DIR):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(CORE_DIR, filename), "r") as f:
                        skill = json.load(f)
                        skill_map[skill["id"]] = skill
                except Exception as e:
                    logger.error(f"Failed to load core skill {filename}: {e}")
                    
    # Load and override with vault skills
    if os.path.exists(SKILLS_DIR):
        for filename in os.listdir(SKILLS_DIR):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(SKILLS_DIR, filename), "r") as f:
                        skill = json.load(f)
                        skill_map[skill["id"]] = skill
                except Exception as e:
                    logger.error(f"Failed to load vault skill {filename}: {e}")
                    
    return list(skill_map.values())

@router.put("/skills/{skill_id}")
async def save_skill(skill_id: str, payload: Dict[str, Any] = Body(...)):
    """Creates or Updates a skill in the local vault."""
    # Enforce Skill Boundary
    category = payload.get("category", "FRAMEWORK")
    if category in ["TOOL", "MCP"]:
        raise HTTPException(status_code=400, detail="Cannot save TOOL category to Skills endpoint. Use /api/v1/tools")
        
    os.makedirs(SKILLS_DIR, exist_ok=True)
    
    # Secure the skill ID to prevent path traversal
    safe_id = "".join(c for c in skill_id if c.isalnum() or c in ("-", "_"))
    if not safe_id:
        raise HTTPException(status_code=400, detail="Invalid skill ID")
        
    file_path = os.path.join(SKILLS_DIR, f"{safe_id}.json")
    
    # Ensure ID matches
    payload["id"] = safe_id
    
    try:
        with open(file_path, "w") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"Skill {safe_id} saved to vault.")
        
        # Sync to SkillManager if available
        from .. import services
        if services.skill_manager:
            await services.skill_manager.save_skill(payload)
            
        return {"status": "SUCCESS", "skill_id": safe_id}
    except Exception as e:
        logger.error(f"Failed to save skill {safe_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to write skill to vault")

@router.delete("/skills/{skill_id}")
async def delete_skill(skill_id: str):
    """Deletes a skill from the local vault."""
    safe_id = "".join(c for c in skill_id if c.isalnum() or c in ("-", "_"))
    file_path = os.path.join(SKILLS_DIR, f"{safe_id}.json")
    
    deleted = False
    if os.path.exists(file_path):
        os.remove(file_path)
        deleted = True
        logger.info(f"Skill {safe_id} deleted from disk.")
        
    # Sync to SkillManager if available
    from .. import services
    if services.skill_manager:
        manager_deleted = await services.skill_manager.delete_skill(safe_id)
        deleted = deleted or manager_deleted
        
    if deleted:
        return {"status": "SUCCESS"}
    raise HTTPException(status_code=404, detail="Skill not found")

@router.put("/skills/{skill_id}/toggle")
async def toggle_skill(skill_id: str, payload: Dict[str, bool] = Body(...)):
    """Toggles a skill's active state in the toggles.json configuration."""
    if "verified" not in payload and "enabled" not in payload:
        raise HTTPException(status_code=400, detail="Missing 'verified' or 'enabled' field in payload")
    
    # Frontend might send 'verified' or 'enabled', handle both
    is_enabled = payload.get("verified", payload.get("enabled", False))
    
    from ..state_manager import StateManager
    StateManager.set_skill_toggle(skill_id, is_enabled)
    logger.info(f"Skill {skill_id} toggled to {is_enabled}")
    return {"status": "SUCCESS", "skill_id": skill_id, "verified": is_enabled}
