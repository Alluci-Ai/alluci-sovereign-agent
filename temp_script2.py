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

asyncio.run(inspect())
