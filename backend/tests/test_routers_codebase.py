import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.routers.codebase import router
from backend.security.auth import verify_authenticated
from backend import services

async def mock_auth():
    return True

app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)


def test_get_workspace_tree():
    res = client.get("/codebase/tree?max_depth=2")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "directory"
    assert "children" in data


def test_get_file_catalog():
    res = client.get("/codebase/catalog?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_ast_symbols():
    res = client.get("/codebase/symbols?files=backend/models.py")
    assert res.status_code == 200
    data = res.json()
    assert "files" in data


def test_read_file_snippet_valid():
    res = client.get("/codebase/snippet?path=ARCHITECTURE.md&start=1&end=5")
    assert res.status_code == 200
    data = res.json()
    assert data["path"] == "ARCHITECTURE.md"
    assert data["start_line"] == 1
    assert data["end_line"] == 5


def test_read_file_snippet_not_found():
    res = client.get("/codebase/snippet?path=nonexistent_file_12345.xyz")
    assert res.status_code == 404


def test_read_file_snippet_traversal():
    res = client.get("/codebase/snippet?path=../../etc/passwd")
    assert res.status_code == 400


def test_get_architecture():
    res = client.get("/codebase/architecture")
    assert res.status_code == 200
    data = res.json()
    assert "pillars" in data
    assert len(data["pillars"]) == 5


def test_get_git_status():
    res = client.get("/codebase/git")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "recent_commits" in data


def test_get_github_overview():
    services.vault = MagicMock()
    services.vault.retrieve_secret = AsyncMock(return_value={"token": "fake", "repository": "Alluci-Ai/alluci-sovereign-agent"})

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "full_name": "Alluci-Ai/alluci-sovereign-agent",
            "description": "Enterprise Sovereign Agent",
            "default_branch": "main",
            "stargazers_count": 50
        }
        mock_get.return_value = mock_resp

        res = client.get("/codebase/github")
        assert res.status_code == 200
        data = res.json()
        assert "overview" in data


@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_index_codebase_not_ready(mock_csrf):
    services.hlsm_manager = None
    res = client.post("/codebase/index")
    assert res.status_code == 503


@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_index_codebase_success(mock_csrf):
    mock_hlsm = MagicMock()
    mock_hlsm.l1_store = AsyncMock(return_value="mem_123")
    services.hlsm_manager = mock_hlsm

    try:
        res = client.post("/codebase/index")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["indexed_entries"] > 0
    finally:
        services.hlsm_manager = None
        services.vault = None
