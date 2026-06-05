import pytest
from backend.security.csrf import CsrfSettings
from backend.config import settings

def test_csrf_config():
    config = CsrfSettings()
    assert config.cookie_key == "fastapi-csrf-token"
    assert config.cookie_samesite == "lax"
    assert config.secret_key == settings.CSRF_SECRET_KEY
    assert config.cookie_secure == (settings.APP_ENV != "development")
