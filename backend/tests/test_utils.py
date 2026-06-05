import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, patch
from backend.security.utils import sanitize_input, log_system_event

@pytest.mark.asyncio
async def test_sanitize_input_ok():
    text = "hello \x00 world"
    res = await sanitize_input(text)
    assert res == "hello  world"

@pytest.mark.asyncio
async def test_sanitize_input_too_long():
    text = "a" * 10001
    with pytest.raises(HTTPException) as excinfo:
        await sanitize_input(text)
    assert excinfo.value.status_code == 413
    assert "exceeds maximum length" in excinfo.value.detail

@pytest.mark.asyncio
async def test_sanitize_input_with_scanner_ok():
    scanner = AsyncMock()
    scanner.scan_input.return_value = (True, "")
    res = await sanitize_input("clean", scanner=scanner)
    assert res == "clean"
    scanner.scan_input.assert_called_once_with("clean")

@pytest.mark.asyncio
async def test_sanitize_input_with_scanner_fail():
    scanner = AsyncMock()
    scanner.scan_input.return_value = (False, "Bad input")
    with pytest.raises(HTTPException) as excinfo:
        await sanitize_input("dirty", scanner=scanner)
    assert excinfo.value.status_code == 400
    assert excinfo.value.detail == "Bad input"

@pytest.mark.asyncio
@patch("backend.security.audit_ledger.sync_audit_entry", new_callable=AsyncMock)
async def test_log_system_event(mock_sync):
    await log_system_event("TEST_EVENT", "Details", "OK")
    mock_sync.assert_called_once()
    entry = mock_sync.call_args[0][0]
    assert entry.event == "TEST_EVENT"
    assert entry.details == "Details"
    assert entry.status == "OK"

@pytest.mark.asyncio
@patch("backend.security.audit_ledger.sync_audit_entry", new_callable=AsyncMock)
async def test_log_system_event_exception(mock_sync):
    mock_sync.side_effect = Exception("db error")
    # Should catch exception and not raise
    await log_system_event("TEST_EVENT", "Details")
    mock_sync.assert_called_once()
