
import asyncio
import os
from backend.services import init_services, orchestrator, vault
from backend.config import settings

async def test_context():
    # Mock settings for local run
    os.environ["POLYTOPE_MASTER_KEY"] = settings.POLYTOPE_MASTER_KEY
    
    # We need a dummy app for init_services
    class DummyApp:
        pass
    
    await init_services(DummyApp())
    
    context = await orchestrator._build_system_context()
    print("--- SYSTEM CONTEXT ---")
    print(context)
    print("--- END CONTEXT ---")

if __name__ == "__main__":
    asyncio.run(test_context())
