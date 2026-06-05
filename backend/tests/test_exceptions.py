import pytest
from backend.security.exceptions import SecurityException

def test_security_exception():
    exc = SecurityException("test message", "TEST_ERROR", {"key": "value"})
    assert exc.message == "test message"
    assert exc.exception_type == "TEST_ERROR"
    assert exc.metadata == {"key": "value"}
    assert str(exc) == "test message"

def test_security_exception_no_metadata():
    exc = SecurityException("test message", "TEST_ERROR")
    assert exc.metadata == {}
