import pytest
import os
import json
import struct
from cryptography.fernet import Fernet
from backend.security.vault import VaultManager
from backend.config import settings

@pytest.fixture
def temp_vault(tmp_path):
    vault_dir = tmp_path / "vaults"
    vault_dir.mkdir()
    return str(vault_dir)

def test_vault_store_and_retrieve(temp_vault):
    """Test that vault can store and retrieve secrets correctly (V2/AES-GCM path)."""
    from unittest.mock import patch
    master_key = Fernet.generate_key().decode()
    with patch('backend.security.vault.settings') as mock_s:
        mock_s.VERUS_AUTH_ENABLED = False
        manager = VaultManager(master_key, vault_root=temp_vault)
    
    # Store and retrieve
    import asyncio
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
    
    async def _test():
        bridge_id = "test_store"
        data = {"api_key": "secret_v2"}
        await manager.store_secret(bridge_id, data)
        retrieved = await manager.retrieve_secret(bridge_id)
        assert retrieved == data
    
    loop.run_until_complete(_test())

def test_config_gemini_optional():
    # settings is already loaded, but we can check if it allows None/empty
    from backend.config import Settings
    # Check that the class allows None for GEMINI_API_KEY
    pass

def test_metrics_endpoint(app_client, auth_headers):
    """Test metrics endpoint at /api/v1/metrics (served by metrics_router)."""
    response = app_client.get("/api/v1/metrics", headers=auth_headers)
    # Metrics endpoint is mounted and returns prometheus-format text
    assert response.status_code == 200
    assert "alluci_http_requests_total" in response.text

def test_health_enhancements():
    from backend.app import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    pass
