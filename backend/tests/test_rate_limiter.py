import pytest
pytestmark = pytest.mark.unit

import time
from fastapi import Request, Response, HTTPException
from unittest.mock import MagicMock, AsyncMock, patch
from backend.security.rate_limiter import SlidingWindowLimiter, get_fallback_limiter
from backend.security.rate_limit import RateLimiter
from backend.config import settings

@pytest.fixture
def mock_request():
    req = MagicMock(spec=Request)
    req.headers = {"x-forwarded-for": "192.168.1.1"}
    req.url.path = "/test/path"
    req.client.host = "192.168.1.1"
    return req

@pytest.fixture
def sliding_limiter():
    return SlidingWindowLimiter()

@pytest.mark.asyncio
async def test_sliding_window_make_key(sliding_limiter, mock_request):
    key = sliding_limiter._make_key(mock_request)
    assert key == "192.168.1.1:/test/path"

@pytest.mark.asyncio
async def test_sliding_window_check_ok(sliding_limiter, mock_request):
    await sliding_limiter.check(mock_request, times=5, seconds=60)
    key = sliding_limiter._make_key(mock_request)
    assert len(sliding_limiter._windows[key]) == 1

@pytest.mark.asyncio
async def test_sliding_window_check_exceeded(sliding_limiter, mock_request):
    for _ in range(2):
        await sliding_limiter.check(mock_request, times=2, seconds=60)
    
    with pytest.raises(HTTPException) as excinfo:
        await sliding_limiter.check(mock_request, times=2, seconds=60)
    assert excinfo.value.status_code == 429

@pytest.mark.asyncio
async def test_sliding_window_reset(sliding_limiter, mock_request):
    await sliding_limiter.check(mock_request, times=5, seconds=60)
    await sliding_limiter.reset(mock_request)
    key = sliding_limiter._make_key(mock_request)
    assert key not in sliding_limiter._windows

@pytest.mark.asyncio
@patch("backend.security.rate_limit.FastAPIRateLimiter.__call__", new_callable=AsyncMock)
async def test_rate_limit_adapter_success(mock_fastapi_call, mock_request):
    limiter = RateLimiter(times=5, seconds=60)
    res = MagicMock(spec=Response)
    
    mock_fastapi_call.return_value = None
    
    await limiter(mock_request, res)
    mock_fastapi_call.assert_called_once_with(mock_request, res)

@pytest.mark.asyncio
@patch("backend.security.rate_limit.FastAPIRateLimiter.__call__", new_callable=AsyncMock)
@patch.object(SlidingWindowLimiter, "check", new_callable=AsyncMock)
@patch("backend.security.rate_limit.settings")
async def test_rate_limit_adapter_fallback_development(mock_settings, mock_check, mock_fastapi_call, mock_request):
    mock_settings.APP_ENV = "development"
    limiter = RateLimiter(times=5, seconds=60)
    res = MagicMock(spec=Response)
    
    mock_fastapi_call.side_effect = Exception("redis error")
    
    await limiter(mock_request, res)
    
    mock_fastapi_call.assert_called_once_with(mock_request, res)
    mock_check.assert_called_once_with(mock_request, times=5, seconds=60)

@pytest.mark.asyncio
@patch("backend.security.rate_limit.FastAPIRateLimiter.__call__", new_callable=AsyncMock)
@patch("backend.security.rate_limit.settings")
async def test_rate_limit_adapter_fallback_production(mock_settings, mock_fastapi_call, mock_request):
    mock_settings.APP_ENV = "production"
    limiter = RateLimiter(times=5, seconds=60)
    res = MagicMock(spec=Response)
    
    mock_fastapi_call.side_effect = Exception("redis error")
    
    with pytest.raises(HTTPException) as excinfo:
        await limiter(mock_request, res)
        
    assert excinfo.value.status_code == 500
