import pytest
pytestmark = pytest.mark.unit

import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from backend.security.network_policy import EgressFilterTransport, get_secure_client
from backend.security.exceptions import SecurityException

@pytest.mark.asyncio
async def test_egress_filter_trusted():
    inner = AsyncMock()
    inner.handle_async_request.return_value = httpx.Response(200)
    
    transport = EgressFilterTransport(inner)
    request = httpx.Request("GET", "https://api.openai.com/v1/models")
    
    response = await transport.handle_async_request(request)
    assert response.status_code == 200
    inner.handle_async_request.assert_called_once_with(request)

@pytest.mark.asyncio
async def test_egress_filter_untrusted():
    inner = AsyncMock()
    transport = EgressFilterTransport(inner)
    request = httpx.Request("GET", "https://evil.com/malware")
    
    with pytest.raises(SecurityException) as excinfo:
        await transport.handle_async_request(request)
        
    assert excinfo.value.exception_type == "DOMAIN_BLOCK"
    assert excinfo.value.metadata["domain"] == "evil.com"
    inner.handle_async_request.assert_not_called()

def test_get_secure_client():
    client = get_secure_client(timeout=10.0, transport="ignored")
    assert isinstance(client, httpx.AsyncClient)
    
    t = client._transport
    if hasattr(t, "_transport") and not isinstance(t, EgressFilterTransport):
        t = t._transport
        
    assert isinstance(t, EgressFilterTransport)
    assert client.timeout.read == 10.0
