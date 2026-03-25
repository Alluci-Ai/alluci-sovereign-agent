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
    qr_data = await iwatch_bridge.generate_pairing_qr("http://localhost:8000")
    device_id = qr_data["device_id"]
    secret = qr_data["qr_payload"]["seed"]
    
    # Simulate step 2: User gets code from watch (using same secret)
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()
    
    # Submit code
    result = await iwatch_bridge.submit_pairing_code(valid_code, device_id=device_id)
    
    assert result["status"] == "SUCCESS"
    assert "session_token" in result
    assert iwatch_bridge.is_connected is True
    assert device_id not in iwatch_bridge._pending_seeds

@pytest.mark.asyncio
async def test_iwatch_bridge_pairing_failure(iwatch_bridge):
    # Simulate step 1
    qr_data = await iwatch_bridge.generate_pairing_qr("http://localhost:8000")
    device_id = qr_data["device_id"]
    
    # Submit wrong code
    result = await iwatch_bridge.submit_pairing_code("000000", device_id=device_id)
    
    assert result["status"] == "FAILED"
    assert "Invalid pairing code" in result["error"]
    assert device_id in iwatch_bridge._pending_seeds  # Keeps pending secret so user can try again

@pytest.mark.asyncio
async def test_iwatch_bridge_pairing_no_session(iwatch_bridge):
    # Submit code without calling pair/ first
    result = await iwatch_bridge.submit_pairing_code("123456", device_id="some-unknown-id")
    
    assert result["status"] == "FAILED"
    assert "No pending" in result["error"]
