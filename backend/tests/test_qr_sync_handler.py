import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
from backend.security.qr_sync_handler import QRSyncHandler

@pytest.fixture
def mock_vault():
    return AsyncMock()

@pytest.fixture
def mock_redis():
    return AsyncMock()

@pytest.fixture
def handler_memory(mock_vault):
    return QRSyncHandler(vault=mock_vault)

@pytest.fixture
def handler_redis(mock_vault, mock_redis):
    return QRSyncHandler(vault=mock_vault, redis_client=mock_redis)

@pytest.mark.asyncio
async def test_create_sync_challenge_memory(handler_memory):
    sync_id = await handler_memory.create_sync_challenge()
    assert sync_id in handler_memory._active_sessions
    assert isinstance(sync_id, str)

@pytest.mark.asyncio
async def test_create_sync_challenge_redis(handler_redis):
    sync_id = await handler_redis.create_sync_challenge()
    handler_redis.redis_client.setex.assert_called_once()
    assert sync_id not in handler_redis._active_sessions

@pytest.mark.asyncio
async def test_create_sync_challenge_redis_exception(handler_redis):
    handler_redis.redis_client.setex.side_effect = Exception("error")
    sync_id = await handler_redis.create_sync_challenge()
    # Fallbacks to memory
    assert sync_id in handler_redis._active_sessions

@pytest.mark.asyncio
async def test_complete_sync_memory_success(handler_memory):
    sync_id = await handler_memory.create_sync_challenge()
    res = await handler_memory.complete_sync("bridge", "acc", sync_id, {"key": "val"})
    assert res is True
    handler_memory.vault.store_connection_secret.assert_called_once_with("bridge", "acc", {"key": "val"})
    assert sync_id not in handler_memory._active_sessions

@pytest.mark.asyncio
async def test_complete_sync_redis_success(handler_redis):
    sync_id = "test_sync_id"
    handler_redis.redis_client.get.return_value = str(time.time()).encode()
    res = await handler_redis.complete_sync("bridge", "acc", sync_id, {"key": "val"})
    assert res is True
    handler_redis.vault.store_connection_secret.assert_called_once()
    handler_redis.redis_client.delete.assert_called_once_with(f"qr_sync:{sync_id}")

@pytest.mark.asyncio
async def test_complete_sync_redis_exception_fallback(handler_redis):
    sync_id = await handler_redis.create_sync_challenge()
    # Manually add to memory fallback for this test
    handler_redis._active_sessions[sync_id] = time.time()
    
    handler_redis.redis_client.get.side_effect = Exception("error")
    res = await handler_redis.complete_sync("bridge", "acc", sync_id, {"key": "val"})
    
    assert res is True
    handler_redis.vault.store_connection_secret.assert_called_once()

@pytest.mark.asyncio
async def test_complete_sync_invalid_id(handler_memory):
    res = await handler_memory.complete_sync("bridge", "acc", "bad_id", {"key": "val"})
    assert res is False

@pytest.mark.asyncio
async def test_complete_sync_expired_memory(handler_memory):
    sync_id = await handler_memory.create_sync_challenge()
    handler_memory._active_sessions[sync_id] = time.time() - 400 # 400s ago, ttl is 300
    res = await handler_memory.complete_sync("bridge", "acc", sync_id, {"key": "val"})
    assert res is False
    assert sync_id not in handler_memory._active_sessions

@pytest.mark.asyncio
async def test_complete_sync_expired_redis(handler_redis):
    sync_id = "test_id"
    handler_redis.redis_client.get.return_value = str(time.time() - 400)
    res = await handler_redis.complete_sync("bridge", "acc", sync_id, {"key": "val"})
    assert res is False
    handler_redis.redis_client.delete.assert_called_once_with(f"qr_sync:{sync_id}")

@pytest.mark.asyncio
async def test_complete_sync_vault_exception(handler_memory):
    sync_id = await handler_memory.create_sync_challenge()
    handler_memory.vault.store_connection_secret.side_effect = Exception("vault error")
    res = await handler_memory.complete_sync("bridge", "acc", sync_id, {"key": "val"})
    assert res is False
    # Not cleaned up on failure
    assert sync_id in handler_memory._active_sessions

def test_cleanup_expired(handler_memory):
    handler_memory._active_sessions["active"] = time.time()
    handler_memory._active_sessions["expired"] = time.time() - 400
    handler_memory.cleanup_expired()
    assert "active" in handler_memory._active_sessions
    assert "expired" not in handler_memory._active_sessions
