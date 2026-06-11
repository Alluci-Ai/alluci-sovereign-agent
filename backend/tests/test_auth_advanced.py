import pytest
pytestmark = pytest.mark.unit

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from backend.security.webauthn_store import WebAuthnChallengeStore
from backend.security.oauth_store import OAuthStateStore
from backend.security.verusid_auth import VerusIDAuth

@pytest.mark.asyncio
class TestWebAuthnStore:
    async def test_create_and_consume_challenge_memory(self):
        """WebAuthn challenge should be created and consumed once (in-memory)."""
        store = WebAuthnChallengeStore(redis_client=None)
        cid, b64 = await store.create_challenge()
        assert cid in store._local
        
        # First consumption succeeds
        challenge = await store.consume_challenge(cid)
        assert challenge is not None
        assert cid not in store._local
        
        # Second consumption fails (replay protection)
        challenge2 = await store.consume_challenge(cid)
        assert challenge2 is None

    async def test_consume_nonexistent_challenge(self):
        """Consuming a challenge that doesn't exist returns None."""
        store = WebAuthnChallengeStore(redis_client=None)
        challenge = await store.consume_challenge("fake-cid")
        assert challenge is None

    async def test_redis_atomic_consume(self):
        """Ensure Redis-backed store uses atomic GET/DELETE (via mock)."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = b"test-challenge"
        store = WebAuthnChallengeStore(redis_client=mock_redis)
        
        challenge = await store.consume_challenge("test-id")
        assert challenge == b"test-challenge"
        mock_redis.delete.assert_called_once_with("webauthn:challenge:test-id")

@pytest.mark.asyncio
class TestOAuthStore:
    async def test_oauth_state_replay_prevention(self):
        """OAuth state should be consumable exactly once."""
        store = OAuthStateStore(redis_client=None)
        state = "test-state-123"
        data = {"provider": "slack", "verifier": "xyz"}
        
        await store.store_state(state, data)
        
        # First consume
        result = await store.consume_state(state)
        assert result == data
        
        # Replay attempt
        result2 = await store.consume_state(state)
        assert result2 is None

@pytest.mark.asyncio
class TestVerusIDAuth:
    async def test_verusid_challenge_creation(self):
        """VerusID challenges are unique and stored correctly."""
        auth = VerusIDAuth(redis_client=None)
        challenge = await auth.create_login_challenge(identity_hint="user@")
        cid = challenge["challenge_id"]
        
        assert cid in auth.challenges
        assert auth.challenges[cid][2] == "user@"
        
        # Cleanup test
        auth.ttl = -1 # Force expiry
        auth._cleanup()
        assert cid not in auth.challenges

    async def test_verusid_verification_failure_branch(self):
        """Ensure verify_login_response handles bridge failures gracefully."""
        auth = VerusIDAuth(redis_client=None)
        
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 1 # Failure
            mock_process.communicate.return_value = (b"", b"Bridge crashed")
            mock_exec.return_value = mock_process
            
            result = await auth.verify_login_response({"some": "data"})
            assert result is False

    async def test_verusid_verification_success_branch(self):
        """Ensure successful verification stores result correctly."""
        auth = VerusIDAuth(redis_client=None)
        mock_response = {
            "verified": True,
            "signing_id": "alluci@",
            "decision": {"challenge_id": "test-cid", "subject": "alluci@"}
        }
        
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = AsyncMock()
            mock_process.returncode = 0
            mock_process.communicate.return_value = (json.dumps(mock_response).encode(), b"")
            mock_exec.return_value = mock_process
            
            result = await auth.verify_login_response({"test": "payload"})
            assert result is True
            
            # Check if stored for polling
            status = await auth.get_login_status("test-cid")
            assert status["identity"] == "alluci@"  # type: ignore

class TestAuthIntegrationAdvanced:
    def test_webauthn_verify_invalid_challenge(self, app_client):
        """API: /auth/webauthn/verify should fail if challenge is missing or consumed."""
        payload = {
            "challengeId": "invalid-cid",
            "id": "abc",
            "rawId": "abc",
            "response": {
                "attestationObject": "fake",
                "clientDataJSON": "fake"
            }
        }
        response = app_client.post("/api/v1/auth/webauthn/verify", json=payload)
        assert response.status_code == 400
        assert "Challenge not found or expired" in response.text
