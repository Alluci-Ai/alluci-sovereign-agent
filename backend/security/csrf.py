from pydantic import BaseModel
from fastapi_csrf_protect import CsrfProtect
from ..config import settings

class CsrfSettings(BaseModel):
    auth_cookie_name: str = settings.AUTH_COOKIE_NAME
    csrf_secret: str = settings.CSRF_SECRET_KEY
    csrf_cookie_samesite: str = settings.AUTH_COOKIE_SAMESITE
    csrf_cookie_secure: bool = settings.APP_ENV != "development"

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()
