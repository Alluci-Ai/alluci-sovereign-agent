import os
import sys
import logging
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

# Setup structured logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PolytopeConfig")

class Settings(BaseSettings):
    # Deployment Environment
    APP_ENV: str = "development"  # development, production, local_sovereign
    
    # Security & Sovereignty
    POLYTOPE_MASTER_KEY: str
    JWT_SECRET_KEY: str  # Separate key for JWT signing — never reuse the vault master key
    VERUS_ID_IDENTITY: Optional[str] = None
    VERUS_ID_PRIVATE_KEY: Optional[str] = None
    
    # Model Providers
    GEMINI_API_KEY: str
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    NVIDIA_NIM_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    
    # Network
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]
    AUTH_COOKIE_NAME: str = "alluci_daemon_token"
    AUTH_COOKIE_SAMESITE: str = "lax"  # Use 'lax' or 'strict' for local dev
    
    # Execution Governance
    MAX_AUTONOMY_RETRIES: int = 3
    CRITIC_THRESHOLD: float = 0.75
    MAX_CONCURRENT_TASKS: int = 5

    # Verus RPC Settings
    VERUS_RPC_HOST: str = "127.0.0.1"
    VERUS_RPC_PORT: int = 27486
    VERUS_RPC_USER: str = ""
    VERUS_RPC_PASSWORD: str = ""
    VERUS_AUTH_ENABLED: bool = False
    VERUS_ID_IDENTITY: str = ""  # The agent's VerusID (e.g., alluci@)

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Database
    DATABASE_URL: str = "sqlite:///polytope_data.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

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

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v or "PLACEHOLDER" in v:
            logger.critical("🚨 FATAL: GEMINI_API_KEY is required for the Inference Engine.")
            sys.exit(1)
        return v

def load_settings() -> Settings:
    try:
        return Settings()
    except Exception as e:
        logger.critical(f"Configuration Load Failed: {e}")
        sys.exit(1)
