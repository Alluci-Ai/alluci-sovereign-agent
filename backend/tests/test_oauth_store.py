import pytest
import json
from unittest.mock import AsyncMock
from backend.security.oauth_store import OAuthStateStore

@pytest.fixture
def memory_store():
    return OAuthStateStore()

@pytest.fixture
def redis_store():
    redis_mock = AsyncMock()
    return OAuthStateStore(redis_client=redis_mock)

@pytest.mark.asyncio
async def test_store_state_memory(memory_store):
    await memory_store.store_state("test_state", {"data": "value"})
    assert "test_state" in memory_store._local
    assert memory_store._local["test_state"] == {"data": "value"}

@pytest.mark.asyncio
async def test_consume_state_memory(memory_store):
    await memory_store.store_state("test_state", {"data": "value"})
    data = await memory_store.consume_state("test_state")
    assert data == {"data": "value"}
    # Verify consumed
    data_again = await memory_store.consume_state("test_state")
    assert data_again is None

@pytest.mark.asyncio
async def test_store_state_redis(redis_store):
    await redis_store.store_state("test_state", {"data": "value"})
    redis_store._redis.setex.assert_called_once()
    args = redis_store._redis.setex.call_args[0]
    assert args[0] == "oauth:state:test_state"
    assert args[1] == 600
    assert args[2] == json.dumps({"data": "value"})

@pytest.mark.asyncio
async def test_consume_state_redis_found(redis_store):
    redis_store._redis.get.return_value = json.dumps({"data": "value"}).encode()
    data = await redis_store.consume_state("test_state")
    assert data == {"data": "value"}
    redis_store._redis.get.assert_called_once_with("oauth:state:test_state")
    redis_store._redis.delete.assert_called_once_with("oauth:state:test_state")

@pytest.mark.asyncio
async def test_consume_state_redis_not_found(redis_store):
    redis_store._redis.get.return_value = None
    data = await redis_store.consume_state("test_state")
    assert data is None
    redis_store._redis.get.assert_called_once_with("oauth:state:test_state")
    redis_store._redis.delete.assert_not_called()

@pytest.mark.asyncio
async def test_consume_state_redis_invalid_json(redis_store):
    redis_store._redis.get.return_value = b"invalid json"
    data = await redis_store.consume_state("test_state")
    assert data == "invalid json"
    redis_store._redis.delete.assert_called_once()
