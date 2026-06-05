import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.fixture
def mock_vault_service():
    with patch("backend.routers.vault.services.vault", new_callable=AsyncMock) as mock_v:
        mock_v.rotate_keys.return_value = True
        mock_v.retrieve_secret.return_value = {}
        mock_v.export_identity_pem = MagicMock(return_value="mock_pem")
        yield mock_v

@pytest.fixture
def mock_router_service():
    with patch("backend.routers.vault.services.router", new_callable=AsyncMock) as mock_r:
        mock_r.check_health.return_value = {"openai": "healthy"}
        yield mock_r

def test_rotate_vault_keys_success(app_client, auth_headers, mock_vault_service):
    response = app_client.post("/api/v1/vault/rotate", json={"new_key": "valid_new_key_123"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"status": "success", "message": "All Active Vaults Cryptographically Rotated"}
    mock_vault_service.rotate_keys.assert_called_once_with("valid_new_key_123")

def test_rotate_vault_keys_missing_key(app_client, auth_headers):
    response = app_client.post("/api/v1/vault/rotate", json={}, headers=auth_headers)
    assert response.status_code == 400

def test_rotate_vault_keys_vault_not_ready(app_client, auth_headers):
    with patch("backend.routers.vault.services.vault", None):
        response = app_client.post("/api/v1/vault/rotate", json={"new_key": "valid_new_key_123"}, headers=auth_headers)
        assert response.status_code == 503

def test_rotate_vault_keys_failure(app_client, auth_headers, mock_vault_service):
    mock_vault_service.rotate_keys.return_value = False
    response = app_client.post("/api/v1/vault/rotate", json={"new_key": "valid_new_key_123"}, headers=auth_headers)
    assert response.status_code == 500

def test_export_identity_pem_success(app_client, auth_headers, mock_vault_service):
    response = app_client.post("/api/v1/vault/export-identity-pem", json={"export_passphrase": "super_long_passphrase_here"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["pem"] == "mock_pem"
    mock_vault_service.export_identity_pem.assert_called_once_with("super_long_passphrase_here")

def test_export_identity_pem_too_short(app_client, auth_headers):
    response = app_client.post("/api/v1/vault/export-identity-pem", json={"export_passphrase": "short"}, headers=auth_headers)
    assert response.status_code == 422  # validation error

def test_export_identity_pem_value_error(app_client, auth_headers, mock_vault_service):
    mock_vault_service.export_identity_pem.side_effect = ValueError("Bad passphrase")
    response = app_client.post("/api/v1/vault/export-identity-pem", json={"export_passphrase": "super_long_passphrase_here"}, headers=auth_headers)
    assert response.status_code == 400

def test_flush_vault_success(app_client, auth_headers, mock_vault_service):
    response = app_client.post("/api/v1/vault/flush", headers=auth_headers)
    assert response.status_code == 200
    mock_vault_service.flush_cache.assert_called_once()

def test_flush_vault_not_ready(app_client, auth_headers):
    with patch("backend.routers.vault.services.vault", None):
        response = app_client.post("/api/v1/vault/flush", headers=auth_headers)
        assert response.status_code == 503

def test_check_health_success(app_client, auth_headers, mock_router_service, mock_vault_service):
    response = app_client.post("/api/v1/check-health", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["results"] == {"openai": "healthy"}
    mock_router_service.check_health.assert_called_once()
    mock_vault_service.update_vault_status.assert_called_once_with("openai", "healthy")

def test_check_health_router_not_ready(app_client, auth_headers):
    with patch("backend.routers.vault.services.router", None):
        response = app_client.post("/api/v1/check-health", headers=auth_headers)
        assert response.status_code == 503

def test_get_vault_keys(app_client, auth_headers, mock_vault_service):
    mock_vault_service.retrieve_secret.return_value = {
        "llm": {"openai": "sk-123"},
        "audio": "something_else"
    }
    response = app_client.get("/api/v1/vault/keys", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["llm"]["openai"] == "••••••••••••"
    assert data["audio"] == "something_else"

def test_get_vault_keys_not_ready(app_client, auth_headers):
    with patch("backend.routers.vault.services.vault", None):
        response = app_client.get("/api/v1/vault/keys", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {}

def test_save_vault_keys_success(app_client, auth_headers, mock_vault_service):
    mock_vault_service.retrieve_secret.return_value = {
        "llm": {"openai": "sk-old"},
    }
    response = app_client.post("/api/v1/vault/keys", json={
        "llm": {"openai": "••••••••••••", "anthropic": "sk-new"}
    }, headers=auth_headers)
    
    assert response.status_code == 200
    mock_vault_service.store_secret.assert_called_once()
    saved = mock_vault_service.store_secret.call_args[0][1]
    assert saved["llm"]["openai"] == "sk-old"
    assert saved["llm"]["anthropic"] == "sk-new"

def test_save_vault_keys_not_ready(app_client, auth_headers):
    with patch("backend.routers.vault.services.vault", None):
        response = app_client.post("/api/v1/vault/keys", json={"llm": {}}, headers=auth_headers)
        assert response.status_code == 503

def test_get_vault_keys_error(app_client, auth_headers, mock_vault_service):
    mock_vault_service.retrieve_secret.side_effect = Exception("db error")
    response = app_client.get("/api/v1/vault/keys", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {}

def test_save_vault_keys_error(app_client, auth_headers, mock_vault_service):
    mock_vault_service.retrieve_secret.side_effect = Exception("db error")
    response = app_client.post("/api/v1/vault/keys", json={"llm": {}}, headers=auth_headers)
    assert response.status_code == 500
