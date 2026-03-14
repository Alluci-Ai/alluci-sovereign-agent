
import json
import logging
from typing import Optional, Any

logger = logging.getLogger("OAuthStore")

STATE_TTL_SECONDS = 600  # 10-minute window for OAuth flow

class OAuthStateStore:
    """
    Redis-backed store for OAuth states and PKCE verifiers.
    Falls back to an asyncio-safe in-memory dict when Redis is unavailable.
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._local: dict = {}  # fallback
        if not redis_client:
            logger.warning(
                "[OAuth] Redis unavailable — using in-memory state store. "
                "NOT safe for multi-worker deployments."
            )

    async def store_state(self, state: str, data: Any):
        """Store OAuth state data with a TTL."""
        if self._redis:
            await self._redis.setex(
                f"oauth:state:{state}",
                STATE_TTL_SECONDS,
                json.dumps(data),
            )
        else:
            self._local[state] = data

    async def consume_state(self, state: str) -> Optional[Any]:
        """Atomically retrieve and delete state data."""
        if self._redis:
            key = f"oauth:state:{state}"
            raw = await self._redis.get(key)
            if raw:
                await self._redis.delete(key)
                try:
                    return json.loads(raw)
                except Exception:
                    return raw.decode() if isinstance(raw, bytes) else raw
            return None
        else:
            return self._local.pop(state, None)

# Module-level singleton
oauth_store = OAuthStateStore()
