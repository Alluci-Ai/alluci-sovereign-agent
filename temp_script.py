import asyncio
from backend.config import settings
from backend.security.vault import VaultManager
from backend.skill_manager import SkillManager
import json

async def inspect():
    vault = VaultManager(settings.POLYTOPE_MASTER_KEY)
    sm = SkillManager(vault)
    skills = await sm.list_skills()
    print("ALL SKILLS:")
    for s in skills:
        id_val = s.get("id")
        src_val = s.get("source", "vault")
        print(f"- {id_val} (source={src_val})")
        if id_val == "dr_skill_01" or id_val == "aar_cognitive_framework":
            print(json.dumps(s, indent=2))

asyncio.run(inspect())
