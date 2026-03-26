import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def wallet_client(app_client, mock_settings):
    """Use the existing app_client but inject wallet adapter into the registry."""
    import backend.services as services_module
    
    mock_adapter = AsyncMock()
    
    # channel_registry is a dict in tests; inject the adapter directly
    original_registry = services_module.channel_registry
    services_module.channel_registry = MagicMock()
    services_module.channel_registry.get = MagicMock(return_value=mock_adapter)
    
    yield app_client, mock_adapter
    
    services_module.channel_registry = original_registry


class TestWalletAPI:
    """Tests for Wallet API routes (existing endpoints)."""

    def get_headers(self, client, mock_settings):
        login_resp = client.post("/api/v1/auth/login", json={"key": mock_settings.POLYTOPE_MASTER_KEY})
        token = login_resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_get_wallet_status(self, wallet_client, mock_settings):
        client, mock_adapter = wallet_client
        mock_adapter.get_status = AsyncMock(return_value={"status": "connected", "chain": "VRSC"})

        response = client.get("/api/v1/wallet/status", headers=self.get_headers(client, mock_settings))
        assert response.status_code == 200
        assert response.json()["status"] == "connected"

    def test_get_wallet_balance(self, wallet_client, mock_settings):
        client, mock_adapter = wallet_client
        mock_adapter.get_balance = AsyncMock(return_value={"balance": 42.5, "currency": "VRSC"})

        response = client.get("/api/v1/wallet/balance", headers=self.get_headers(client, mock_settings))
        assert response.status_code == 200
        assert response.json()["currency"] == "VRSC"

    def test_get_mining_status(self, wallet_client, mock_settings):
        client, mock_adapter = wallet_client
        mock_adapter.get_mining_status = AsyncMock(return_value={"status": "active", "hashrate": "1.2 MH/s"})

        response = client.get("/api/v1/wallet/mining", headers=self.get_headers(client, mock_settings))
        assert response.status_code == 200

    def test_wallet_requires_auth(self, wallet_client):
        client, _ = wallet_client
        response = client.get("/api/v1/wallet/status")
        assert response.status_code == 401
