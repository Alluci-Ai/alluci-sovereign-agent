import os
import sys
import logging
from .logging_config import get_logger
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

# Minimal fallback logging for module-load-time messages.
# structlog takes over in the app lifespan via logging_config.configure_logging().
if not logging.root.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
logger = get_logger("PolytopeConfig")


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Retrieves secrets from environment or a cloud Secrets Manager if configured."""
    # 1. Check direct environment override first
    v = os.getenv(key)
    if v:
        return v

    # 2. Check for AWS/GCP secrets if SECRETS_PROVIDER is set
    provider = os.getenv("SECRETS_PROVIDER", "").lower()
    if provider == "aws":
        try:
            import boto3
            client = boto3.client('secretsmanager')
            # SecretId is expected to be 'alluci/{env}/{key}'
            resp = client.get_secret_value(SecretId=f"alluci/{os.getenv('APP_ENV', 'dev')}/{key}")
            return resp.get('SecretString')
        except Exception as e:
            logger.warning(f"AWS Secrets Manager failed for {key}: {e}")
    
    return default

def get_system_ram_mb() -> int:
    """Detects total system RAM in MB. Fallback to 4GB if detection fails."""
    try:
        import psutil
        return int(psutil.virtual_memory().total / (1024 * 1024))
    except ImportError:
        # Fallback to /proc/meminfo on Linux if psutil is missing
        if os.path.exists("/proc/meminfo"):
            try:
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if "MemTotal" in line:
                            return int(line.split()[1]) // 1024
            except Exception:
                pass
    except Exception:
        pass
    return 4096 # Assume 4GB if unsure

class Settings(BaseSettings):
    # Deployment Environment
    APP_ENV: str = "development"  # development, production, local_sovereign
    
    # Security & Sovereignty
    POLYTOPE_MASTER_KEY: str
    JWT_SECRET_KEY: str  # Separate key for JWT signing — never reuse the vault master key
    CSRF_SECRET_KEY: str  # Separate key for CSRF token signing
    VERUS_ID_IDENTITY: Optional[str] = None
    VERUS_ID_PRIVATE_KEY: Optional[str] = None
    
    # Model Providers
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    NVIDIA_NIM_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    LM_STUDIO_URL: str = "http://localhost:1234/v1"
    TOGETHER_API_KEY: Optional[str] = None
    COHERE_API_KEY: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # OAuth Client Credentials (PPN/AAP)
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    SLACK_CLIENT_ID: Optional[str] = None
    SLACK_CLIENT_SECRET: Optional[str] = None
    SLACK_SIGNING_SECRET: Optional[str] = None
    SLACK_BOT_TOKEN: Optional[str] = None
    SLACK_VERIFICATION_TOKEN: Optional[str] = None
    SLACK_REDIRECT_URI: Optional[str] = "http://localhost:8000/api/channels/slack/callback"
    DISCORD_CLIENT_ID: Optional[str] = None
    DISCORD_CLIENT_SECRET: Optional[str] = None
    INSTAGRAM_CLIENT_ID: Optional[str] = None
    INSTAGRAM_CLIENT_SECRET: Optional[str] = None
    FACEBOOK_CLIENT_ID: Optional[str] = None
    FACEBOOK_CLIENT_SECRET: Optional[str] = None
    TWITTER_CLIENT_ID: Optional[str] = None
    TWITTER_CLIENT_SECRET: Optional[str] = None
    MSTEAMS_CLIENT_ID: Optional[str] = None
    MSTEAMS_CLIENT_SECRET: Optional[str] = None
    
    # WhatsApp Cloud API
    WHATSAPP_CLIENT_ID: Optional[str] = None
    WHATSAPP_CLIENT_SECRET: Optional[str] = None
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = None
    WHATSAPP_ACCESS_TOKEN: Optional[str] = None
    WHATSAPP_VERIFY_TOKEN: Optional[str] = None
    WHATSAPP_APP_SECRET: Optional[str] = None
    
    # Meta / Instagram / Facebook Additional
    META_APP_SECRET: Optional[str] = None
    META_VERIFY_TOKEN: Optional[str] = None

    # MS Teams Bot
    MSTEAMS_BOT_APP_ID: Optional[str] = None
    
    # WeCom (Enterprise WeChat)
    WECOM_CORP_ID: Optional[str] = None
    WECOM_CORP_SECRET: Optional[str] = None
    WECOM_AGENT_ID: Optional[str] = None
    WECOM_TOKEN: Optional[str] = None
    WECOM_ENCODING_AES_KEY: Optional[str] = None
    
    # Google Chat
    GOOGLE_CHAT_SERVICE_ACCOUNT_FILE: Optional[str] = None
    GOOGLE_CHAT_AUDIENCE: Optional[str] = None
    
    # Signal Bridge
    SIGNAL_CLI_PATH: str = "signal-cli"
    SIGNAL_SOCKET_PATH: str = "/tmp/signal-cli.sock"
    
    # iCloud Bridge
    ICLOUD_COOKIE_DIR: str = "~/.icloud"
    
    # Network
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
    
    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def strip_localhost_in_prod(cls, v: List[str], info) -> List[str]:
        # Use info.data to read the already-parsed APP_ENV value
        app_env = info.data.get("APP_ENV", os.getenv("APP_ENV", "development"))
        if app_env == "production":
            filtered = [
                origin for origin in v
                if "localhost" not in origin and "127.0.0.1" not in origin
            ]
            if not filtered:
                raise ValueError(
                    "ALLOWED_ORIGINS contains only localhost entries but APP_ENV=production. "
                    "Set ALLOWED_ORIGINS to your production domain."
                )
            return filtered
        return v

    # WebAuthn Settings
    WEBAUTHN_RP_ID: str = "localhost"
    WEBAUTHN_ORIGIN: str = "http://localhost:5173"

    AUTH_COOKIE_NAME: str = "alluci_daemon_token"
    AUTH_COOKIE_SAMESITE: str = "lax"  # Use 'lax' or 'strict' for local dev
    
    # Execution Governance
    MAX_AUTONOMY_RETRIES: int = 3
    CRITIC_THRESHOLD: float = 0.75
    MAX_CONCURRENT_TASKS: int = 5

    # Proactive Cognition Loop (PCL)
    PCL_ENABLED: bool = True
    PCL_CYCLE_INTERVAL: int = 300
    PCL_QUIET_START_HOUR: int = 22
    PCL_QUIET_END_HOUR: int = 7

    # Verus RPC Settings
    VERUS_RPC_HOST: str = "127.0.0.1"
    VERUS_RPC_PORT: int = 27486
    VERUS_RPC_USER: str = ""
    VERUS_RPC_PASSWORD: str = ""
    VERUS_AUTH_ENABLED: bool = False
    VERUS_WALLET_ENABLED: bool = True
    VERUS_LITE_MODE: bool = True # Default to Lite Mode
    VERUS_PUBLIC_RPC_URL: str = "https://api.verus.services"
    VERUS_NETWORK: str = "mainnet" # mainnet or vrsctest
    VERUS_STAKING_ADDRESS: Optional[str] = None
    VERUS_PBAAS_CHAINS: List[str] = ["VRSC", "VRSCTEST"]
    VERUS_DEFAULT_CURRENCY: str = "VRSC"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Local Sovereign Inference
    WHISPER_CPP_PATH: str = "whisper-cpp"
    OLLAMA_URL: str = "http://localhost:11434"
    PIPER_PATH: str = "piper"
    PIPER_MODEL: str = "en_US-amy-medium.onnx"

    # Database & Cache
    DATABASE_URL: str = "sqlite:///polytope_data.db"
    REDIS_URL: Optional[str] = None # e.g., redis://localhost:6379/0
    # Hardware Characteristics (P4-020)
    TOTAL_RAM_MB: int = get_system_ram_mb()
    LITE_MODE: bool = False
    
    @property
    def is_pi(self) -> bool:
        import platform
        return "arm" in platform.machine().lower() or "aarch64" in platform.machine().lower()

    @field_validator("LITE_MODE", mode="before")
    @classmethod
    def auto_detect_lite_mode(cls, v, info):
        # Explicit override takes precedence
        if v is not None and isinstance(v, bool):
            return v
        
        # Auto-detect based on RAM (< 2.5GB)
        ram = get_system_ram_mb()
        if ram < 2500:
            logger.info(f"Low memory detected ({ram}MB). Enabling LITE_MODE.")
            return True
        return False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("DATABASE_URL")
    @classmethod
    def enforce_production_db(cls, v: str, info) -> str:
        app_env = info.data.get("APP_ENV", os.getenv("APP_ENV", "development"))
        if app_env == "production" and "sqlite" in v:
            prod_url = os.getenv("PROD_DATABASE_URL")
            if not prod_url:
                logger.critical(
                    "\U0001f6a8 FATAL: APP_ENV=production but PROD_DATABASE_URL is not set. "
                    "SQLite is not suitable for production. "
                    "Set PROD_DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname"
                )
                sys.exit(1)
            return prod_url
        return v

    @field_validator("POLYTOPE_MASTER_KEY")
    @classmethod
    def validate_master_key(cls, v: str, info) -> str:
        """Enforces secure key requirements in all environments."""
        if not v or "PLACEHOLDER" in v:
            logger.critical("🚨 FATAL: POLYTOPE_MASTER_KEY must be set in .env or environment variables.")
            sys.exit(1)
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_key(cls, v: str) -> str:
        if not v or "PLACEHOLDER" in v:
            logger.critical("🚨 FATAL: JWT_SECRET_KEY must be set and distinct from POLYTOPE_MASTER_KEY.")
            sys.exit(1)
        return v

    @field_validator("CSRF_SECRET_KEY")
    @classmethod
    def csrf_key_must_be_distinct(cls, v, info):
        jwt_key = info.data.get("JWT_SECRET_KEY", "")
        master = info.data.get("POLYTOPE_MASTER_KEY", "")
        if v == jwt_key or v == master:
            raise ValueError("CSRF_SECRET_KEY must differ from JWT and vault keys.")
        return v

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_api_key(cls, v: Optional[str]) -> Optional[str]:
        if not v or "PLACEHOLDER" in v:
            logger.warning("⚠️ WARNING: GEMINI_API_KEY is not set. Cloud Inference Engine will be disabled.")
        return v

def load_settings() -> Settings:
    try:
        return Settings()
    except Exception as e:
        logger.critical(f"Configuration Load Failed: {e}")
        sys.exit(1)

# Global settings instance for canonical use
settings = load_settings()
