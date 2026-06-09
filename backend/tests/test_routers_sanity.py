import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import routers
from backend.routers.goals import router as goals_router
from backend.routers.memory import router as memory_router
from backend.routers.security import router as security_router
from backend.routers.sessions import router as sessions_router
from backend.routers.tasks import router as tasks_router
from backend.routers.telemetry import router as telemetry_router
from backend.routers.vault import router as vault_router
from backend.routers.voice import router as voice_router
from backend.routers.wallet import router as wallet_router
from backend.routers.websockets import router as websockets_router
from backend.security.auth import verify_authenticated

# Mock authentication dependency
async def mock_auth():
    return True

app = FastAPI()
# Include routers (each router defines its own prefix)
app.include_router(goals_router)
app.include_router(memory_router)
app.include_router(security_router)
app.include_router(sessions_router)
app.include_router(tasks_router)
app.include_router(telemetry_router)
app.include_router(vault_router)
app.include_router(voice_router)
app.include_router(wallet_router)
app.include_router(websockets_router)

# Override authentication dependency for all routers
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)

@pytest.mark.parametrize(
    "path",
    [
        "/goals/",                # List goals (503 if engine not set)
        "/memory",                # List memory (503 if not ready)
        "/security/resolve",      # POST endpoint (400 missing fields)
        "/sessions/",             # Sessions router root (should not 404)
        "/tasks/",                # Tasks router root
        "/telemetry/",            # Telemetry router root
        "/vault/",                # Vault router root
        "/voice/",                # Voice router root
        "/wallet/",               # Wallet router root
        "/ws/",                   # Websockets router prefix (might be /ws)
    ],
)
def test_router_endpoint_accessible(path):
    """Sanity check that each router endpoint is reachable (not 404)."""
    if path == "/security/resolve":
        response = client.post(path, json={"task_id": "t", "resolution_type": "CANCEL_TASK"})
    else:
        response = client.get(path)
    assert response.status_code != 404, f"Endpoint {path} returned 404"
