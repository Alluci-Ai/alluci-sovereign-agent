
import asyncio
import os
from backend.orchestrator import ExecutiveOrchestrator
from backend.inference.router import ModelRouter
from backend.security.vault import VaultManager
from backend.skill_manager import SkillManager
from backend.config import settings

async def test_context():
    vault = VaultManager(settings.POLYTOPE_MASTER_KEY)
    router = ModelRouter(settings, vault=vault)
    skill_manager = SkillManager(vault)
    
    orchestrator = ExecutiveOrchestrator(
        router=router,
        vault=vault,
        ace=None,
        skill_manager=skill_manager,
        analytics=None,
        settings=settings,
        vault_root=os.path.join(os.path.expanduser(settings.POLYTOPE_STORAGE_ROOT), "vaults"),
        approval_manager=None
    )
    
    context = await orchestrator._build_system_context()
    print("--- SYSTEM CONTEXT ---")
    print(context)
    print("--- END CONTEXT ---")

if __name__ == "__main__":
    asyncio.run(test_context())
