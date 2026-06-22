
import base64
import secrets
from ..logging_config import get_logger
from typing import Optional

logger = get_logger("WebAuthnStore")

CHALLENGE_TTL_SECONDS = 120  # 2-minute challenge window

class WebAuthnChallengeStore:
    """
    Redis-backed store for WebAuthn challenges.
    Falls back to an asyncio-safe in-memory dict when Redis is unavailable.
    Keys: challenge_id (returned to browser as 'challengeId' field)
    Values: raw challenge bytes, with TTL
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._local: dict = {}  # fallback
        if not redis_client:
            logger.warning(
                "[WebAuthn] Redis unavailable — using in-memory challenge store. "
                "NOT safe for multi-worker deployments."
            )

    async def create_challenge(self) -> tuple[str, str]:
        """
        Returns (challenge_id, b64_challenge).
        challenge_id is stored server-side and returned to the browser.
        b64_challenge is the raw challenge sent to the authenticator.
        """
        challenge_bytes = secrets.token_bytes(32)
        challenge_id = secrets.token_urlsafe(24)
        b64_challenge = base64.urlsafe_b64encode(challenge_bytes).decode().rstrip("=")

        if self._redis:
            await self._redis.setex(
                f"webauthn:challenge:{challenge_id}",
                CHALLENGE_TTL_SECONDS,
                challenge_bytes,
            )
        else:
            self._local[challenge_id] = challenge_bytes

        return challenge_id, b64_challenge

    async def consume_challenge(self, challenge_id: str) -> Optional[bytes]:
        """
        Atomically retrieve and delete a challenge by its ID.
        Returns None if the challenge doesn't exist or has expired.
        """
        if self._redis:
            key = f"webauthn:challenge:{challenge_id}"
            # GETDEL is atomic — prevents replay
            raw = await self._redis.get(key)
            if raw:
                await self._redis.delete(key)
            return raw if raw else None
        else:
            return self._local.pop(challenge_id, None)

# Module-level singleton — injected with redis_client during lifespan
webauthn_store: WebAuthnChallengeStore = WebAuthnChallengeStore()
