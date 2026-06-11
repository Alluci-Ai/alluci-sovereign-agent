import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, patch, MagicMock
from backend.security.credential_store import CredentialStore

@pytest.fixture
def store():
    return CredentialStore()

@pytest.mark.asyncio
@patch("backend.services.vault", new_callable=AsyncMock)
async def test_load_from_vault_success(mock_vault, store):
    mock_vault.retrieve_secret.return_value = {
        "cred1": {"credential_id": "cred1", "public_key": b"pk1".hex()}
    }
    await store.load_from_vault()
    assert "cred1" in store._cache

@pytest.mark.asyncio
@patch("backend.services.vault", new_callable=AsyncMock)
async def test_load_from_vault_exception(mock_vault, store):
    mock_vault.retrieve_secret.side_effect = Exception("error")
    await store.load_from_vault()
    assert store._cache == {}

@pytest.mark.asyncio
@patch("backend.services.vault", new_callable=AsyncMock)
async def test_persist_success(mock_vault, store):
    store._cache = {"cred1": {"id": "1"}}
    await store._persist()
    mock_vault.store_secret.assert_called_once_with("webauthn_credentials", store._cache)

@pytest.mark.asyncio
@patch("backend.services.vault", new_callable=AsyncMock)
async def test_persist_exception(mock_vault, store):
    mock_vault.store_secret.side_effect = Exception("error")
    store._cache = {"cred1": {"id": "1"}}
    await store._persist() # Should not raise
    mock_vault.store_secret.assert_called_once()

@pytest.mark.asyncio
@patch("backend.services.vault", new_callable=AsyncMock)
async def test_store_credential(mock_vault, store):
    await store.store_credential("cred_id", b"public_key_bytes", 1)
    assert "cred_id" in store._cache
    assert store._cache["cred_id"]["public_key"] == b"public_key_bytes".hex()
    assert store._cache["cred_id"]["sign_count"] == 1
    mock_vault.store_secret.assert_called_once()

@pytest.mark.asyncio
@patch.object(CredentialStore, "load_from_vault")
async def test_get_credential_load_cache(mock_load, store):
    # Cache is empty, should trigger load_from_vault
    async def mock_load_func():
        store._cache = {"cred_id": {"credential_id": "cred_id", "public_key": b"pk".hex()}}
    mock_load.side_effect = mock_load_func
    
    res = await store.get_credential("cred_id")
    assert res is not None
    assert res["public_key"] == b"pk"
    mock_load.assert_called_once()

@pytest.mark.asyncio
async def test_get_credential_not_found(store):
    store._cache = {"other": {}}
    res = await store.get_credential("cred_id")
    assert res is None

@pytest.mark.asyncio
@patch("backend.services.vault", new_callable=AsyncMock)
async def test_update_sign_count(mock_vault, store):
    store._cache = {"cred_id": {"sign_count": 1}}
    await store.update_sign_count("cred_id", 5)
    assert store._cache["cred_id"]["sign_count"] == 5
    mock_vault.store_secret.assert_called_once()

@pytest.mark.asyncio
async def test_update_sign_count_not_found(store):
    store._cache = {"other": {}}
    await store.update_sign_count("cred_id", 5)
    assert "cred_id" not in store._cache

@pytest.mark.asyncio
@patch.object(CredentialStore, "load_from_vault")
async def test_list_credentials(mock_load, store):
    async def mock_load_func():
        store._cache = {"cred1": {}, "cred2": {}}
    mock_load.side_effect = mock_load_func
    
    res = await store.list_credentials()
    assert set(res) == {"cred1", "cred2"}
    mock_load.assert_called_once()

@pytest.mark.asyncio
async def test_list_credentials_cached(store):
    store._cache = {"cred1": {}}
    res = await store.list_credentials()
    assert res == ["cred1"]
