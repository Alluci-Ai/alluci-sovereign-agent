# backend/config.py — MODULARIZED PRODUCTION SETTINGS
import sys
from typing import List, Optional, Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, field_validator
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
    STRICT_BIOMETRIC_GATING: bool = False
    REQUIRE_WATCH_TELEMETRY: bool = False
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
    VERUS_INTEGRATION_MODE: Literal["off", "lite", "full"] = "off"

from pydantic import BaseModel, Field

class InferenceSettings(BaseModel):
    LOCAL_LCE_URL: str = "http://localhost:8000"
    LOCAL_MODEL_MAX: str = "alluci-polytope-gemma-4-31b-it-bf16"
    LOCAL_MODEL_STRONG: str = "alluci-polytope-gemma-4-31b-it-8bit"
    LOCAL_MODEL_MEDIUM: str = "alluci-polytope-gemma-4-26b-a4b-it-4bit"
    LOCAL_MODEL_LIGHT: str = Field(default="alluci-polytope-gemma-4-12B-it-4bit", title="Local Model Lite")
    LOCAL_MODEL_LITE: str = Field(default="alluci-polytope-gemma-4-e2b-it-4bit", title="Local Model Edge")
    SOVEREIGN_MODE: bool = False
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

class RuntimeSettings(BaseModel):
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DATABASE_URL: str = "sqlite:///:memory:"
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
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
    
    # Security
    POLYTOPE_MASTER_KEY: str
    JWT_SECRET_KEY: str
    CSRF_SECRET_KEY: str
    STRICT_BIOMETRIC_GATING: bool = False
    REQUIRE_WATCH_TELEMETRY: bool = False
    
    # AI/Inference
    SOVEREIGN_MODE: bool = False
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    LOCAL_LCE_URL: str = "http://localhost:8000"
    LOCAL_MODEL_MAX: str = "alluci-polytope-gemma-4-31b-it-bf16"
    LOCAL_MODEL_STRONG: str = "alluci-polytope-gemma-4-31b-it-8bit"
    LOCAL_MODEL_MEDIUM: str = "alluci-polytope-gemma-4-26b-a4b-it-4bit"
    LOCAL_MODEL_LIGHT: str = Field(default="alluci-polytope-gemma-4-12B-it-4bit", title="Local Model Lite")
    LOCAL_MODEL_LITE: str = Field(default="alluci-polytope-gemma-4-e2b-it-4bit", title="Local Model Edge")
    
    # Storage
    DATABASE_URL: str = "sqlite:///db.sqlite3"
    GRAPH_DB_PATH: str = "./polytope_data.kuzu"
    REDIS_URL: Optional[str] = None
    POLYTOPE_STORAGE_ROOT: str = "~/.polytope"
    ICLOUD_COOKIE_DIR: str = "~/.icloud"

    # Observability
    SENTRY_DSN: Optional[str] = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    
    # Governance
    RATE_LIMIT_PER_MINUTE: int = 60
    MAX_CONCURRENT_TASKS: int = 5
    MAX_CONCURRENCY: int = 5  # Controls inference concurrency, can be overridden via env var
    MAX_AUTONOMY_RETRIES: int = 3
    TASK_TIMEOUT_SECONDS: float = 3600.0  # Configurable task execution timeout in seconds
    CRITIC_THRESHOLD: float = 0.75
    HEARTBEAT_INTERVAL: int = 30
    
    # Verus Core
    VERUS_RPC_HOST: str = "localhost"
    VERUS_RPC_PORT: int = 27486
    VERUS_RPC_USER: Optional[str] = None
    VERUS_RPC_PASSWORD: Optional[str] = None
    VERUS_PUBLIC_RPC_URL: str = "https://api.verus.services"
    VERUS_INTEGRATION_MODE: Literal["off", "lite", "full"] = "off"
    VERUS_ID_IDENTITY: Optional[str] = None
    VERUS_ID_PRIVATE_KEY: Optional[str] = None
    VERUS_SYSTEM_ID: str = "i5w5MuNik5NtLcYmNzcvaoixooEebB6MGV"  # VRSC
    VERUS_PBAAS_CHAINS: List[str] = ["VRSC", "vETH"]
    UNOFFICIAL_BRIDGES_ENABLED: bool = False
    
    # Signal
    SIGNAL_CLI_PATH: str = "/opt/homebrew/bin/signal-cli"
    SIGNAL_SOCKET_PATH: str = "/tmp/signal-cli.sock"
    
    # Auth & Cookies
    AUTH_COOKIE_NAME: str = "alluci_daemon_token"
    AUTH_COOKIE_SECURE: bool = False  # Should be False for local Electron apps
    AUTH_COOKIE_SAMESITE: Literal["lax", "none", "strict"] = "lax"
    
    # Agentic Identity / Auth.md
    AGENT_IDENTITY_ISSUER: str = "https://identity.alluci-ai.internal"
    AGENT_USER_EMAIL: str = "query@alluci.ai"
    AGENT_CLIENT_ID: str = "https://registry.alluci-ai.internal/profiles/agent-v4"
    AGENT_CLIENT_NAME: str = "Alluci Sovereign Assistant"
    AGENT_CLIENT_URI: str = "https://alluci.ai"
    AGENT_LOGO_URI: str = "https://alluci.ai/logo.png"
    AGENT_TOS_URI: str = "https://alluci.ai/tos"
    
    # WebAuthn
    WEBAUTHN_RP_ID: Optional[str] = None
    WEBAUTHN_ORIGIN: Optional[str] = None
    
    # Modes
    DEBUG: bool = False
    LITE_MODE: bool = False
    
    # Compliance & Data Residency
    DATA_REGION: Literal["US", "EU", "GLOBAL"] = "GLOBAL"
    ENFORCE_EU_ENDPOINTS: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=()
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def enforce_production_db(cls, v: str, info) -> str:
        # Since the Sovereign Agent is a 100% local-first Electron application,
        # 'production' environments should indeed run on the local SQLite DB.
        # We no longer force a remote PostgreSQL URL here.
        return v

    @field_validator("AUTH_COOKIE_SECURE")
    @classmethod
    def enforce_secure_cookies(cls, v: bool, info) -> bool:
        # For a local-first Electron app running on localhost, enforcing Secure cookies
        # over HTTP will cause browsers to reject them, breaking CSRF. 
        # We respect the environment variable value rather than forcing it based on APP_ENV.
        return v

def load_settings() -> Settings:
    try:
        return Settings()  # type: ignore
    except Exception as e:
        logger.critical(f"Config Fail: {e}")
        sys.exit(1)

settings = load_settings()
