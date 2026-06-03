import httpx
from typing import Set
from urllib.parse import urlparse
from ..logging_config import get_logger

logger = get_logger("NetworkPolicy")

from .exceptions import SecurityException

class EgressFilterTransport(httpx.AsyncBaseTransport):
    """
    Zero-Trust Network Egress Filter for the Core Agent.
    Strictly intercepts and drops any HTTP requests to domains not in the TRUSTED_DOMAINS allowlist.
    """
    
    TRUSTED_DOMAINS: Set[str] = {
        "127.0.0.1",
        "localhost",
        "api.openai.com",
        "api.anthropic.com",
        "api.cohere.ai",
        "generativelanguage.googleapis.com",
        "discord.com",
        "slack.com",
        "api.telegram.org",
        "api.twitter.com"
    }

    def __init__(self, inner_transport: httpx.AsyncBaseTransport):
        self._inner = inner_transport

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        domain = request.url.host
        if domain not in self.TRUSTED_DOMAINS:
            logger.error(f"[SECURITY] EGRESS BLOCKED: Attempted to contact untrusted domain '{domain}'.")
            raise SecurityException(
                f"Network request to untrusted domain '{domain}' was blocked by the Vault Core firewall.",
                exception_type="DOMAIN_BLOCK",
                metadata={"domain": domain}
            )
        
        return await self._inner.handle_async_request(request)

def get_secure_client(**kwargs) -> httpx.AsyncClient:
    """Returns an httpx.AsyncClient wrapped in the EgressFilterTransport."""
    base_transport = httpx.AsyncHTTPTransport()
    secure_transport = EgressFilterTransport(base_transport)
    
    # We must pop the 'transport' arg if it exists to avoid conflicts
    if 'transport' in kwargs:
        kwargs.pop('transport')
        
    return httpx.AsyncClient(transport=secure_transport, **kwargs)
