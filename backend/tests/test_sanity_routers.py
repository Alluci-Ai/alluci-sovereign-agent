import asyncio
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

# Import routers
from backend.routers import goals as goals_router
from backend.routers import memory as memory_router
from backend.routers import security as security_router

# Dummy auth dependency that always passes
async def dummy_auth():
    return True

# Dummy CSRF dependency that does nothing
class DummyCsrfProtect:
    async def validate_csrf(self, request):
        return None

# Stub services implementations
class DummyGoalEngine:
    async def list_goals(self, status=None):
        return []
    async def create_goal(self, title, description, priority):
        return 1
    async def get_goal(self, goal_id):
        return {"id": goal_id, "title": "test", "description": "desc", "priority": "MEDIUM"}
    async def update_goal(self, goal_id, **kwargs):
        return True
    async def delete_goal(self, goal_id):
        return True

class DummyMemory:
    async def list_entries(self, limit=50, offset=0):
        return []
    async def search(self, q, limit=10):
        return []
    async def store(self, content, metadata=None):
        return {"status": "STORED"}
    async def get_stats(self):
        return {}
    async def delete(self, entry_id):
        return True

class DummyHLSMManager:
    async def consolidation_sweep(self):
        return {}

# Apply stubs to the services module
import backend.services as services
services.goal_engine = DummyGoalEngine()
services.memory = DummyMemory()
services.hlsm_manager = DummyHLSMManager()

# Patch security resolution manager to always succeed
import backend.security.resolution as resolution_mod
resolution_mod.resolution_manager.provide_resolution = lambda *args, **kwargs: True

app = FastAPI()
# Override auth dependency for each router
app.dependency_overrides[goals_router.verify_authenticated] = dummy_auth
app.dependency_overrides[memory_router.verify_authenticated] = dummy_auth
# No auth dependency for security router
# Override CSRF dependency
app.dependency_overrides[goals_router.CsrfProtect] = lambda: DummyCsrfProtect()
app.dependency_overrides[memory_router.CsrfProtect] = lambda: DummyCsrfProtect()
# No CSRF dependency for security router

# Include routers
app.include_router(goals_router.router)
app.include_router(memory_router.router)
app.include_router(security_router.router)

client = TestClient(app)

def test_goals_list():
    response = client.get("/goals/")
    assert response.status_code == 200
    assert response.json() == []

def test_memory_list():
    response = client.get("/memory")
    assert response.status_code == 200
    assert response.json() == []

def test_security_resolve_cancel():
    payload = {"task_id": "dummy", "resolution_type": "CANCEL_TASK"}
    response = client.post("/security/resolve", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "success"
