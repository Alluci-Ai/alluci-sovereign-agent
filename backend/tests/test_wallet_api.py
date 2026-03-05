import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

@pytest.fixture
def wallet_client(mock_settings):
    """Create a test client with mocked wallet service and authentication."""
    with patch('backend.config.load_settings', return_value=mock_settings), \
         patch('backend.database.load_settings', return_value=mock_settings):
        
        from backend.app import app
        import backend.app as app_module
        
        # Mock the wallet_service
        app_module.wallet_service = AsyncMock()
        
        client = TestClient(app, raise_server_exceptions=False)
        yield client, app_module.wallet_service

class TestWalletAPI:
    """Tests for Phase 2 Wallet API routes."""

    def get_headers(self, client, mock_settings):
        login_resp = client.post("/auth/login", json={"key": mock_settings.POLYTOPE_MASTER_KEY})
        token = login_resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_get_currencies(self, wallet_client, mock_settings):
        client, mock_service = wallet_client
        mock_service.get_currencies.return_value = [{"name": "VRSC", "currencyid": "i5w5u9rRzSNoQit8966Y5w57v6Kue91S9B"}]
        
        response = client.get("/api/wallet/currencies", headers=self.get_headers(client, mock_settings))
        assert response.status_code == 200
        assert response.json() == [{"name": "VRSC", "currencyid": "i5w5u9rRzSNoQit8966Y5w57v6Kue91S9B"}]

    def test_wallet_convert(self, wallet_client, mock_settings):
        client, mock_service = wallet_client
        mock_service.convert.return_value = {"success": True, "txid": "test_txid"}
        
        payload = {
            "amount": 10.0,
            "from_currency": "VRSC",
            "to_currency": "vETH",
            "via": "Bridge.vETH"
        }
        response = client.post("/api/wallet/convert", json=payload, headers=self.get_headers(client, mock_settings))
        assert response.status_code == 200
        assert response.json()["txid"] == "test_txid"

    def test_wallet_convert_estimate(self, wallet_client, mock_settings):
        client, mock_service = wallet_client
        mock_service.get_conversion_estimate.return_value = {"estimated_return": 9.95, "estimated": True}
        
        payload = {
            "amount": 10.0,
            "from_currency": "VRSC",
            "to_currency": "vETH"
        }
        response = client.post("/api/wallet/convert/estimate", json=payload, headers=self.get_headers(client, mock_settings))
        assert response.status_code == 200
        assert response.json()["estimated_return"] == 9.95

    def test_create_invoice(self, wallet_client, mock_settings):
        client, mock_service = wallet_client
        mock_invoice = {
            "address": "RTestAddress",
            "amount": 5.0,
            "currency": "VRSC",
            "uri": "verus:RTestAddress?amount=5",
            "success": True
        }
        mock_service.create_invoice.return_value = mock_invoice
        
        payload = {"amount": 5.0, "currency": "VRSC", "memo": "Invoice Test"}
        response = client.post("/api/wallet/invoice", json=payload, headers=self.get_headers(client, mock_settings))
        assert response.status_code == 200
        assert response.json()["address"] == "RTestAddress"
