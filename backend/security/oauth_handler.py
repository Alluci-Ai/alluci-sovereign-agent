import secrets
import hashlib
import base64
import httpx
import logging
from typing import Dict, Any, Optional
from backend.security.vault import VaultManager

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger("OAuthHandler")

class OAuthHandler:
    """
    Standardizes OAuth 2.0 and PKCE flows for Alluci Sovereign bridges.
    Handles code exchange, state verification, and token rotation.
    """
    def __init__(self, vault: VaultManager):
        self.vault = vault
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Clean up resources."""
        await self.client.aclose()

    @staticmethod
    def generate_pkce_pair():
        """Generates code_verifier and code_challenge for PKCE."""
        verifier = secrets.token_urlsafe(32)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().replace('=', '')
        return verifier, challenge

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.ProtocolError)),
        reraise=True
    )
    async def exchange_code(self, 
                            bridge_id: str, 
                            account_id: str, 
                            token_url: str, 
                            client_id: str, 
                            client_secret: Optional[str], 
                            code: str, 
                            redirect_uri: str, 
                            code_verifier: Optional[str] = None) -> Dict[str, Any]:
        """
        Exchanges an authorization code for an access token.
        Supports both standard OAuth 2.0 and PKCE.
        """
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id
        }
        
        if client_secret:
            payload["client_secret"] = client_secret
        
        if code_verifier:
            payload["code_verifier"] = code_verifier

        try:
            response = await self.client.post(token_url, data=payload)
            response.raise_for_status()
            token_data = response.json()
            
            # Vault the resulting tokens (Hybrid Encryption)
            await self.vault.store_connection_secret(bridge_id, account_id, token_data)
            logger.info(f"OAuth exchange successful for {bridge_id}:{account_id}")
            return token_data
            
        except httpx.HTTPStatusError as e:
            logger.error(f"OAuth exchange failed for {bridge_id}: {e.response.text}")
            return {"error": "exchange_failed", "details": e.response.text}
        except Exception as e:
            logger.error(f"Unexpected error in OAuth exchange: {e}")
            return {"error": "internal_error", "details": str(e)}

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.ProtocolError)),
        reraise=True
    )
    async def refresh_token(self, 
                            bridge_id: str, 
                            account_id: str, 
                            token_url: str, 
                            client_id: str, 
                            client_secret: Optional[str]) -> Dict[str, Any]:
        """
        Uses a stored refresh_token to obtain a new access_token.
        """
        creds = await self.vault.retrieve_connection_secret(bridge_id, account_id)
        if not creds: return {"error": "no_credentials"}
        
        refresh_token = creds.get("refresh_token")
        if not refresh_token:
            return {"error": "no_refresh_token"}

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id
        }
        
        if client_secret:
            payload["client_secret"] = client_secret

        try:
            response = await self.client.post(token_url, data=payload)
            response.raise_for_status()
            new_tokens = response.json()
            
            # Merge and preserve missing fields (Hybrid Encryption)
            creds.update(new_tokens)
            await self.vault.store_connection_secret(bridge_id, account_id, creds)
            
            return creds
        except Exception as e:
            logger.error(f"Token refresh failed for {bridge_id}: {e}")
            return {"error": "refresh_failed", "details": str(e)}
