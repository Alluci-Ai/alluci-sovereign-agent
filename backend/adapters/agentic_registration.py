import asyncio
import httpx
from typing import Dict, Any
from .base import Adapter
from ..logging_config import get_logger
from ..auth.autonomous_discoverer import AlluciAutonomousDiscoverer

logger = get_logger("AgenticRegistrationAdapter")

class AgenticRegistrationAdapter(Adapter):
    name = "agentic_registration"
    description = "Discovers and registers the agent on a target domain using auth.md and RFC 9728."

    async def execute(self, args: Dict[str, Any]) -> Any:
        target_domain = args.get("target_domain")
        scopes = args.get("scopes")
        if not target_domain:
            return {"status": "error", "message": "target_domain is required."}

        discoverer = AlluciAutonomousDiscoverer()
        try:
            result = await discoverer.discover_and_register(target_domain, scopes=scopes)
            if not result:
                return {"status": "error", "message": "Discovery failed or returned no data."}

            if result.get("flow_type") == "user_claimed" and result.get("status") == "authorization_pending":
                # Start background polling task so we don't block the Orchestrator
                asyncio.create_task(self._poll_for_token(result, target_domain))
                
                return {
                    "status": "success",
                    "flow_type": "user_claimed",
                    "message": "Claim ceremony initiated. Please present the user_code and verification_uri to the user.",
                    "user_code": result.get("user_code"),
                    "verification_uri": result.get("verification_uri"),
                    "verification_uri_complete": result.get("verification_uri_complete")
                }
            elif result.get("flow_type") == "agent_verified":
                # Store access_token in vault
                from .. import services
                if services.vault:
                    await services.vault.store_connection_secret("agent_registration", target_domain, {
                        "access_token": result.get("access_token"),
                        "refresh_token": result.get("refresh_token"),
                        "expires_in": result.get("expires_in"),
                        "client_id": result.get("client_id")
                    })
                return {
                    "status": "success",
                    "flow_type": "agent_verified",
                    "message": "Agent verified successfully and token stored in Vault."
                }
            
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"AgenticRegistrationAdapter failed: {e}")
            return {"status": "error", "message": str(e)}

    async def _poll_for_token(self, claim_data: Dict[str, Any], target_domain: str):
        device_code = claim_data.get("device_code")
        interval = claim_data.get("interval", 5)
        token_endpoint = claim_data.get("token_endpoint")
        
        from ..config import settings
        client_id = settings.AGENT_CLIENT_ID

        if not all([device_code, token_endpoint]):
            logger.error("Missing polling data for claim ceremony.")
            return

        payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code or "",
            "client_id": client_id or ""
        }
        
        if not token_endpoint:
            logger.error("No token_endpoint provided for polling.")
            return

        max_attempts = 120 # e.g. 10 minutes at 5s interval
        attempts = 0

        async with httpx.AsyncClient(timeout=10.0) as client:
            while attempts < max_attempts:
                try:
                    res = await client.post(token_endpoint, data=payload)
                    if res.status_code == 200:
                        token_data = res.json()
                        access_token = token_data.get("access_token")
                        logger.info(f"Successfully retrieved token for {target_domain} via claim ceremony.")
                        
                        from .. import services
                        if services.vault:
                            await services.vault.store_connection_secret("agent_registration", target_domain, {
                                "access_token": access_token,
                                "refresh_token": token_data.get("refresh_token"),
                                "expires_in": token_data.get("expires_in"),
                                "client_id": client_id
                            })
                        
                        # Notify Memory if available
                        if services.memory:
                            await services.memory.l1_store(
                                f"Agentic Registration completed for {target_domain}. Token stored in vault.",
                                source="agentic_registration"
                            )
                        break
                    elif res.status_code == 400:
                        error_code = res.json().get("error")
                        if error_code == "authorization_pending":
                            # Keep polling
                            pass
                        elif error_code == "slow_down":
                            interval += 2
                        elif error_code in ["expired_token", "access_denied"]:
                            logger.error(f"Claim ceremony failed: {error_code}")
                            break
                        else:
                            logger.error(f"Unknown error during polling: {error_code}")
                            break
                    else:
                        logger.error(f"Unexpected status during polling: {res.status_code}")
                        break
                except Exception as e:
                    logger.error(f"Polling error: {e}")
                
                await asyncio.sleep(interval)
                attempts += 1
