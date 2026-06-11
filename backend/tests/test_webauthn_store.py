import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock
import base64
from backend.security.webauthn_store import WebAuthnChallengeStore

@pytest.fixture
def memory_store():
    return WebAuthnChallengeStore()

@pytest.fixture
def redis_store():
    redis_mock = AsyncMock()
    return WebAuthnChallengeStore(redis_client=redis_mock)

@pytest.mark.asyncio
async def test_create_challenge_memory(memory_store):
    c_id, c_b64 = await memory_store.create_challenge()
    assert c_id in memory_store._local
    assert len(c_id) > 0
    assert len(c_b64) > 0

@pytest.mark.asyncio
async def test_consume_challenge_memory(memory_store):
    c_id, _ = await memory_store.create_challenge()
    raw = await memory_store.consume_challenge(c_id)
    assert raw is not None
    # Verify consumed
    raw_again = await memory_store.consume_challenge(c_id)
    assert raw_again is None

@pytest.mark.asyncio
async def test_create_challenge_redis(redis_store):
    c_id, c_b64 = await redis_store.create_challenge()
    redis_store._redis.setex.assert_called_once()
    args = redis_store._redis.setex.call_args[0]
    assert args[0] == f"webauthn:challenge:{c_id}"
    assert args[1] == 120 # CHALLENGE_TTL_SECONDS
    assert isinstance(args[2], bytes)

@pytest.mark.asyncio
async def test_consume_challenge_redis_found(redis_store):
    c_id = "test_id"
    redis_store._redis.get.return_value = b"raw_data"
    raw = await redis_store.consume_challenge(c_id)
    assert raw == b"raw_data"
    redis_store._redis.get.assert_called_once_with(f"webauthn:challenge:{c_id}")
    redis_store._redis.delete.assert_called_once_with(f"webauthn:challenge:{c_id}")

@pytest.mark.asyncio
async def test_consume_challenge_redis_not_found(redis_store):
    c_id = "test_id"
    redis_store._redis.get.return_value = None
    raw = await redis_store.consume_challenge(c_id)
    assert raw is None
    redis_store._redis.get.assert_called_once_with(f"webauthn:challenge:{c_id}")
    redis_store._redis.delete.assert_not_called()
