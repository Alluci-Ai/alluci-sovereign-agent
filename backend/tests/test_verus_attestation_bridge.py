import pytest
pytestmark = pytest.mark.unit

import json
from unittest.mock import AsyncMock, patch

from backend.security.verus_attestation_bridge import VerusAttestationBridge

@pytest.fixture
def bridge():
    vault_manager = AsyncMock()
    return VerusAttestationBridge(vault_manager)

@pytest.mark.asyncio
async def test_extract_lite_mode_credentials_success(bridge):
    bridge.vault_manager.retrieve_secret.side_effect = ["google_val", "signal_val"]
    creds = await bridge._extract_lite_mode_credentials()
    assert creds == {"google_drive_oauth": "google_val", "signal_jwt": "signal_val"}

@pytest.mark.asyncio
async def test_extract_lite_mode_credentials_exception(bridge):
    bridge.vault_manager.retrieve_secret.side_effect = Exception("vault error")
    creds = await bridge._extract_lite_mode_credentials()
    assert creds == {}

@pytest.mark.asyncio
@patch("backend.security.verus_rpc.verus_rpc.sign_message", new_callable=AsyncMock)
async def test_generate_zk_attestations_success(mock_sign, bridge):
    bridge.verus_id = "test@id"
    mock_sign.return_value = "mock_signature"
    creds = {"google_drive_oauth": "val1", "signal_jwt": "val2", "empty_one": "empty"}
    
    attests = await bridge._generate_zk_attestations(creds)
    assert len(attests) == 2
    assert attests["google_drive_oauth"]["signature"] == "mock_signature"
    assert attests["signal_jwt"]["signature"] == "mock_signature"
    assert mock_sign.call_count == 2

@pytest.mark.asyncio
async def test_generate_zk_attestations_no_id(bridge):
    bridge.verus_id = None
    with pytest.raises(ValueError):
        await bridge._generate_zk_attestations({"k": "v"})

@pytest.mark.asyncio
@patch("backend.security.verus_rpc.verus_rpc.sign_message", new_callable=AsyncMock)
async def test_generate_zk_attestations_rpc_error(mock_sign, bridge):
    bridge.verus_id = "test@id"
    mock_sign.side_effect = Exception("sign error")
    attests = await bridge._generate_zk_attestations({"k": "v"})
    assert len(attests) == 0

@pytest.mark.asyncio
@patch("backend.security.verus_rpc.verus_rpc.update_identity", new_callable=AsyncMock)
async def test_bind_to_verus_id_success(mock_update, bridge):
    mock_update.return_value = "txid"
    res = await bridge._bind_to_verus_id("test@id", {"k": "v"})
    assert res is True
    mock_update.assert_called_once()
    args, _ = mock_update.call_args
    assert "alluci.attestations.v1@" in args[0]["contentmultimap"]

@pytest.mark.asyncio
async def test_bind_to_verus_id_empty(bridge):
    res = await bridge._bind_to_verus_id("test@id", {})
    assert res is True

@pytest.mark.asyncio
@patch("backend.security.verus_rpc.verus_rpc.update_identity", new_callable=AsyncMock)
async def test_bind_to_verus_id_error(mock_update, bridge):
    mock_update.side_effect = Exception("update error")
    res = await bridge._bind_to_verus_id("test@id", {"k": "v"})
    assert res is False

@pytest.mark.asyncio
async def test_upgrade_to_sovereign_mode_success(bridge):
    with patch.object(bridge, "_extract_lite_mode_credentials", new_callable=AsyncMock) as mock_ext, \
         patch.object(bridge, "_generate_zk_attestations", new_callable=AsyncMock) as mock_gen, \
         patch.object(bridge, "_bind_to_verus_id", new_callable=AsyncMock) as mock_bind:
         
        mock_ext.return_value = {"k": "v"}
        mock_gen.return_value = {"k": {"sig": "sig"}}
        mock_bind.return_value = True
        
        res = await bridge.upgrade_to_sovereign_mode("test@id")
        assert res is True
        assert bridge.sovereign_mode_active is True
        assert bridge.verus_id == "test@id"

@pytest.mark.asyncio
async def test_upgrade_to_sovereign_mode_failure(bridge):
    with patch.object(bridge, "_extract_lite_mode_credentials", new_callable=AsyncMock) as mock_ext, \
         patch.object(bridge, "_generate_zk_attestations", new_callable=AsyncMock) as mock_gen, \
         patch.object(bridge, "_bind_to_verus_id", new_callable=AsyncMock) as mock_bind:
         
        mock_ext.return_value = {"k": "v"}
        mock_gen.return_value = {"k": {"sig": "sig"}}
        mock_bind.return_value = False
        
        res = await bridge.upgrade_to_sovereign_mode("test@id")
        assert res is False
        assert bridge.sovereign_mode_active is False

@pytest.mark.asyncio
async def test_upgrade_to_sovereign_mode_exception(bridge):
    with patch.object(bridge, "_extract_lite_mode_credentials", new_callable=AsyncMock) as mock_ext:
        mock_ext.side_effect = Exception("Extract error")
        res = await bridge.upgrade_to_sovereign_mode("test@id")
        assert res is False
