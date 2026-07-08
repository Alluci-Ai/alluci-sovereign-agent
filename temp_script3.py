import asyncio
import os
import yaml
from backend.config import settings
from backend.security.vault import VaultManager
from backend.skill_manager import SkillManager

async def inspect():
    vault = VaultManager(settings.POLYTOPE_MASTER_KEY)
    sm = SkillManager(vault)
    
    dirs_to_scan = [sm.skills_dir, sm.workspace_skills_dir]
    for d in dirs_to_scan:
        if not d or not os.path.exists(d):
            continue
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
                if skill_data["id"] == "aar_cognitive_framework":
                    print(f"FOUND aar_cognitive_framework IN FILE: {file_path}")
                if skill_data["id"] == "dr_skill_01":
                    print(f"FOUND dr_skill_01 IN FILE: {file_path}")

asyncio.run(inspect())
