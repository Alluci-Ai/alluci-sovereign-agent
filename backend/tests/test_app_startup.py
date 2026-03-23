from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import pytest

def test_app_imports_and_lifespan_starts():
    """
    Validates that backend.app imports without NameError and 
    the FastAPI lifespan context manager starts and stops correctly.
    """
    with patch("backend.services.init_services", new=AsyncMock()), \
         patch("backend.services.shutdown_services", new=AsyncMock()), \
         patch("backend.services.vault", new=MagicMock()), \
         patch("backend.security.auth.init_jwt_keys"):

        import backend.app as app_module

        # Mock the vault keypair creation required during lifespan
        mock_private = MagicMock()
        mock_public = MagicMock()
        
        # Ensure services.vault is treated as the mock we defined
        app_module.services.vault.get_or_create_jwt_keypair = AsyncMock(
            return_value=(mock_private, mock_public)
        )

        with TestClient(app_module.app) as client:
            res = client.get("/health")
            assert res.status_code == 200
            assert res.json()["status"] == "healthy"
            
            # Verify the vault was called during startup
            app_module.services.vault.get_or_create_jwt_keypair.assert_called_once()
