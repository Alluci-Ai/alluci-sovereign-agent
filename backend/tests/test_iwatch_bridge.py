from backend.bridges.iwatch import IWatchBridge
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def iwatch_bridge():
    bridge = IWatchBridge(bridge_id="iwatch", vault_root="/tmp/vaults")
    bridge.logger = MagicMock()
    return bridge

@pytest.mark.asyncio
async def test_iwatch_bridge_connect(iwatch_bridge):
    assert not iwatch_bridge.is_connected
    # Connect with loaded secret
    result = await iwatch_bridge.connect({"totp_secret": "JBSWY3DPEHPK3PXP"})
    assert result is True
    assert iwatch_bridge.is_connected
    
@pytest.mark.asyncio
async def test_iwatch_bridge_pairing_success(iwatch_bridge):
    import pyotp
    # Simulate step 1: API generates pending secret
    secret = pyotp.random_base32()
    iwatch_bridge.pending_totp_secret = secret
    
    # Simulate step 2: User gets code from watch (using same secret)
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()
    
    # Submit code
    result = await iwatch_bridge.submit_pairing_code(valid_code)
    
    assert result["status"] == "SUCCESS"
    assert result["paired"] is True
    assert result["credentials"]["totp_secret"] == secret
    assert iwatch_bridge.is_connected is True
    assert iwatch_bridge.pending_totp_secret is None

@pytest.mark.asyncio
async def test_iwatch_bridge_pairing_failure(iwatch_bridge):
    import pyotp
    secret = pyotp.random_base32()
    iwatch_bridge.pending_totp_secret = secret
    
    # Submit wrong code
    result = await iwatch_bridge.submit_pairing_code("000000")
    
    assert result["status"] == "FAILED"
    assert iwatch_bridge.is_connected is False
    assert iwatch_bridge.pending_totp_secret == secret  # Keeps pending secret so user can try again

@pytest.mark.asyncio
async def test_iwatch_bridge_pairing_no_session(iwatch_bridge):
    # Submit code without calling pair/ first
    result = await iwatch_bridge.submit_pairing_code("123456")
    
    assert result["status"] == "FAILED"
    assert "No pending" in result["error"]
