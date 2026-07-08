import httpx
from typing import Dict, Any
from backend.logging_config import get_logger
from backend.auth.autonomous_discoverer import AlluciAutonomousDiscoverer

logger = get_logger("AgenticRevocationAdapter")

class AgenticRevocationAdapter:
    name = "agentic_revocation"
    description = "Revokes agent access to a target domain using RFC 7009 Token Revocation."

    async def execute(self, args: Dict[str, Any]) -> Any:
        target_domain = args.get("target_domain")
        if not target_domain:
            return {"status": "error", "message": "target_domain is required."}

        from backend import services
        if not services.vault:
            return {"status": "error", "message": "Vault is not available."}

        secret = await services.vault.retrieve_connection_secret("agent_registration", target_domain)
        if not secret or not secret.get("access_token"):
            return {"status": "error", "message": f"No active agent registration found for {target_domain}."}

        # We need the authorization server. We can use the discoverer to find it.
        discoverer = AlluciAutonomousDiscoverer()
        clean_domain = target_domain.rstrip('/')
        prm_url = f"{clean_domain}/.well-known/oauth-protected-resource"
        
        auth_server_url = clean_domain
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            try:
                prm_response = await client.get(prm_url)
                if prm_response.status_code == 200:
                    metadata = prm_response.json()
                    auth_server_url = metadata.get("authorization_server", clean_domain)
                else:
                    auth_md_res = await client.get(f"{clean_domain}/auth.md")
                    if auth_md_res.status_code == 200:
                        import re
                        auth_server_match = re.search(r'`?authorization_server`?:\s*`?(https?://[^\s`]+)`?', auth_md_res.text, re.IGNORECASE)
                        if auth_server_match:
                            auth_server_url = auth_server_match.group(1)
            except Exception as e:
                logger.warning(f"Discovery for revocation failed: {e}. Using {clean_domain} as auth server.")

        revoke_endpoint = f"{auth_server_url.rstrip('/')}/oauth2/revoke"
        
        # Prepare DPoP proof
        private_key, _ = await services.vault.get_web_idp_keypair()
        dpop_proof = discoverer._generate_dpop_proof(private_key, "POST", revoke_endpoint)
        
        payload = {
            "token": secret.get("access_token"),
            "token_type_hint": "access_token",
            "client_id": secret.get("client_id")
        }
        
        headers = {"DPoP": dpop_proof}

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                res = await client.post(revoke_endpoint, data=payload, headers=headers)
                if res.status_code in [200, 204]:
                    await services.vault.delete_connection_secret("agent_registration", target_domain, skip_revoke=True)
                    if services.memory:
                        await services.memory.l1_store(f"Revoked agent registration for {target_domain}.", source="agentic_revocation")
                    return {"status": "success", "message": f"Successfully revoked access for {target_domain}"}
                else:
                    return {"status": "error", "message": f"Revocation failed: {res.text}"}
            except Exception as e:
                return {"status": "error", "message": f"Revocation error: {str(e)}"}
