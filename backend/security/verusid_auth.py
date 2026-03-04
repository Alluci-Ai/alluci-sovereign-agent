
import secrets
import time
import logging
from typing import Dict, Tuple
from backend.security.verus_rpc import verus_rpc

logger = logging.getLogger("VerusIDAuth")

class VerusIDAuth:
    """
    Handles VerusID SSID authentication (Challenge-Response).
    """
    def __init__(self):
        # In-memory storage for pending challenges
        # Challenge ID -> (nonce, timestamp, identity_hint)
        self.challenges: Dict[str, Tuple[str, float, str]] = {}
        self.ttl = 300  # 5 minutes

    def create_login_challenge(self, identity_hint: str = "") -> Dict[str, str]:
        """
        Generates a nonce and a challenge ID for the frontend/mobile.
        """
        challenge_id = secrets.token_urlsafe(16)
        nonce = secrets.token_hex(32)
        timestamp = time.time()
        
        self.challenges[challenge_id] = (nonce, timestamp, identity_hint)
        
        # Cleanup expired challenges logic (usually triggered on new creations)
        self._cleanup()
        
        return {
            "challenge_id": challenge_id,
            "nonce": nonce,
            "timestamp": str(timestamp),
            "identity_hint": identity_hint
        }

    async def verify_login_response(self, identity: str, signature: str, challenge_id: str) -> bool:
        """
        Verifies the signed challenge using the Verus verifymessage RPC.
        """
        if challenge_id not in self.challenges:
            logger.error(f"Auth failed: Challenge ID {challenge_id} not found or expired.")
            return False
        
        nonce, timestamp, _ = self.challenges[challenge_id]
        
        # Ensure challenge hasn't expired
        if time.time() - timestamp > self.ttl:
            logger.error(f"Auth failed: Challenge ID {challenge_id} expired.")
            del self.challenges[challenge_id]
            return False
        
        # The message to verify is typically the nonce
        try:
            is_valid = await verus_rpc.verify_message(identity, signature, nonce)
            if is_valid:
                logger.info(f"Identity {identity} authenticated successfully via VerusID.")
                # Consume the challenge
                del self.challenges[challenge_id]
                return True
            else:
                logger.warning(f"Signature verification failed for identity {identity}.")
                return False
        except Exception as e:
            logger.error(f"VerusID verification RPC failed: {str(e)}")
            return False

    def _cleanup(self):
        now = time.time()
        expired = [cid for cid, (_, ts, _) in self.challenges.items() if now - ts > self.ttl]
        for cid in expired:
            del self.challenges[cid]

# Singleton instance
verus_auth = VerusIDAuth()
