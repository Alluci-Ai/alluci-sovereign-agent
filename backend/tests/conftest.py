"""
Production-grade pytest configuration and fixtures for the Alluci Sovereign Agent.

Provides:
- Isolated per-test SQLite databases (no shared state between tests)
- Authenticated test clients (JWT token pre-injected)
- Mock LLM router with configurable response behavior
- Vault instances with deterministic test keys
- Seeded database fixtures (runs, tasks, task records)
"""
import os
import sys
import json
import asyncio
import tempfile
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from typing import Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from cryptography.fernet import Fernet
from starlette.requests import Request
from starlette.responses import Response

# CRITICAL: Set environment variables BEFORE any backend modules are imported
# so that module-level Pydantic settings evaluation captures the test values.
os.environ["APP_ENV"] = "testing"
os.environ["CSRF_SECRET_KEY"] = "test-csrf-secret-key-12345678"
os.environ["POLYTOPE_MASTER_KEY"] = "test-polytope-master-key"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-12345678"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Ensure backend importable from test runner
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Test Environment Variables ──────────────────────────────────────────────
os.environ.update({
    "APP_ENV":               "testing",
    "POLYTOPE_MASTER_KEY":   Fernet.generate_key().decode(),
    "JWT_SECRET_KEY":        "test-jwt-secret-do-not-use-in-production-32chars",
    "GEMINI_API_KEY":        "test-gemini-key-placeholder",
    "DATABASE_URL":          "sqlite:///./test_polytope.db",
    "OTEL_SDK_DISABLED":     "true",
    "RATE_LIMIT_PER_MINUTE": "9999",    # Disable rate limits in tests
    "VERUS_AUTH_ENABLED":    "false",
})

# Configure structured logging for tests so they use standard logging handlers
from backend.logging_config import configure_logging
configure_logging(app_env="testing")

# SEC-001: Initialize mock JWT keys for tests
from backend.security.auth import init_jwt_keys
# Use a dummy but valid RSA private/public key pair (or mock them if possible, 
# but init_jwt_keys expects strings/bytes that look like keys or actual key objects)
# For now, let's just use some dummy strings if the security/auth.py handles it,
# or better yet, generate a small one.
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

_test_priv_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_test_pub_key = _test_priv_key.public_key()

_priv_pem = _test_priv_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode()

_pub_pem = _test_pub_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode()

init_jwt_keys(_test_priv_key, _test_pub_key)


# ══════════════════════════════════════════════════════════════════════════════
# DATABASE FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="function")
def temp_db():
    """
    Provides an isolated SQLite database per test function.
    All tables are created fresh and torn down after each test.
    This ensures complete test isolation — no shared state.
    """
    from sqlmodel import create_engine, SQLModel
    import backend.models  # Register all models with metadata
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    
    # Patch all direct module lookups to db_engine
    with patch("backend.database.engine", engine, create=True), \
         patch("backend.routers.system.db_engine", engine, create=True), \
         patch("backend.routers.objectives.db_engine", engine, create=True), \
         patch("backend.routers.dag.db_engine", engine, create=True), \
         patch("backend.routers.sessions.db_engine", engine, create=True), \
         patch("backend.security.audit_ledger.db_engine", engine, create=True), \
         patch("backend.goals.engine.db_engine", engine, create=True), \
         patch("backend.sop.engine.db_engine", engine, create=True), \
         patch("backend.device_manager.db_engine", engine, create=True), \
         patch("backend.orchestrator.db_engine", engine, create=True), \
         patch("backend.models.engine", engine, create=True):
        yield engine

    os.unlink(db_path)


@pytest.fixture(scope="function")
def db_session(temp_db):
    """Provides a live Session bound to the per-test database."""
    from sqlmodel import Session
    with Session(temp_db) as session:
        yield session


# ══════════════════════════════════════════════════════════════════════════════
# SETTINGS & CONFIG FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def mock_settings():
    """
    Provides a fully-populated mock Settings object.
    Session-scoped: shared across all tests to avoid repeated construction.
    """
    settings = MagicMock()
    settings.APP_ENV = "testing"
    settings.POLYTOPE_MASTER_KEY = os.environ["POLYTOPE_MASTER_KEY"]
    settings.JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
    settings.CSRF_SECRET_KEY = "dummy-csrf-secret-key-for-tests-12345"
    settings.GEMINI_API_KEY = "test-gemini-key"
    settings.OPENAI_API_KEY = None
    settings.ANTHROPIC_API_KEY = None
    settings.GROQ_API_KEY = None
    settings.DEEPSEEK_API_KEY = None
    settings.VERUS_AUTH_ENABLED = False
    settings.VERUS_ID_IDENTITY = None
    settings.VERUS_ID_PRIVATE_KEY = None
    settings.HOST = "0.0.0.0"
    settings.PORT = 8000
    settings.ALLOWED_ORIGINS = ["http://localhost:3000", "http://localhost:5173"]
    settings.MAX_AUTONOMY_RETRIES = 3
    settings.CRITIC_THRESHOLD = 0.75
    settings.MAX_CONTEXT_TOKENS = 8000
    settings.MAX_CONCURRENT_TASKS = 5
    settings.RATE_LIMIT_PER_MINUTE = 9999
    settings.DATABASE_URL = "sqlite:///./test_polytope.db"
    settings.AUTH_COOKIE_NAME = "alluci_daemon_token"
    settings.AUTH_COOKIE_SECURE = False
    settings.AUTH_COOKIE_HTTPONLY = True
    settings.VERUS_RPC_HOST = "127.0.0.1"
    settings.VERUS_RPC_PORT = 27486
    settings.WEBAUTHN_RP_ID = "localhost"
    settings.WEBAUTHN_RP_NAME = "Alluci Sovereign Agent"
    settings.WEBAUTHN_ORIGIN = "http://localhost:3000"
    return settings


# ══════════════════════════════════════════════════════════════════════════════
# LLM ROUTER FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def mock_router():
    """
    Mock ModelRouter that returns deterministic responses without making
    real LLM API calls. Suitable for testing engine logic in isolation.
    """
    router = AsyncMock()
    router.get_response = AsyncMock(return_value="This is a test response.")
    router.get_structured_plan = AsyncMock(return_value={
        "steps": [
            {
                "id": "step_1",
                "tool": "system_query",
                "description": "Gather initial information",
                "dependencies": []
            },
            {
                "id": "step_2",
                "tool": "summarize",
                "description": "Summarize gathered information",
                "dependencies": ["step_1"]
            }
        ]
    })
    router.critique_result = AsyncMock(return_value={
        "score": 0.88,
        "feedback": "Execution completed successfully. All objectives met."
    })
    router.refine_plan = AsyncMock(return_value={
        "steps": [
            {
                "id": "step_1_refined",
                "tool": "system_query",
                "description": "Refined step",
                "dependencies": []
            }
        ]
    })
    router.check_health = AsyncMock(return_value={"gemini": "ok", "openai": "unavailable"})
    return router

@pytest.fixture
def mock_adapter_registry():
    """Mock adapter registry for resolving tools during execution tests."""
    registry = MagicMock()
    # By default, any adapter requested will just return a mock adapter
    mock_adapter = MagicMock()
    mock_adapter.execute = AsyncMock(return_value="adapter output")
    registry.get.return_value = mock_adapter
    return registry


@pytest.fixture
def failing_router():
    """
    Mock router that simulates LLM API failures for testing error handling
    and failover behavior.
    """
    router = AsyncMock()
    router.get_response = AsyncMock(side_effect=Exception("LLM API timeout"))
    router.get_structured_plan = AsyncMock(side_effect=Exception("LLM API timeout"))
    router.critique_result = AsyncMock(side_effect=Exception("LLM API timeout"))
    router.get_fast_tactical_response = AsyncMock(side_effect=Exception("LLM API timeout"))
    return router


@pytest.fixture
def low_score_router():
    """
    Mock router that returns below-threshold critic scores to test
    retry and refinement logic.
    """
    router = AsyncMock()
    router.get_response = AsyncMock(return_value="Incomplete response.")
    router.get_structured_plan = AsyncMock(return_value={
        "steps": [{"id": "s1", "tool": "search", "description": "Search", "dependencies": []}]
    })
    router.critique_result = AsyncMock(return_value={
        "score": 0.45,
        "feedback": "Objective not fully achieved. Key information missing."
    })
    return router


# ══════════════════════════════════════════════════════════════════════════════
# VAULT FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def temp_vault():
    """
    Provides a VaultManager instance with a fresh temporary directory.
    Uses a deterministic test key for reproducibility.
    """
    key = Fernet.generate_key().decode()
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("backend.security.vault.settings") as mock_s:
            mock_s.VERUS_AUTH_ENABLED = False
            from backend.security.vault import VaultManager
            yield VaultManager(key, vault_root=tmpdir)


# ══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATED HTTP CLIENT FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def app_client(mock_settings, temp_db):
    """
    TestClient with all global services mocked and a fresh DB per test.
    The client is pre-configured to work without real API keys.
    """
    from fastapi.testclient import TestClient
    import backend.services as services

    with patch("backend.config.load_settings", return_value=mock_settings):

        from backend.app import app
        from backend.security.auth import init_jwt_keys
        from cryptography.hazmat.primitives.asymmetric import rsa
        
        # Initialize RS256 keys for testing
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        init_jwt_keys(private_key, public_key)

        # Inject mocked services
        services.vault = MagicMock()
        services.vault.retrieve_secret = AsyncMock(return_value={})
        services.vault.store_secret = AsyncMock()
        services.vault.get_active_vaults = MagicMock(return_value=set())
        services.vault.delete_secret = AsyncMock(return_value=True)
        services.vault.rotate_keys = AsyncMock(return_value=True)
        services.vault.flush_cache = AsyncMock()
        services.vault.update_vault_status = AsyncMock()

        services.router = MagicMock()
        services.router.router = MagicMock()
        services.router.router.providers = {}
        services.router.get_response = AsyncMock(return_value="Test response")
        services.router.get_structured_plan = AsyncMock(return_value={
            "steps": [{"id": "s1", "tool": "search", "description": "Test", "dependencies": []}]
        })
        services.router.critique_result = AsyncMock(return_value={"score": 0.9, "feedback": "Good"})
        services.router.check_health = AsyncMock(return_value={"gemini": "ok"})
        services.router.get_fast_tactical_response = AsyncMock(return_value="safe")

        from backend.security.guardrail import GuardrailScanner
        services.scanner = GuardrailScanner(router=services.router)

        services.ace = MagicMock()
        services.ace.process_telemetry = MagicMock(return_value={"mode": "STANDARD", "reason": "Test"})
        services.ace.compute_psi = MagicMock(return_value=1.5)

        mock_orch = AsyncMock()
        mock_orch.execute_objective = AsyncMock(return_value={
            "run_id": 1, "status": "completed", "task_count": 2, "result": "Done."
        })
        mock_orch.preview_plan = AsyncMock(return_value=[
            {"id": "s1", "action": "search", "description": "Search step", "dependencies": []}
        ])
        mock_orch.cancel_run = AsyncMock(return_value=True)
        services.orchestrator = mock_orch

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as tf:
            tf.write("- [ ] Test task\n")
            tasks_path = tf.name

        from backend.tasks import TaskManager
        services.task_manager = TaskManager(filepath=tasks_path)
        services.skill_manager = MagicMock()
        services.skill_manager.list_skills = MagicMock(return_value=[])
        
        services.usage_tracker = MagicMock()
        services.usage_tracker.get_sessions = MagicMock(return_value=[])
        
        services.cron_engine = MagicMock()
        services.cron_engine.list_jobs = MagicMock(return_value=[])
        
        services.channel_registry = {}
        
        services.config_editor = MagicMock()
        services.config_editor.read_config = MagicMock(return_value={})
        
        services.exec_approval = AsyncMock()
        services.exec_approval.get_pending = AsyncMock(return_value=[])

        mock_csrf = MagicMock()
        mock_csrf.validate_csrf = AsyncMock()
        from fastapi_csrf_protect import CsrfProtect
        app.dependency_overrides[CsrfProtect] = lambda: mock_csrf

        # Bypass RateLimiter since lifespan isn't run for TestClient
        async def mock_rate_limit(self, request: Request, response: Response):
            pass
            
        with patch('fastapi_limiter.depends.RateLimiter.__call__', new=mock_rate_limit):
            client = TestClient(app, raise_server_exceptions=True)
            
            from itsdangerous import URLSafeTimedSerializer
            serializer = URLSafeTimedSerializer("test-csrf-secret-key-12345678", salt="fastapi-csrf-token")
            token = "test-token"
            signed_token = serializer.dumps(token)
            
            # The cookie name we fixed to cookie_key in csrf.py is AUTH_COOKIE_NAME but the fastAPI csrf default is 'fastapi-csrf-token'
            # Let's set both to be safe, but actually our settings override it to settings.AUTH_COOKIE_NAME which is 'alluci_daemon_token'
            client.cookies.set("alluci_daemon_token", signed_token)
            client.headers["X-CSRF-Token"] = token
            
            yield client
            
        app.dependency_overrides.pop(CsrfProtect, None)

        os.unlink(tasks_path)


@pytest.fixture
def auth_headers(app_client, mock_settings):
    """
    Returns Authorization headers for a valid authenticated session.
    Use this in tests that require authentication.
    """
    response = app_client.post(
        "/api/v1/auth/login",
        json={"key": mock_settings.POLYTOPE_MASTER_KEY}
    )
    assert response.status_code == 200, f"Auth failed: {response.text}"
    token = response.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "X-CSRF-Token": "test-token"  # Matches the token in app_client
    }


# ══════════════════════════════════════════════════════════════════════════════
# SEEDED DATA FIXTURES
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def seed_run(db_session):
    """Creates a single completed Run record and returns its ID."""
    from backend.models import Run, RunStatus
    run = Run(
        objective="Test objective: summarize quarterly earnings",
        status="completed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run.id


@pytest.fixture
def seed_failed_run(db_session):
    """Creates a failed Run record for testing cancel/retry paths."""
    from backend.models import Run
    run = Run(
        objective="Test failed objective",
        status="failed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run.id


@pytest.fixture
def seed_run_with_tasks(db_session):
    """Creates a Run with 3 TaskRecord entries (mixed statuses)."""
    from backend.models import Run, TaskRecord
    run = Run(
        objective="Multi-task test objective",
        status="completed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    for i, (dag_id, status) in enumerate([
        ("task_search", "completed"),
        ("task_analyze", "completed"),
        ("task_report", "failed"),
    ]):
        record = TaskRecord(
            run_id=run.id,
            task_dag_id=dag_id,
            action=f"action_{i}",
            args=json.dumps({"description": f"Task {i}", "dependencies": []}),
            status=status,
            result=f"Result {i}" if status == "completed" else None,
            error="Timeout" if status == "failed" else None,
        )
        db_session.add(record)

    db_session.commit()
    return run.id, 3
