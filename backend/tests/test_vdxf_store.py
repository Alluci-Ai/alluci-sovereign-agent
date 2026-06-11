import pytest
pytestmark = pytest.mark.unit

import asyncio
import time
from unittest.mock import patch, AsyncMock

from backend.security.vdxf_store import VDXFStore

@pytest.fixture
def store():
    return VDXFStore("test@")

@pytest.mark.asyncio
async def test_anchor_vault_hash_disabled(store):
    with patch("backend.security.vdxf_store.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = False
        res = await store.anchor_vault_hash("data")
        assert res is None

@pytest.mark.asyncio
@patch("backend.security.verus_rpc.verus_rpc.get_identity", new_callable=AsyncMock)
@patch("backend.security.verus_rpc.verus_rpc.update_identity", new_callable=AsyncMock)
async def test_anchor_vault_hash_success(mock_update, mock_get, store):
    with patch("backend.security.vdxf_store.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        
        mock_get.return_value = {"identity": {"contentmultimap": {}}}
        mock_update.return_value = "mock_txid"
        
        res = await store.anchor_vault_hash("vault_data")
        assert res == "mock_txid"
        
        # Verify call
        mock_update.assert_called_once()
        args, _ = mock_update.call_args
        identity = args[0]
        assert store.vdxf_manifest_key in identity["contentmultimap"]
        manifest = identity["contentmultimap"][store.vdxf_manifest_key][0]
        assert "keys_hash" in manifest
        
@pytest.mark.asyncio
@patch("backend.security.verus_rpc.verus_rpc.get_identity", new_callable=AsyncMock)
async def test_anchor_vault_hash_exception(mock_get, store):
    with patch("backend.security.vdxf_store.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        mock_get.side_effect = Exception("RPC failed")
        res = await store.anchor_vault_hash("data")
        assert res is None

@pytest.mark.asyncio
async def test_anchor_audit_batch_disabled(store):
    with patch("backend.security.vdxf_store.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = False
        res = await store.anchor_audit_batch("data")
        assert res is None

@pytest.mark.asyncio
@patch("backend.security.verus_rpc.verus_rpc.get_identity", new_callable=AsyncMock)
@patch("backend.security.verus_rpc.verus_rpc.update_identity", new_callable=AsyncMock)
async def test_anchor_audit_batch_success(mock_update, mock_get, store):
    with patch("backend.security.vdxf_store.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        
        # Test branch where contentmultimap does not exist yet
        mock_get.return_value = {"identity": {}}
        mock_update.return_value = "mock_txid_audit"
        
        res = await store.anchor_audit_batch("batch_data")
        assert res == "mock_txid_audit"
        
        args, _ = mock_update.call_args
        identity = args[0]
        assert "alluci.audit.ledger@" in identity["contentmultimap"]

@pytest.mark.asyncio
@patch("backend.security.verus_rpc.verus_rpc.get_identity", new_callable=AsyncMock)
async def test_anchor_audit_batch_exception(mock_get, store):
    with patch("backend.security.vdxf_store.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        mock_get.side_effect = Exception("RPC error")
        res = await store.anchor_audit_batch("batch_data")
        assert res is None

@pytest.mark.asyncio
async def test_verify_integrity_disabled(store):
    with patch("backend.security.vdxf_store.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = False
        res = await store.verify_integrity("data")
        assert res is True

@pytest.mark.asyncio
@patch("backend.security.verus_rpc.verus_rpc.get_content_multimap", new_callable=AsyncMock)
async def test_verify_integrity_no_data(mock_get_content, store):
    with patch("backend.security.vdxf_store.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        mock_get_content.return_value = None
        res = await store.verify_integrity("data")
        assert res is True

@pytest.mark.asyncio
@patch("backend.security.verus_rpc.verus_rpc.get_content_multimap", new_callable=AsyncMock)
async def test_verify_integrity_match(mock_get_content, store):
    with patch("backend.security.vdxf_store.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        local_hash = store._get_hash("data")
        mock_get_content.return_value = [{"keys_hash": f"sha256:{local_hash}"}]
        
        res = await store.verify_integrity("data")
        assert res is True

@pytest.mark.asyncio
@patch("backend.security.verus_rpc.verus_rpc.get_content_multimap", new_callable=AsyncMock)
async def test_verify_integrity_mismatch(mock_get_content, store):
    with patch("backend.security.vdxf_store.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        mock_get_content.return_value = [{"keys_hash": "sha256:wrong_hash"}]
        
        res = await store.verify_integrity("data")
        assert res is False

@pytest.mark.asyncio
@patch("backend.security.verus_rpc.verus_rpc.get_content_multimap", new_callable=AsyncMock)
async def test_verify_integrity_exception(mock_get_content, store):
    with patch("backend.security.vdxf_store.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        mock_get_content.side_effect = Exception("RPC")
        res = await store.verify_integrity("data")
        assert res is False

def test_memory_cache(store):
    store.set_memory("key1", "val1")
    assert store.get_from_memory("key1") == "val1"
    assert store.get_from_memory("missing") is None
    
    # Test TTL expiry
    store.cache_expiry["key1"] = time.time() - 10 # expired
    assert store.get_from_memory("key1") is None
    assert "key1" not in store.memory_cache
