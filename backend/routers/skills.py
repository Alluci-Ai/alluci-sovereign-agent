import os
import json
import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from ..security.auth import verify_authenticated
from ..logging_config import get_logger
from ..config import settings

logger = get_logger("SkillsRouter")
router = APIRouter(tags=["Skills Vault"])

SKILLS_DIR = "alluci_vault/skills"

@router.get("/skills")
async def get_all_skills():
    """Retrieve all dynamically loaded skills from the vault."""
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

@router.put("/skills/{skill_id}", dependencies=[Depends(verify_authenticated)])
async def save_skill(skill_id: str, payload: Dict[str, Any] = Body(...)):
    """Creates or Updates a skill in the local vault."""
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
        return {"status": "SUCCESS", "skill_id": safe_id}
    except Exception as e:
        logger.error(f"Failed to save skill {safe_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to write skill to vault")

@router.delete("/skills/{skill_id}", dependencies=[Depends(verify_authenticated)])
async def delete_skill(skill_id: str):
    """Deletes a skill from the local vault."""
    safe_id = "".join(c for c in skill_id if c.isalnum() or c in ("-", "_"))
    file_path = os.path.join(SKILLS_DIR, f"{safe_id}.json")
    if os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f"Skill {safe_id} deleted from vault.")
        return {"status": "SUCCESS"}
    raise HTTPException(status_code=404, detail="Skill not found")
