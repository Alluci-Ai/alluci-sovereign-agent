"""
Pytest configuration and shared fixtures for the Polytope backend test suite.
"""
import os
import sys
import pytest
import tempfile
from unittest.mock import AsyncMock, MagicMock

# Ensure backend is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set dummy environment variables to pass Pydantic validation during test collection
os.environ["POLYTOPE_MASTER_KEY"] = "dGVzdC1rZXktZm9yLXVuaXQtdGVzdGluZw=="
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-for-unit-tests"
os.environ["GEMINI_API_KEY"] = "test-gemini-key"
os.environ["APP_ENV"] = "testing"


# --- Fixtures: Database ---

@pytest.fixture
def temp_db():
    """Provides a temporary SQLite database for testing."""
    from sqlmodel import create_engine, SQLModel
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    
    yield engine
    
    os.unlink(db_path)


@pytest.fixture
def db_session(temp_db):
    """Provides a database session for testing."""
    from sqlmodel import Session
    with Session(temp_db) as session:
        yield session


# --- Fixtures: Settings ---

@pytest.fixture
def mock_settings():
    """Provides mock settings that don't require real API keys."""
    settings = MagicMock()
    settings.POLYTOPE_MASTER_KEY = "dGVzdC1rZXktZm9yLXVuaXQtdGVzdGluZw=="  # base64 test key
    settings.JWT_SECRET_KEY = "test-jwt-secret-key-for-unit-tests"
    settings.GEMINI_API_KEY = "test-gemini-key"
    settings.OPENAI_API_KEY = None
    settings.ANTHROPIC_API_KEY = None
    settings.APP_ENV = "development"
    settings.HOST = "0.0.0.0"
    settings.PORT = 8000
    settings.ALLOWED_ORIGINS = ["http://localhost:3000"]
    settings.MAX_AUTONOMY_RETRIES = 3
    settings.CRITIC_THRESHOLD = 0.75
    settings.MAX_CONCURRENT_TASKS = 5
    settings.RATE_LIMIT_PER_MINUTE = 60
    settings.DATABASE_URL = "sqlite:///test.db"
    settings.VERUS_ID_IDENTITY = None
    settings.VERUS_ID_PRIVATE_KEY = None
    return settings


# --- Fixtures: Mock Router ---

@pytest.fixture
def mock_router():
    """Provides a mock ModelRouter for testing without real API calls."""
    router = AsyncMock()
    router.get_response = AsyncMock(return_value="Test response.")
    router.get_structured_plan = AsyncMock(return_value={
        "steps": [
            {"id": "step_1", "description": "Test step 1", "tool": "system_query", "dependencies": []},
            {"id": "step_2", "description": "Test step 2", "tool": "summarize", "dependencies": ["step_1"]}
        ]
    })
    router.critique_result = AsyncMock(return_value={"score": 0.85, "feedback": "Good result."})
    router.refine_plan = AsyncMock(return_value={"steps": []})
    return router


# --- Fixtures: Vault ---

@pytest.fixture
def temp_vault():
    """Provides a VaultManager with a temporary vault directory."""
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        from backend.security.vault import VaultManager
        yield VaultManager(key, vault_root=tmpdir)


# --- Fixtures: Task Manager ---

@pytest.fixture
def temp_task_file():
    """Provides a temporary TASKS.md file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write("# Tasks\n")
        f.write("- [ ] [HIGH] Fix critical bug (due: 2024-01-15)\n")
        f.write("- [x] [MEDIUM] Write documentation\n")
        f.write("- [ ] [URGENT] Deploy to production (due: 2099-12-31)\n")
        f.write("- [ ] [LOW] Refactor code\n")
        path = f.name
    
    yield path
    os.unlink(path)


# --- Fixtures: Adapter Registry ---

@pytest.fixture
def mock_adapter_registry():
    """Provides a mock AdapterRegistry with test adapters."""
    registry = MagicMock()
    
    mock_adapter = AsyncMock()
    mock_adapter.execute = AsyncMock(return_value="Adapter result")
    
    registry.get = MagicMock(return_value=mock_adapter)
    registry.list_tools = MagicMock(return_value=["filesystem", "system_query"])
    return registry


# --- End of tests ---
