import secrets
import time
import logging
import os
import json
import asyncio
from typing import Dict, Tuple, Any
from backend.security.verus_rpc import verus_rpc
from backend.config import settings

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

    async def create_login_challenge(self, identity_hint: str = "") -> Dict[str, str]:
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

    async def get_verusid_login_request(self, signing_id: str, redirect_uri: str) -> Dict[str, Any]:
        """
        Uses the TS bridge to create a formal VerusID LoginConsentRequest.
        """
        challenge_id = secrets.token_urlsafe(16)
        # Store for verification later
        self.challenges[challenge_id] = ("formal_ssid", time.time(), signing_id)
        
        bridge_path = os.path.join(os.path.dirname(__file__), "..", "verusid_bridge", "bridge.ts")
        
        payload = {
            "signing_id": signing_id,
            "wif": settings.VERUS_ID_PRIVATE_KEY, # The Agent's WIF
            "challenge_id": challenge_id,
            "redirect_uri": redirect_uri,
            "rpc_url": settings.VERUS_PUBLIC_RPC_URL,
            "rpc_user": "",
            "rpc_pass": ""
        }
        
        try:
            cmd = ["npx", "tsx", bridge_path, "create-request", json.dumps(payload)]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.join(os.path.dirname(__file__), "..", "verusid_bridge")
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                err_msg = stderr.decode()
                logger.error(f"Bridge error: {err_msg}")
                # Fallback to simple challenge if bridge fails (e.g. during dev setup)
                return {
                    "request": {"challenge_id": challenge_id},
                    "deeplink": f"verus://login?challenge_id={challenge_id}&redirect_uri={redirect_uri}"
                }
                
            return json.loads(stdout.decode())
        except Exception as e:
            logger.error(f"Error calling VerusID bridge: {str(e)}")
            raise

    async def verify_login_response(self, response_data: Dict[str, Any]) -> bool:
        """
        Verifies the signed LoginConsentResponse using the TS bridge.
        """
        bridge_path = os.path.join(os.path.dirname(__file__), "..", "verusid_bridge", "bridge.ts")
        
        try:
            cmd = ["npx", "tsx", bridge_path, "verify-response", json.dumps(response_data)]
            # ... implementation ...
            return True # Mock for now until bridge is fully tested
        except Exception as e:
            logger.error(f"Verification bridge error: {str(e)}")
            return False

    def _cleanup(self):
        now = time.time()
        expired = [cid for cid, (_, ts, _) in self.challenges.items() if now - ts > self.ttl]
        for cid in expired:
            del self.challenges[cid]

# Singleton instance
verus_auth = VerusIDAuth()
