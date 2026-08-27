import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from backend.app import create_app
from backend import services

# Assuming create_app() provides the FastAPI instance
# We might need to mock auth if it's protected

app = create_app()

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_auth():
    with patch("backend.security.auth.verify_authenticated", return_value=True):
        yield

def test_save_tool_api(client, mock_auth):
    # Test valid categories
    payload = {
        "id": "test_mcp",
        "name": "Test MCP",
        "category": "MCP",
        "description": "A test MCP tool",
        "enabled": True,
        "execution": {
            "type": "MCP",
            "transport": "stdio",
            "command": "node index.js"
        },
        "schema": {
            "type": "object",
            "properties": {"arg1": {"type": "string"}},
            "required": ["arg1"]
        }
    }
    
    with patch("backend.routers.tools.os.makedirs"):
        with patch("backend.routers.tools.open", create=True):
            with patch("backend.tool_manager.ToolManager.save_tool", new_callable=AsyncMock):
                response = client.put("/api/v1/tools/test_mcp", json=payload)
                assert response.status_code == 200
                assert response.json()["status"] == "SUCCESS"

def test_sandbox_api_success(client, mock_auth):
    payload = {
        "manifest": {
            "id": "test_cli",
            "name": "Test CLI",
            "category": "CLI",
            "execution": {
                "type": "CLI",
                "command": "echo"
            }
        },
        "params": {"arg1": "value"}
    }
    
    mock_scanner_instance = AsyncMock()
    mock_scanner_instance.scan_input = AsyncMock(return_value=(True, "Safe"))
    
    mock_process = MagicMock()
    mock_process.stdout = b"mock output"
    mock_process.stderr = b""
    mock_process.returncode = 0
    
    with patch('backend.routers.tools.GuardrailScanner', return_value=mock_scanner_instance):
        with patch('backend.routers.tools.subprocess.run', return_value=mock_process):
            response = client.post("/api/v1/tools/test_sandbox", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "SUCCESS"
            if data.get("output"):
                assert data["output"] == "mock output"

def test_sandbox_api_rupture(client, mock_auth):
    payload = {
        "manifest": {
            "id": "test_cli",
            "name": "Test CLI",
            "category": "CLI",
            "execution": {
                "type": "CLI",
                "command": "rm -rf /"
            }
        },
        "params": {}
    }
    
    mock_scanner_instance = AsyncMock()
    # Simulate guardrail failure (Topological Rupture)
    mock_scanner_instance.scan_input = AsyncMock(return_value=(False, "Malicious command detected"))
    
    with patch('backend.routers.tools.GuardrailScanner', return_value=mock_scanner_instance):
        response = client.post("/api/v1/tools/test_sandbox", json=payload)
        # Should be forbidden
        assert response.status_code == 403
        assert "Topological Rupture" in response.json()["detail"]

def test_store_tool_secret(client, mock_auth):
    payload = {"secret_value": "super_secret_token"}
    
    with patch("backend.security.vault.VaultManager.store_secret", new_callable=AsyncMock) as mock_store:
        response = client.post("/api/v1/vault/tool-secrets", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert "vault_id" in data
        assert data["vault_id"].startswith("vault_ref_")
        mock_store.assert_called_once()
