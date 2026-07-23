# backend/core/startup_checks.py
import os
import sys
from dotenv import load_dotenv

# Prevent overriding test environment variables during test suite execution
override = os.environ.get("APP_ENV") != "testing"
load_dotenv(override=override)

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
    }
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url.startswith("sqlite"):
        checks["DB_PASSWORD"] = os.getenv("DB_PASSWORD", "")

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

def seed_rocco_agent() -> None:
    """
    Ensures the user's configured Rocco agent has deep research tools enabled,
    and removes any legacy auto-seeded 'rocco' duplicate.
    """
    import json
    from sqlmodel import Session, select
    from ..database import engine
    from ..models import AgentRecord

    research_tools = {
        "deep_research_query_expansion": {"enabled": True},
        "deep_research_harvest": {"enabled": True},
        "deep_research_evaluate": {"enabled": True}
    }

    with Session(engine) as session:
        # Delete duplicate id="rocco" if a custom Rocco agent exists
        custom_rocco = session.get(AgentRecord, "a32eb383")
        if not custom_rocco:
            stmt = select(AgentRecord).where(AgentRecord.name.ilike("%rocco%"), AgentRecord.id != "rocco")
            custom_rocco = session.exec(stmt).first()

        dup_rocco = session.get(AgentRecord, "rocco")
        if dup_rocco and custom_rocco:
            session.delete(dup_rocco)
            session.commit()
            import logging
            logging.getLogger(__name__).info("Removed duplicate 'rocco' agent record from database.")

        target_agent = custom_rocco or dup_rocco
        if not target_agent:
            target_agent = AgentRecord(
                id="a32eb383",
                name="Rocco",
                status="active",
                description="Deep Research Agent",
                model="local/alluci-polytope-gemma-4-31b-it-bf16",
                system_prompt="You are Rocco, an advanced deep research agent. Your sole purpose is to execute comprehensive research workflows, gather extensive data from the web, evaluate findings, and synthesize detailed reports.",
                tools_manifest=json.dumps(research_tools)
            )
            session.add(target_agent)
            session.commit()
        else:
            manifest = {}
            if target_agent.tools_manifest:
                try:
                    manifest = json.loads(target_agent.tools_manifest)
                except Exception:
                    manifest = {}
            updated = False
            for tool, config in research_tools.items():
                if tool not in manifest or not manifest[tool].get("enabled"):
                    manifest[tool] = config
                    updated = True
            
            if updated:
                target_agent.tools_manifest = json.dumps(manifest)
                session.add(target_agent)
                session.commit()
