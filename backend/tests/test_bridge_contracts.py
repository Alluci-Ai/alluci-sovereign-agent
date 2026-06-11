import pytest
pytestmark = pytest.mark.unit

from backend.app import SovereignAPIException

def test_api_exception_structure():
    """Validates the standard rigid error structure."""
    exc = SovereignAPIException(status_code=400, error_code="E_400_BAD_REQ", detail="Invalid parameter")
    assert exc.status_code == 400
    assert exc.error_code == "E_400_BAD_REQ"
    assert exc.detail == "Invalid parameter"
