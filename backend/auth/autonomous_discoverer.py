# -*- coding: utf-8 -*-
"""
Copyright © 2026 Alluci-Ai. All Rights Reserved.
Sovereign Agentic Registration Kernel - auth.md Spec Protocol Enforcement Engine.
"""

import httpx
import importlib
import datetime
import uuid
import logging
import json
import re
from typing import Dict, Any, Optional, List
from ..config import settings
from jose import jwt

def _get_vault():
    """Return the vault instance.
    If a test has injected a mock into the module-level `vault` variable, use it.
    Otherwise lazily import from `backend.services`.
    """
    if vault is not None:
        return vault
    services = importlib.import_module('backend.services')
    return services.vault

logger = logging.getLogger("AuthMDDiscoverer")

class AlluciAutonomousDiscoverer:
    def __init__(self, manifest_path: str = ""):
        self.manifest_path = manifest_path
        # Core Identity properties for the Web IdP
        self.issuer = settings.AGENT_IDENTITY_ISSUER
        self.user_email = settings.AGENT_USER_EMAIL
        self.client_id = settings.AGENT_CLIENT_ID
        self.client_name = settings.AGENT_CLIENT_NAME
        self.client_uri = settings.AGENT_CLIENT_URI
        self.logo_uri = settings.AGENT_LOGO_URI
        self.tos_uri = settings.AGENT_TOS_URI

    async def discover_and_register(self, target_domain: str, scopes: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Executes a secure discovery sweep across a target service 
        and initiates agent registration (RFC 9728 / auth.md).
        """
        clean_domain = target_domain.rstrip('/')
        prm_url = f"{clean_domain}/.well-known/oauth-protected-resource"
        
        logger.info(f"[DISCOVERY] Probing discovery layers for target endpoint: {clean_domain}")
        
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            try:
                # Hop 1: Probe the Protected Resource Metadata endpoint (RFC 9728)
                prm_response = await client.get(prm_url)
                agent_auth_config = {}
                auth_server_url = None

                if prm_response.status_code == 200:
                    metadata = prm_response.json()
                    agent_auth_config = metadata.get("agent_auth", {})
                    auth_server_url = metadata.get("authorization_server")
                else:
                    logger.info(f"[DISCOVERY] PRM lookup missed. Checking fallback structural file: {clean_domain}/auth.md")
                    # Fallback to auth.md (not fully spec compliant as a metadata file, but common fallback)
                    auth_md_res = await client.get(f"{clean_domain}/auth.md")
                    if auth_md_res.status_code != 200:
                        raise FileNotFoundError("Service does not expose a compatible auth.md interface.")
                    
                    auth_md_content = auth_md_res.text
                    
                    # Regex Markdown parsing for auth.md
                    register_uri_match = re.search(r'`?register_uri`?:\s*`?(https?://[^\s`]+)`?', auth_md_content, re.IGNORECASE)
                    auth_server_match = re.search(r'`?authorization_server`?:\s*`?(https?://[^\s`]+)`?', auth_md_content, re.IGNORECASE)
                    id_types_match = re.search(r'`?identity_types_supported`?:\s*`?([^\n`]+)`?', auth_md_content, re.IGNORECASE)
                    
                    if register_uri_match:
                        agent_auth_config["register_uri"] = register_uri_match.group(1)
                    if auth_server_match:
                        auth_server_url = auth_server_match.group(1)
                    if id_types_match:
                        types_raw = id_types_match.group(1)
                        agent_auth_config["identity_types_supported"] = [t.strip() for t in types_raw.split(',')]

                if not agent_auth_config and auth_server_url:
                    # Hop 2: Resolve pointers down to the core Authorization Server metadata file
                    server_res = await client.get(f"{auth_server_url.rstrip('/')}/.well-known/oauth-authorization-server")
                    if server_res.status_code == 200:
                        agent_auth_config = server_res.json().get("agent_auth", {})

                # If still no agent_auth config, fallback to user claimed OTP flow
                if not agent_auth_config:
                    return await self.execute_user_claimed_fallback(client, clean_domain, auth_server_url or clean_domain)

                # Extract explicit target registration endpoint routes
                register_uri = agent_auth_config.get("register_uri")
                supported_types = agent_auth_config.get("identity_types_supported", [])

                if agent_auth_config and "register_uri" in agent_auth_config:
                    return await self.execute_agent_verified_handshake(
                        client, 
                        clean_domain, 
                        agent_auth_config["register_uri"], 
                        auth_server_url or clean_domain,
                        scopes=scopes
                    )
                elif "claim_token" in supported_types or not supported_types:
                    return await self.execute_user_claimed_fallback(client, clean_domain, auth_server_url or clean_domain)
                else:
                    logger.error(f"[AUTONOMOUS ERROR] Unsupported identity types: {supported_types}")
                    return None

            except Exception as error:
                logger.error(f"[AUTONOMOUS ERROR] Registration failed across domain boundaries: {str(error)}")
                return None

    def _generate_dpop_proof(self, private_key, method: str, url: str) -> str:
        import time
        from cryptography.hazmat.primitives import serialization
        import base64

        public_key = private_key.public_key()
        pn = public_key.public_numbers()
        
        def int_to_base64url(val):
            v_bytes = val.to_bytes((val.bit_length() + 7) // 8, byteorder='big')
            return base64.urlsafe_b64encode(v_bytes).decode('utf-8').rstrip("=")

        jwk = {
            "kty": "RSA",
            "n": int_to_base64url(pn.n),
            "e": int_to_base64url(pn.e)
        }
        
        headers = {
            "typ": "dpop+jwt",
            "alg": "RS256",
            "jwk": jwk
        }
        
        payload = {
            "jti": uuid.uuid4().hex,
            "htm": method.upper(),
            "htu": url,
            "iat": int(time.time())
        }
        
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        return jwt.encode(payload, pem, algorithm="RS256", headers=headers)

    async def execute_agent_verified_handshake(self, client: httpx.AsyncClient, domain: str, register_uri: str, auth_server: str, scopes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Mints an ID-JAG token, POSTs it to the registration endpoint, 
        and exchanges the resulting identity_assertion for an access_token.
        """
        logger.info(f"[HANDSHAKE] Generating signed ID-JAG identity token for: {register_uri}")
        
        now = datetime.datetime.now(datetime.timezone.utc)
        id_jag_claims = {
            "iss": self.issuer,
            "sub": f"alluci_user_{uuid.uuid4().hex[:12]}",
            "aud": auth_server,
            "client_id": self.client_id,
            "jti": uuid.uuid4().hex,
            "iat": now,
            "exp": now + datetime.timedelta(minutes=5),
            "email": self.user_email,
            "email_verified": True
        }

        local_vault = _get_vault()
        if local_vault is None:
            raise RuntimeError("VaultManager is not initialized. Cannot perform cryptographic signing.")
        
        # Use the newly partitioned Web IdP keypair
        private_key, _ = await local_vault.get_web_idp_keypair()
        
        from cryptography.hazmat.primitives import serialization
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        encoded_id_jag = jwt.encode(id_jag_claims, pem, algorithm="RS256")

        # 1. Register at /agent/identity to get the service-signed identity_assertion
        payload = {
            "type": "identity_assertion",
            "assertion": encoded_id_jag,
            "client_name": self.client_name,
            "client_uri": self.client_uri,
            "logo_uri": self.logo_uri,
            "tos_uri": self.tos_uri
        }

        if scopes:
            payload["scopes_requested"] = " ".join(scopes)

        dpop_proof = self._generate_dpop_proof(private_key, "POST", register_uri)
        headers = {"DPoP": dpop_proof}

        logger.info(f"[HANDSHAKE] Executing Claim Ceremony with {register_uri}")
        response = await client.post(register_uri, json=payload, headers=headers)
        if response.status_code not in [200, 201]:
            raise ConnectionRefusedError(f"Handshake rejected by target authorization endpoints: {response.text}")
            
        registration_data = response.json()
        service_assertion = registration_data.get("identity_assertion")
        client_id = registration_data.get("client_id")

        if not service_assertion:
            raise ValueError("Target server did not return a service-signed identity_assertion.")

        # 2. Exchange at /oauth2/token
        token_endpoint = f"{auth_server.rstrip('/')}/oauth2/token"
        token_payload = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": service_assertion,
            "client_id": client_id
        }

        if scopes:
            token_payload["scope"] = " ".join(scopes)

        dpop_token_proof = self._generate_dpop_proof(private_key, "POST", token_endpoint)
        token_headers = {"DPoP": dpop_token_proof}

        token_res = await client.post(token_endpoint, data=token_payload, headers=token_headers)
        if token_res.status_code == 200:
            logger.info("[SUCCESS] Subagent registration and token exchange completed.")
            return {
                "flow_type": "agent_verified",
                "status": "success",
                "access_token": token_res.json().get("access_token"),
                "refresh_token": token_res.json().get("refresh_token"),
                "expires_in": token_res.json().get("expires_in"),
                "client_id": client_id
            }
        else:
            raise ConnectionRefusedError(f"Token exchange failed: {token_res.text}")

    async def execute_user_claimed_fallback(self, client: httpx.AsyncClient, resource: str, auth_server: str) -> Dict[str, Any]:
        """
        Initiates the claim ceremony by calling the device authorization endpoint.
        Returns the user_code and verification_uri immediately.
        """
        logger.info(f"[FALLBACK] Initiating Claim Ceremony (RFC 8628) for: {auth_server}")
        device_endpoint = f"{auth_server.rstrip('/')}/oauth2/device_authorization"
        
        payload = {
            "client_id": self.client_id
        }
        
        # We attempt a device authorization grant
        try:
            res = await client.post(device_endpoint, data=payload)
            if res.status_code == 200:
                data = res.json()
                return {
                    "flow_type": "user_claimed",
                    "status": "authorization_pending",
                    "user_code": data.get("user_code"),
                    "verification_uri": data.get("verification_uri"),
                    "verification_uri_complete": data.get("verification_uri_complete"),
                    "device_code": data.get("device_code"),
                    "interval": data.get("interval", 5),
                    "token_endpoint": f"{auth_server.rstrip('/')}/oauth2/token"
                }
            else:
                logger.warning(f"Device authorization failed: {res.text}. Falling back to manual claim.")
        except Exception as e:
            logger.warning(f"Device authorization error: {e}")

        # Ultimate fallback if endpoint is totally absent
        return {
            "flow_type": "user_claimed",
            "status": "manual_intervention_required",
            "message": "Please register the agent manually at the target site."
        }

# Compatibility placeholder for test patches
vault = None
