# backend/config.py — MODULARIZED PRODUCTION SETTINGS
import os
import sys
import logging
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field, field_validator
from .logging_config import get_logger

logger = get_logger("PolytopeConfig")

def get_system_ram_mb() -> int:
    try:
        import psutil
        return int(psutil.virtual_memory().total / (1024 * 1024))
    except (ImportError, Exception):
        return 4096

# ── Domain Models ────────────────────────────────────────────────────────────

class SecuritySettings(BaseModel):
    POLYTOPE_MASTER_KEY: str
    JWT_SECRET_KEY: str
    CSRF_SECRET_KEY: str
    VERUS_ID_IDENTITY: Optional[str] = None
    VERUS_ID_PRIVATE_KEY: Optional[str] = None
    SENSITIVE_LOG_KEYS: List[str] = [
        "key", "secret", "token", "password", "key_id", "authorization", 
        "master_key", "jwt_secret", "api_key", "private_key"
    ]

class BridgeSettings(BaseModel):
    UNOFFICIAL_BRIDGES_ENABLED: bool = False
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    SIGNAL_CLI_PATH: str = "signal-cli"
    SIGNAL_SOCKET_PATH: str = "/tmp/signal-cli.sock"
    ICLOUD_COOKIE_DIR: str = "~/.icloud"
    
    # Verus Core
    VERUS_RPC_HOST: str = "localhost"
    VERUS_RPC_PORT: int = 27486
    VERUS_RPC_USER: Optional[str] = None
    VERUS_RPC_PASSWORD: Optional[str] = None
    VERUS_PUBLIC_RPC_URL: str = "https://api.verus.services"
    VERUS_LITE_MODE: bool = False

class InferenceSettings(BaseModel):
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL_STRONG: str = "llama3.3:70b"
    SOVEREIGN_MODE: bool = False
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

class RuntimeSettings(BaseModel):
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DATABASE_URL: str = "sqlite:///polytope_data.db"
    REDIS_URL: Optional[str] = None
    TOTAL_RAM_MB: int = get_system_ram_mb()
    LITE_MODE: bool = False

# ── Main Composed Settings ───────────────────────────────────────────────────

class Settings(BaseSettings):
    """
    Composed settings interface. 
    Flat for backward compatibility, but modularized internally.
    """
    # Runtime & Network
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Security
    POLYTOPE_MASTER_KEY: str
    JWT_SECRET_KEY: str
    CSRF_SECRET_KEY: str
    
    # AI/Inference
    SOVEREIGN_MODE: bool = False
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL_STRONG: str = "llama3.3:70b"
    
    # Storage
    DATABASE_URL: str = "sqlite:///polytope_data.db"
    REDIS_URL: Optional[str] = None
    
    # Governance
    RATE_LIMIT_PER_MINUTE: int = 60
    MAX_CONCURRENT_TASKS: int = 5
    
    # Verus Core
    VERUS_RPC_HOST: str = "localhost"
    VERUS_RPC_PORT: int = 27486
    VERUS_RPC_USER: Optional[str] = None
    VERUS_RPC_PASSWORD: Optional[str] = None
    VERUS_PUBLIC_RPC_URL: str = "https://api.verus.services"
    VERUS_LITE_MODE: bool = False
    VERUS_ID_IDENTITY: Optional[str] = None
    VERUS_ID_PRIVATE_KEY: Optional[str] = None
    
    # Auth & Cookies
    AUTH_COOKIE_NAME: str = "alluci_daemon_token"
    AUTH_COOKIE_SECURE: bool = False  # Set to True in production
    AUTH_COOKIE_SAMESITE: str = "lax"
    VERUS_AUTH_ENABLED: bool = False
    
    # WebAuthn
    WEBAUTHN_RP_ID: str = "localhost"
    WEBAUTHN_ORIGIN: str = "http://localhost:5173"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=()
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def enforce_production_db(cls, v: str, info) -> str:
        app_env = info.data.get("APP_ENV", "development")
        if app_env == "production" and "sqlite" in v:
            prod_url = os.getenv("PROD_DATABASE_URL")
            if not prod_url:
                logger.critical("FATAL: Production requires PROD_DATABASE_URL")
                sys.exit(1)
            return prod_url
        return v

def load_settings() -> Settings:
    try:
        return Settings()
    except Exception as e:
        logger.critical(f"Config Fail: {e}")
        sys.exit(1)

settings = load_settings()
