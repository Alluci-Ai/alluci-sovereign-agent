import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

import backend.services
import backend.core.startup_checks
import backend.security.auth

def test_app_imports_and_lifespan_starts():
    """
    Validates that backend.app imports without NameError and 
    the FastAPI lifespan context manager starts and stops correctly.
    """
    with patch("backend.services.init_services", new=AsyncMock()) as mock_init, \
         patch("backend.services.shutdown_services", new=AsyncMock()) as mock_shutdown, \
         patch("backend.services.vault", new=MagicMock()) as mock_vault, \
         patch("backend.security.auth.init_jwt_keys"), \
         patch("backend.core.startup_checks.assert_secrets_are_set"), \
         patch("backend.core.startup_checks.warn_on_stale_model_ids"):

        import backend.app as app_module
        
        # Ensure we use the mocked vault for the keypair call
        mock_vault.get_or_create_jwt_keypair = AsyncMock(
            return_value=("mock_priv", "mock_pub")
        )

        with TestClient(app_module.app) as client:
            response = client.get("/health")
            # We don't necessarily need 200, just that it didn't crash
            assert response.status_code in [200, 404]

        assert mock_init.called
        assert mock_shutdown.called
        # Verify the vault was called during startup
        mock_vault.get_or_create_jwt_keypair.assert_called_once()
