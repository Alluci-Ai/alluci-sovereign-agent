# backend/core/startup_checks.py
import os
import sys
from dotenv import load_dotenv

load_dotenv(override=True)

FORBIDDEN_SECRET_VALUES = {
    "testing_csrf_key_auto_generated",
    "change_me",
    "secret",
    "your-secret-here",
    "",
}

KNOWN_VALID_MODEL_IDS = {
    "gemini-3.0-flash", # Leaving for now as per previous context if needed, but spec says 2.0
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
}

def assert_secrets_are_set() -> None:
    """
    Called from app lifespan at startup.
    Raises SystemExit if any critical secret is missing or set to a known-bad value.
    """
    checks = {
        "POLYTOPE_MASTER_KEY": os.getenv("POLYTOPE_MASTER_KEY", ""),
        "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", ""),
        "CSRF_SECRET_KEY": os.getenv("CSRF_SECRET_KEY", ""),
        "DB_PASSWORD": os.getenv("DB_PASSWORD", ""),
    }

    errors: list[str] = []
    for key, value in checks.items():
        if not value or value in FORBIDDEN_SECRET_VALUES:
            errors.append(f"  - {key} is missing or set to a known-insecure placeholder value.")

    if errors:
        print("\n\033[91mFATAL: Refusing to start with insecure configuration:\033[0m", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        
        print("\n\033[1m[REPARATION HINT]\033[0m", file=sys.stderr)
        print("To fix this, add the missing keys to your \033[1m.env\033[0m file or export them locally.", file=sys.stderr)
        print("Example: \033[92mexport CSRF_SECRET_KEY=$(openssl rand -hex 32)\033[0m", file=sys.stderr)
        print("Or use: \033[92mmake init\033[0m to generate a standard template.\n", file=sys.stderr)
        sys.exit(1)

def warn_on_stale_model_ids() -> None:
    """
    Logs a warning if configured model IDs are not in the known-valid set.
    Does NOT raise — model availability can change; this is advisory only.
    """
    import logging
    logger = logging.getLogger(__name__)

    model_ids_to_check = [
        os.getenv("VITE_DEFAULT_MODEL", ""),
    ]

    for model_id in filter(None, model_ids_to_check):
        if model_id not in KNOWN_VALID_MODEL_IDS:
            logger.warning(
                "Model ID '%s' is not in the known-valid set. "
                "Verify it exists in your provider's API before deployment. "
                "Update KNOWN_VALID_MODEL_IDS in startup_checks.py if this is intentional.",
                model_id,
            )
