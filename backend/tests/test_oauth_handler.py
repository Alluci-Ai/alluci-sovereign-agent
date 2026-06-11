import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, patch, MagicMock
import httpx
from backend.security.oauth_handler import OAuthHandler

@pytest.fixture
def mock_vault():
    vault = AsyncMock()
    return vault

@pytest.fixture
def oauth_handler(mock_vault):
    handler = OAuthHandler(vault=mock_vault)
    handler.client = AsyncMock()
    return handler

@pytest.mark.asyncio
async def test_close(oauth_handler):
    await oauth_handler.close()
    oauth_handler.client.aclose.assert_called_once()

def test_generate_pkce_pair():
    verifier, challenge = OAuthHandler.generate_pkce_pair()
    assert len(verifier) > 0
    assert len(challenge) > 0
    assert "=" not in challenge

@pytest.mark.asyncio
async def test_exchange_code_success(oauth_handler, mock_vault):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "token123"}
    mock_resp.raise_for_status.return_value = None
    oauth_handler.client.post.return_value = mock_resp

    res = await oauth_handler.exchange_code(
        "slack", "acc1", "http://token", "client1", "secret1", "code1", "http://redir", "verifier1"
    )

    assert res == {"access_token": "token123"}
    mock_vault.store_connection_secret.assert_called_once_with("slack", "acc1", {"access_token": "token123"})
    oauth_handler.client.post.assert_called_once()
    kwargs = oauth_handler.client.post.call_args.kwargs
    assert kwargs["data"]["client_secret"] == "secret1"
    assert kwargs["data"]["code_verifier"] == "verifier1"

@pytest.mark.asyncio
async def test_exchange_code_http_error(oauth_handler):
    mock_resp = MagicMock()
    mock_resp.text = "Bad Request"
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError("error", request=MagicMock(), response=mock_resp)
    oauth_handler.client.post.return_value = mock_resp

    res = await oauth_handler.exchange_code(
        "slack", "acc1", "http://token", "client1", None, "code1", "http://redir"
    )

    assert res["error"] == "exchange_failed"
    assert "Bad Request" in res["details"]

@pytest.mark.asyncio
async def test_exchange_code_unexpected_error(oauth_handler):
    oauth_handler.client.post.side_effect = Exception("Unknown")

    res = await oauth_handler.exchange_code(
        "slack", "acc1", "http://token", "client1", None, "code1", "http://redir"
    )

    assert res["error"] == "internal_error"
    assert "Unknown" in res["details"]

@pytest.mark.asyncio
async def test_refresh_token_no_creds(oauth_handler, mock_vault):
    mock_vault.retrieve_connection_secret.return_value = None
    res = await oauth_handler.refresh_token("slack", "acc1", "http://token", "client1", "secret1")
    assert res["error"] == "no_credentials"

@pytest.mark.asyncio
async def test_refresh_token_no_refresh_token(oauth_handler, mock_vault):
    mock_vault.retrieve_connection_secret.return_value = {"access_token": "token1"}
    res = await oauth_handler.refresh_token("slack", "acc1", "http://token", "client1", "secret1")
    assert res["error"] == "no_refresh_token"

@pytest.mark.asyncio
async def test_refresh_token_success(oauth_handler, mock_vault):
    mock_vault.retrieve_connection_secret.return_value = {"refresh_token": "ref123", "old_field": "keep"}
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "token_new"}
    mock_resp.raise_for_status.return_value = None
    oauth_handler.client.post.return_value = mock_resp

    res = await oauth_handler.refresh_token("slack", "acc1", "http://token", "client1", "secret1")

    assert res["access_token"] == "token_new"
    assert res["old_field"] == "keep"
    mock_vault.store_connection_secret.assert_called_once()
    
    kwargs = oauth_handler.client.post.call_args.kwargs
    assert kwargs["data"]["client_secret"] == "secret1"
    assert kwargs["data"]["refresh_token"] == "ref123"

@pytest.mark.asyncio
async def test_refresh_token_error(oauth_handler, mock_vault):
    mock_vault.retrieve_connection_secret.return_value = {"refresh_token": "ref123"}
    oauth_handler.client.post.side_effect = Exception("Fail")

    res = await oauth_handler.refresh_token("slack", "acc1", "http://token", "client1", None)

    assert res["error"] == "refresh_failed"
    assert "Fail" in res["details"]
