import secrets
import time
import logging
import os
import json
import asyncio
from typing import Dict, Tuple, Any, Optional
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
        # Challenge ID -> Success Data (Verified Response)
        self.login_results: Dict[str, Any] = {}
        self.ttl = 300  # 5 minutes

    async def create_login_challenge(self, identity_hint: str = "") -> Dict[str, str]:
        """Generates a nonce and a challenge ID for the simple signature flow."""
        challenge_id = secrets.token_urlsafe(16)
        nonce = secrets.token_hex(32)
        timestamp = time.time()
        self.challenges[challenge_id] = (nonce, timestamp, identity_hint)
        self._cleanup()
        return {
            "challenge_id": challenge_id,
            "nonce": nonce,
            "timestamp": str(timestamp),
            "identity_hint": identity_hint
        }

    async def get_verusid_login_request(self, signing_id: str, redirect_uri: str) -> Dict[str, Any]:
        """Uses the TS bridge to create a formal VerusID LoginConsentRequest."""
        if not settings.VERUS_ID_PRIVATE_KEY:
            logger.error("VERUS_ID_PRIVATE_KEY (WIF) is missing in .env")
            raise Exception("CONFIGURATION_ERROR: VERUS_ID_PRIVATE_KEY is missing. Please add your identity WIF to .env")

        bridge_path = os.path.join(os.path.dirname(__file__), "..", "verusid_bridge", "bridge.ts")
        
        payload = {
            "signing_id": signing_id,
            "wif": settings.VERUS_ID_PRIVATE_KEY,
            "challenge_id": secrets.token_urlsafe(16),
            "redirect_uri": redirect_uri,
            "rpc_url": settings.VERUS_PUBLIC_RPC_URL,
            "rpc_user": settings.VERUS_RPC_USER,
            "rpc_pass": settings.VERUS_RPC_PASSWORD
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
                if "Request must be signed" in err_msg or "WIF" in err_msg:
                    raise Exception(f"VerusID Login Error: Identity private key (WIF) is invalid in .env")
                raise Exception(f"Bridge failed: {err_msg}")
                
            res = json.loads(stdout.decode())
            challenge_id = res.get("request", {}).get("challenge", {}).get("challenge_id")
            if challenge_id:
                self.challenges[challenge_id] = ("formal_ssid", time.time(), signing_id)
            
            return res
        except Exception as e:
            logger.error(f"Error calling VerusID bridge: {str(e)}")
            raise

    async def verify_login_response(self, response_data: Dict[str, Any]) -> bool:
        """Verifies the signed LoginConsentResponse using the TS bridge."""
        bridge_path = os.path.join(os.path.dirname(__file__), "..", "verusid_bridge", "bridge.ts")
        
        # The payload for verification
        verify_payload = {
            "response": response_data,
            "rpc_url": settings.VERUS_PUBLIC_RPC_URL,
            "rpc_user": settings.VERUS_RPC_USER,
            "rpc_pass": settings.VERUS_RPC_PASSWORD
        }
        
        try:
            cmd = ["npx", "tsx", bridge_path, "verify-response", json.dumps(verify_payload)]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.join(os.path.dirname(__file__), "..", "verusid_bridge")
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                err_msg = stderr.decode()
                logger.error(f"Verification bridge error: {err_msg}")
                return False
                
            result = json.loads(stdout.decode())
            if result.get("verified"):
                # Store the result for polling
                decision = result.get("decision", {})
                challenge_id = decision.get("challenge_id")
                if challenge_id:
                    self.login_results[challenge_id] = {
                        "identity": result.get("signing_id"),
                        "decision": decision,
                        "timestamp": time.time()
                    }
                return True
            return False
        except Exception as e:
            logger.error(f"Verification process internal error: {str(e)}")
            return False

    async def get_login_status(self, challenge_id: str) -> Optional[Dict[str, Any]]:
        """Checks if a login has been completed for the given challenge_id."""
        return self.login_results.get(challenge_id)

    def _cleanup(self):
        now = time.time()
        expired_challenges = [cid for cid, (_, ts, _) in self.challenges.items() if now - ts > self.ttl]
        for cid in expired_challenges:
            del self.challenges[cid]
            
        expired_results = [cid for cid, data in self.login_results.items() if now - data["timestamp"] > self.ttl]
        for cid in expired_results:
            del self.login_results[cid]

# Singleton instance
verus_auth = VerusIDAuth()
