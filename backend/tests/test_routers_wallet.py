import pytest
pytestmark = pytest.mark.unit

from unittest.mock import patch, AsyncMock

def test_get_wallet_status_success(app_client, auth_headers):
    mock_adapter = AsyncMock()
    mock_adapter.get_status.return_value = {"status": "ok"}
    with patch.dict("backend.routers.wallet.services.channel_registry", {"verus_wallet": mock_adapter}):
        response = app_client.get("/api/v1/wallet/status", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

def test_get_wallet_status_no_adapter(app_client, auth_headers):
    with patch.dict("backend.routers.wallet.services.channel_registry", {}, clear=True):
        response = app_client.get("/api/v1/wallet/status", headers=auth_headers)
        assert response.status_code == 503

def test_get_wallet_balance_success(app_client, auth_headers):
    mock_adapter = AsyncMock()
    mock_adapter.get_balance.return_value = {"balance": 100}
    with patch.dict("backend.routers.wallet.services.channel_registry", {"verus_wallet": mock_adapter}):
        response = app_client.get("/api/v1/wallet/balance", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"balance": 100}

def test_get_wallet_balance_no_adapter(app_client, auth_headers):
    with patch.dict("backend.routers.wallet.services.channel_registry", {}, clear=True):
        response = app_client.get("/api/v1/wallet/balance", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"balance": 0, "currency": "VRSC"}

def test_wallet_send_success(app_client, auth_headers):
    mock_adapter = AsyncMock()
    mock_adapter.send_funds.return_value = {"txid": "123"}
    with patch.dict("backend.routers.wallet.services.channel_registry", {"verus_wallet": mock_adapter}):
        response = app_client.post("/api/v1/wallet/send", json={"amount": 10}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"txid": "123"}

def test_wallet_send_no_adapter(app_client, auth_headers):
    with patch.dict("backend.routers.wallet.services.channel_registry", {}, clear=True):
        response = app_client.post("/api/v1/wallet/send", json={"amount": 10}, headers=auth_headers)
        assert response.status_code == 503

def test_get_mining_status_success(app_client, auth_headers):
    mock_adapter = AsyncMock()
    mock_adapter.get_mining_status.return_value = {"mining": True}
    with patch.dict("backend.routers.wallet.services.channel_registry", {"verus_wallet": mock_adapter}):
        response = app_client.get("/api/v1/wallet/mining", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"mining": True}

def test_get_mining_status_no_adapter(app_client, auth_headers):
    with patch.dict("backend.routers.wallet.services.channel_registry", {}, clear=True):
        response = app_client.get("/api/v1/wallet/mining", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"status": "offline"}

def test_get_node_status_success(app_client, auth_headers):
    mock_adapter = AsyncMock()
    mock_adapter.get_node_status.return_value = {"synced": True}
    with patch.dict("backend.routers.wallet.services.channel_registry", {"verus_wallet": mock_adapter}):
        response = app_client.get("/api/v1/wallet/node/status", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"synced": True}

def test_get_node_status_no_adapter(app_client, auth_headers):
    with patch.dict("backend.routers.wallet.services.channel_registry", {}, clear=True):
        response = app_client.get("/api/v1/wallet/node/status", headers=auth_headers)
        assert response.status_code == 503

def test_wallet_node_action_success(app_client, auth_headers):
    mock_adapter = AsyncMock()
    mock_adapter.execute_node_action.return_value = {"result": "started"}
    with patch.dict("backend.routers.wallet.services.channel_registry", {"verus_wallet": mock_adapter}):
        response = app_client.post("/api/v1/wallet/node/action", json={"action": "start"}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"result": "started"}
        mock_adapter.execute_node_action.assert_called_once_with("start")

def test_wallet_node_action_no_adapter(app_client, auth_headers):
    with patch.dict("backend.routers.wallet.services.channel_registry", {}, clear=True):
        response = app_client.post("/api/v1/wallet/node/action", json={"action": "start"}, headers=auth_headers)
        assert response.status_code == 503
