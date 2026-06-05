# -*- coding: utf-8 -*-
"""
Copyright © 2026 Alluci-Ai. All Rights Reserved.
Sovereign Agentic Registration Kernel - auth.md Spec Protocol Enforcement Engine.
"""

import os
import httpx
import jwt
import importlib

def _get_vault():
    """Lazily import and return the vault instance from backend.services.
    This avoids importing the entire services module at import time, which pulls in many heavy dependencies.
    """
    services = importlib.import_module('backend.services')
    return services.vault
import datetime
import uuid
import logging
from typing import Dict, Any, Optional
# Vault is fetched lazily via _get_vault()

logger = logging.getLogger("AuthMDDiscoverer")

class AlluciAutonomousDiscoverer:
    def __init__(self, manifest_path: str):
        self.manifest_path = manifest_path
        # Simulated loading of identity parameters from manifest
        self.issuer = "https://identity.alluci-ai.internal"
        self.user_email = "architect@alluci-ai.net"

    async def discover_and_register(self, target_domain: str) -> Optional[Dict[str, Any]]:
        """
        Executes a secure two-hop discovery sweep across a target service 
        and completes agent registration natively.
        """
        clean_domain = target_domain.rstrip('/')
        prm_url = f"{clean_domain}/.well-known/oauth-protected-resource"
        
        logger.info(f"[DISCOVERY] Probing discovery layers for target endpoint: {clean_domain}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Hop 1: Probe the Protected Resource Metadata endpoint (RFC 9728)
                prm_response = await client.get(prm_url)
                if prm_response.status_code != 200:
                    logger.info(f"[DISCOVERY] PRM lookup missed. Checking fallback structural file: {clean_domain}/auth.md")
                    # Fallback to reading raw Markdown file definitions
                    auth_md_res = await client.get(f"{clean_domain}/auth.md")
                    if auth_md_res.status_code != 200:
                        raise FileNotFoundError(f"Service does not expose a compatible auth.md interface.")
                    return await self.execute_user_claimed_fallback(clean_domain)

                metadata = prm_response.json()
                agent_auth_config = metadata.get("agent_auth", {})
                
                if not agent_auth_config:
                    # Hop 2: Resolve pointers down to the core Authorization Server metadata file
                    auth_server_url = metadata.get("authorization_server")
                    if auth_server_url:
                        server_res = await client.get(f"{auth_server_url}/.well-known/oauth-authorization-server")
                        agent_auth_config = server_res.json().get("agent_auth", {})

                # If still no agent_auth config, fallback to user claimed OTP flow
                if not agent_auth_config:
                    return await self.execute_user_claimed_fallback(clean_domain)

                # Extract explicit target registration endpoint routes
                register_uri = agent_auth_config.get("register_uri")
                supported_types = agent_auth_config.get("identity_types_supported", [])

                if "identity_assertion" in supported_types and register_uri:
                    return await self.execute_agent_verified_handshake(client, register_uri, clean_domain)
                else:
                    return await self.execute_user_claimed_fallback(clean_domain)

            except Exception as error:
                logger.error(f"[AUTONOMOUS ERROR] Registration failed across domain boundaries: {str(error)}")
                return None

    async def execute_agent_verified_handshake(self, client: httpx.AsyncClient, register_uri: str, target_domain: str) -> Dict[str, Any]:
        """Mints an ID-JAG token and handles autonomous agent registration."""
        logger.info(f"[HANDSHAKE] Generating signed ID-JAG identity token for: {register_uri}")
        
        # Assemble standard claims matching the identity token specifications
        now = datetime.datetime.now(datetime.timezone.utc)
        id_jag_claims = {
            "iss": self.issuer,
            "sub": f"alluci_user_{uuid.uuid4().hex[:12]}",
            "aud": target_domain,
            "client_id": "https://registry.alluci-ai.internal/profiles/agent-v4",
            "jti": uuid.uuid4().hex,
            "iat": now,
            "exp": now + datetime.timedelta(minutes=5),
            "email": self.user_email,
            "email_verified": True
        }

        # Retrieve secure private key from the Sovereign Vault
        local_vault = _get_vault()
        if local_vault is None:
            raise RuntimeError("VaultManager is not initialized. Cannot perform cryptographic signing.")
        private_key, _ = await local_vault.get_or_create_jwt_keypair()
        
        # Generate the bearer authentication assertion token
        encoded_id_jag = jwt.encode(id_jag_claims, private_key, algorithm="RS256")

        payload = {
            "type": "identity_assertion",
            "assertion": encoded_id_jag,
            "requested_credential_type": "api_key"
        }

        response = await client.post(register_uri, json=payload)
        if response.status_code in [200, 201]:
            credential_package = response.json()
            logger.info("[SUCCESS] Subagent registration completed. Secured native execution keys.")
            return credential_package
        
        raise ConnectionRefusedError(f"Handshake rejected by target authorization endpoints: {response.text}")

    async def execute_user_claimed_fallback(self, target_domain: str) -> Dict[str, Any]:
        logger.info(f"[FALLBACK] Initiating OTP verification sequence for: {target_domain}")
        # Returns a standard instruction state machine to route OTP alerts to your dashboard
        return {"flow_type": "user_claimed_otp", "status": "awaiting_user_token_input"}
