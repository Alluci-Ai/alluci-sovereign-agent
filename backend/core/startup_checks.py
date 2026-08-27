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
    from sqlmodel import Session, select, col
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
            stmt = select(AgentRecord).where(col(AgentRecord.name).ilike("%rocco%"), AgentRecord.id != "rocco")
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


def seed_codi_agent() -> None:
    """
    [ PPN-036 ] Ensures the Sovereign Codi Autonomous Software Engineering Agent is seeded
    in SQLite agent_record with OpenCode harness bindings, AST diff tools, and local MLX model.
    """
    import json
    from datetime import datetime, timezone
    from sqlmodel import Session, select
    from ..database import engine
    from ..models import AgentRecord, AgentSkillBinding

    codi_tools = {
        "codi_tool_01": {"enabled": True, "params": "{\n  \n}"},
        "opencode_ast_diff": {"enabled": True},
        "opencode_lsp_diagnose": {"enabled": True},
        "opencode_test_runner": {"enabled": True},
        "sovereign_checkpoint_create": {"enabled": True},
        "sovereign_checkpoint_rollback": {"enabled": True}
    }

    codi_skills = {
        "codi_01": {"enabled": True},
        "auth_01": {"enabled": True},
        "ws_01": {"enabled": True},
        "msg_01": {"enabled": True}
    }

    engine_manifest = {
        "llm": [
            "local/GLM-4-32B-0414-4bit",
            "local/alluci-polytope-gemma-4-31b-it-bf16",
            "local/GLM-4.7-4bit"
        ]
    }

    with Session(engine) as session:
        codi_agent = session.get(AgentRecord, "codi")
        if not codi_agent:
            codi_agent = AgentRecord(
                id="codi",
                name="Codi",
                status="ACTIVE",
                description="Autonomous Software Engineer & Codebase Refactoring Sub-Agent powered by OpenCode harness",
                model="local/GLM-4-32B-0414-4bit",
                fallback_chain="local/alluci-polytope-gemma-4-31b-it-bf16,local/alluci-polytope-gemma-4-26b-a4b-it-4bit",
                system_prompt=(
                    "[SYSTEM PROMPT DNA: CODI AUTONOMOUS SOFTWARE ENGINEER & OPENCODE HARNESS]\n\n"
                    "ROLE DEFINITION:\n"
                    "You are Codi (agent_id=\"codi\"), the dedicated Sovereign Software Engineering and Codebase Refactoring Sub-Agent "
                    "within the Alluci Sovereign Agent constellation. You leverage the local OpenCode Headless Engine and on-device Apple MLX "
                    "Local Cognitive Engine with zero cloud dependencies and zero external network egress.\n\n"
                    "NON-NEGOTIABLE SOVEREIGN ENGINEERING LAWS:\n"
                    "1. ZERO-STUB & REAL END-TO-END WIRING LAW: NO stubs, NO mocks, NO simulated responses, NO partial scaffolding, and NO dummy fallbacks. "
                    "Every feature, API route, database query, security guard, and React component MUST be 100% complete, fully implemented, and wired end-to-end.\n"
                    "2. ANTI-MONKEY-PATCH & AUTHORITATIVE ROOT-CAUSE LAW: NO dynamic monkey-patching, NO superficial band-aids, NO unittest.mock in production code. "
                    "Always fix root-cause architecture in the authoritative source file.\n"
                    "3. DEFENSIVE TYPE SAFETY & NON-NULL CONTRACTS: Verify non-null state before dereferencing. Enforce strict Pydantic v2 schemas and TypeScript interfaces.\n"
                    "4. ATOMIC PRE-STATE CHECKPOINTING & ROLLBACK: Always create an atomic pre-state checkpoint before mutating filesystem state. Generate exact reverse patch diffs for 1-click rollback.\n"
                    "5. HITL EXECUTIVE GOVERNANCE: All destructive operations, file writes, and test executions must be gated by explicit sovereign HITL authorization."
                ),
                engine_manifest=json.dumps(engine_manifest),
                tools_manifest=json.dumps(codi_tools),
                skills_manifest=json.dumps(codi_skills),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            session.add(codi_agent)
            session.commit()
            import logging
            logging.getLogger(__name__).info("[ Constellation ] Seeded Sovereign Codi Sub-Agent (id='codi').")
        else:
            manifest = {}
            if codi_agent.tools_manifest:
                try:
                    manifest = json.loads(codi_agent.tools_manifest)
                except Exception:
                    manifest = {}
            updated = False
            for tool, config in codi_tools.items():
                if tool not in manifest or not manifest[tool].get("enabled"):
                    manifest[tool] = config
                    updated = True
            
            if codi_agent.status != "ACTIVE":
                codi_agent.status = "ACTIVE"
                updated = True

            if not codi_agent.engine_manifest:
                codi_agent.engine_manifest = json.dumps(engine_manifest)
                updated = True

            if not codi_agent.skills_manifest:
                codi_agent.skills_manifest = json.dumps(codi_skills)
                updated = True

            if updated:
                codi_agent.tools_manifest = json.dumps(manifest)
                codi_agent.updated_at = datetime.now(timezone.utc)
                session.add(codi_agent)
                session.commit()

        # Ensure AgentSkillBindings exist for Codi
        for skill_id in codi_skills.keys():
            existing = session.exec(
                select(AgentSkillBinding).where(
                    AgentSkillBinding.agent_id == "codi",
                    AgentSkillBinding.skill_id == skill_id
                )
            ).first()
            if not existing:
                session.add(AgentSkillBinding(agent_id="codi", skill_id=skill_id))
        session.commit()

