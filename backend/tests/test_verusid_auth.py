import pytest
pytestmark = pytest.mark.unit

import json
import time
from unittest.mock import AsyncMock, patch, MagicMock
from backend.security.verusid_auth import VerusIDAuth
from backend.config import settings

@pytest.fixture
def auth_no_redis():
    return VerusIDAuth()

@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    return redis

@pytest.fixture
def auth_with_redis(mock_redis):
    return VerusIDAuth(redis_client=mock_redis)

@pytest.mark.asyncio
async def test_create_login_challenge_no_redis(auth_no_redis):
    res = await auth_no_redis.create_login_challenge("hint123")
    assert "challenge_id" in res
    assert "nonce" in res
    assert "timestamp" in res
    assert res["identity_hint"] == "hint123"
    assert res["challenge_id"] in auth_no_redis.challenges

@pytest.mark.asyncio
async def test_create_login_challenge_with_redis(auth_with_redis, mock_redis):
    res = await auth_with_redis.create_login_challenge("hint123")
    assert "challenge_id" in res
    assert "nonce" in res
    mock_redis.setex.assert_called_once()
    args, kwargs = mock_redis.setex.call_args
    assert args[0] == f"verus:challenge:{res['challenge_id']}"

@pytest.mark.asyncio
async def test_get_verusid_login_request_missing_wif(auth_no_redis):
    with patch("backend.security.verusid_auth.settings.VERUS_ID_PRIVATE_KEY", None):
        with pytest.raises(Exception, match="CONFIGURATION_ERROR"):
            await auth_no_redis.get_verusid_login_request("alice@", "http://localhost")

@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_get_verusid_login_request_success_no_redis(mock_exec, auth_no_redis):
    with patch("backend.security.verusid_auth.settings.VERUS_ID_PRIVATE_KEY", "dummy_wif"):
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (json.dumps({"challenge_id": "c123", "data": "req"}).encode(), b"")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process
        
        res = await auth_no_redis.get_verusid_login_request("alice@", "http://localhost")
        assert res["challenge_id"] == "c123"
        assert "c123" in auth_no_redis.challenges

@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_get_verusid_login_request_success_with_redis(mock_exec, auth_with_redis, mock_redis):
    with patch("backend.security.verusid_auth.settings.VERUS_ID_PRIVATE_KEY", "dummy_wif"):
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (json.dumps({"challenge_id": "c123", "data": "req"}).encode(), b"")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process
        
        res = await auth_with_redis.get_verusid_login_request("alice@", "http://localhost")
        assert res["challenge_id"] == "c123"
        mock_redis.setex.assert_called_once()

@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_get_verusid_login_request_process_error(mock_exec, auth_no_redis):
    with patch("backend.security.verusid_auth.settings.VERUS_ID_PRIVATE_KEY", "dummy_wif"):
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"WIF invalid")
        mock_process.returncode = 1
        mock_exec.return_value = mock_process
        
        with pytest.raises(Exception, match="invalid in .env"):
            await auth_no_redis.get_verusid_login_request("alice@", "http://localhost")

        mock_process.communicate.return_value = (b"", b"Other error")
        with pytest.raises(Exception, match="Bridge failed"):
            await auth_no_redis.get_verusid_login_request("alice@", "http://localhost")

@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_get_verusid_login_request_process_exception(mock_exec, auth_no_redis):
    with patch("backend.security.verusid_auth.settings.VERUS_ID_PRIVATE_KEY", "dummy_wif"):
        mock_exec.side_effect = Exception("Spawn failed")
        with pytest.raises(Exception, match="Spawn failed"):
            await auth_no_redis.get_verusid_login_request("alice@", "http://localhost")

@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_verify_login_response_success_no_redis(mock_exec, auth_no_redis):
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (json.dumps({"verified": True, "signing_id": "alice@", "decision": {"challenge_id": "c123"}}).encode(), b"")
    mock_process.returncode = 0
    mock_exec.return_value = mock_process
    
    res = await auth_no_redis.verify_login_response({"res": "data"})
    assert res is True
    assert "c123" in auth_no_redis.login_results
    assert auth_no_redis.login_results["c123"]["identity"] == "alice@"

@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_verify_login_response_success_with_redis(mock_exec, auth_with_redis, mock_redis):
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (json.dumps({"verified": True, "signing_id": "alice@", "decision": {"challenge_id": "c123"}}).encode(), b"")
    mock_process.returncode = 0
    mock_exec.return_value = mock_process
    
    res = await auth_with_redis.verify_login_response({"res": "data"})
    assert res is True
    mock_redis.setex.assert_called_once()

@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_verify_login_response_not_verified(mock_exec, auth_no_redis):
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (json.dumps({"verified": False}).encode(), b"")
    mock_process.returncode = 0
    mock_exec.return_value = mock_process
    
    res = await auth_no_redis.verify_login_response({"res": "data"})
    assert res is False

@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_verify_login_response_process_error(mock_exec, auth_no_redis):
    mock_process = AsyncMock()
    mock_process.communicate.return_value = (b"", b"bridge error")
    mock_process.returncode = 1
    mock_exec.return_value = mock_process
    
    res = await auth_no_redis.verify_login_response({"res": "data"})
    assert res is False

@pytest.mark.asyncio
@patch("asyncio.create_subprocess_exec")
async def test_verify_login_response_exception(mock_exec, auth_no_redis):
    mock_exec.side_effect = Exception("Spawn fail")
    res = await auth_no_redis.verify_login_response({"res": "data"})
    assert res is False

@pytest.mark.asyncio
async def test_get_login_status_no_redis(auth_no_redis):
    auth_no_redis.login_results["c123"] = {"status": "ok"}
    res = await auth_no_redis.get_login_status("c123")
    assert res == {"status": "ok"}
    res2 = await auth_no_redis.get_login_status("invalid")
    assert res2 is None

@pytest.mark.asyncio
async def test_get_login_status_with_redis(auth_with_redis, mock_redis):
    mock_redis.get.return_value = json.dumps({"status": "ok"}).encode()
    res = await auth_with_redis.get_login_status("c123")
    assert res == {"status": "ok"}
    mock_redis.get.assert_called_with("verus:result:c123")
    
    mock_redis.get.return_value = None
    res2 = await auth_with_redis.get_login_status("invalid")
    assert res2 is None

def test_cleanup(auth_no_redis):
    now = time.time()
    auth_no_redis.challenges["c1"] = ("nonce", now, "hint")
    auth_no_redis.challenges["c2"] = ("nonce", now - 400, "hint")
    auth_no_redis.login_results["c3"] = {"timestamp": now}
    auth_no_redis.login_results["c4"] = {"timestamp": now - 400}
    
    auth_no_redis._cleanup()
    
    assert "c1" in auth_no_redis.challenges
    assert "c2" not in auth_no_redis.challenges
    assert "c3" in auth_no_redis.login_results
    assert "c4" not in auth_no_redis.login_results
