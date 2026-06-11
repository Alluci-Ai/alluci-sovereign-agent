import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.routers.soul import router
from backend.security.auth import verify_authenticated
from backend import services
from backend.models import SoulManifest

async def mock_auth():
    return True

app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)

@pytest.mark.asyncio
@patch("backend.verus_wallet.wallet_service")
def test_get_soul_manifest_vdxf(mock_wallet):
    with patch("backend.routers.soul.settings.VERUS_AUTH_ENABLED", True):
        mock_wallet.get_manifest = AsyncMock(return_value={"a": 1})
        res = client.get("/soul/manifest")
        assert res.status_code == 200
        assert res.json() == {"a": 1}

@pytest.mark.asyncio
@patch("backend.verus_wallet.wallet_service")
def test_get_soul_manifest_vault(mock_wallet):
    with patch("backend.routers.soul.settings.VERUS_AUTH_ENABLED", True):
        mock_wallet.get_manifest = AsyncMock(return_value=None)
        services.vault = AsyncMock()
        services.vault.retrieve_secret.return_value = {"b": 2}
        res = client.get("/soul/manifest")
        assert res.status_code == 200
        assert res.json() == {"b": 2}

@pytest.mark.asyncio
def test_get_soul_manifest_default():
    with patch("backend.routers.soul.settings.VERUS_AUTH_ENABLED", False):
        services.vault = AsyncMock()
        services.vault.retrieve_secret.return_value = None
        res = client.get("/soul/manifest")
        assert res.status_code == 200
        assert "directives" in res.json()

@pytest.mark.asyncio
@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
@patch("backend.verus_wallet.wallet_service")
def test_update_soul_manifest(mock_wallet, mock_csrf):
    with patch("backend.routers.soul.settings.VERUS_AUTH_ENABLED", True):
        with patch("backend.routers.soul.settings.VERUS_ID_IDENTITY", "ID"):
            services.vault = AsyncMock()
            mock_wallet.update_manifest = AsyncMock()
            manifest_payload = SoulManifest().dict()
            res = client.put("/soul/manifest", json=manifest_payload)
            assert res.status_code == 200
            assert res.json() == {"status": "SUCCESS"}
            services.vault.store_secret.assert_called_once()
            mock_wallet.update_manifest.assert_called_once()

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_preview_soul_response_not_ready(mock_csrf):
    services.orchestrator = None
    res = client.post("/soul/preview", json="hello")
    assert res.status_code == 503

@pytest.mark.asyncio
@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_preview_soul_response(mock_csrf):
    services.orchestrator = AsyncMock()
    services.orchestrator.preview_soul_response.return_value = {"response": "hi"}
    res = client.post("/soul/preview", json="hello")
    assert res.status_code == 200
    assert res.json() == {"response": "hi"}

@pytest.mark.asyncio
def test_get_soul_preferences_vault():
    services.vault = AsyncMock()
    services.vault.retrieve_secret.return_value = {"dark_mode": True}
    res = client.get("/soul/preferences")
    assert res.status_code == 200
    assert res.json() == {"dark_mode": True}

@pytest.mark.asyncio
def test_get_soul_preferences_default():
    services.vault = AsyncMock()
    services.vault.retrieve_secret.return_value = None
    res = client.get("/soul/preferences")
    assert res.status_code == 200
    assert "conciseness" in res.json()
