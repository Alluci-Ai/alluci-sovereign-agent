from pydantic import BaseModel
from fastapi_csrf_protect import CsrfProtect
from ..config import settings

class CsrfSettings(BaseModel):
    cookie_key: str = "fastapi-csrf-token"
    secret_key: str = settings.CSRF_SECRET_KEY
    cookie_samesite: str = "lax"
    cookie_secure: bool = settings.APP_ENV != "development"

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()
