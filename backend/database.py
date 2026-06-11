import os
from sqlmodel import create_engine, SQLModel, Session
from .config import settings
from .logging_config import get_logger

logger = get_logger("Database")

# Configurable database URL from settings.
# For Production: use "postgresql://user:pass@host/dbname" (via psycopg2)
# For Performance: the app supports sync drivers primarily; asyncpg is reserved for high-concurrency extensions.
db_url = settings.DATABASE_URL

# Handle asyncpg URLs by converting them to sync for the main SQLModel engine
if db_url.startswith("postgresql+asyncpg://"):
    logger.info("Converting asyncpg URL to sync for SQLModel engine compatibility.")
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

connect_args = {}
if "sqlite" in db_url:
    connect_args["check_same_thread"] = False

from sqlalchemy.pool import StaticPool

from typing import Any

# Create the primary sync engine
if "sqlite" in db_url:
    engine_kwargs: dict[str, Any] = {
        "connect_args": connect_args,
        "pool_pre_ping": True,
        "echo": False,
    }
    if db_url == "sqlite:///:memory:":
        engine_kwargs["poolclass"] = StaticPool
        
    engine = create_engine(
        db_url,
        **engine_kwargs
    )
else:
    # Production pooling for Postgres
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo=False,
    )

def _enable_wal_mode():
    """Enable Write-Ahead Logging for SQLite — crucial for concurrent bridge activity."""
    if "sqlite" in db_url:
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
                conn.exec_driver_sql("PRAGMA busy_timeout=5000;")
                conn.commit()
            logger.debug("SQLite WAL mode enabled.")
        except Exception as e:
            logger.warning(f"Failed to enable WAL mode: {e}")

def apply_sqlite_migrations():
    """
    Runs raw SQL migration scripts for SQLite (e.g., FTS5) that Alembic
    cannot easily manage without manual intervention.
    """
    if "sqlite" not in db_url:
        return

    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations/raw_sql")
    if not os.path.exists(migrations_dir):
        logger.debug(f"Target raw SQL migration directory not found: {migrations_dir}")
        return

    # Sort files to ensure deterministic execution order
    sql_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
    if not sql_files:
        return

    logger.info(f"Applying {len(sql_files)} raw SQL migrations to SQLite...")
    with engine.connect() as conn:
        for sql_file in sql_files:
            file_path = os.path.join(migrations_dir, sql_file)
            try:
                with open(file_path, "r") as f:
                    sql_script = f.read()
                
                # SQLite/SQLAlchemy exec_driver_sql only allows one statement.
                # We split by semicolon and execute each non-empty part.
                statements = [s.strip() for s in sql_script.split(";") if s.strip()]
                for stmt in statements:
                    conn.exec_driver_sql(stmt)
                
                conn.commit()
                logger.info(f"  Applied: {sql_file}")
            except Exception as e:
                logger.error(f"  Failed to apply raw migration {sql_file}: {e}")
                # We continue to next file as these are usually idempotent CREATE IF NOT EXISTS

def create_db_and_tables():
    """
    Initializes the database schema and performs environment-specific tuning.
    
    [ GAP-001 ] This function is guarded in production. Schema changes in production
    MUST be handled via Alembic migrations (backend/migrations).
    """
    if settings.APP_ENV == "production":
        logger.warning("create_db_and_tables() ignored in PRODUCTION. Use Alembic migrations.")
        # We still perform performance tuning (WAL mode)
        _enable_wal_mode()
        return

    _enable_wal_mode()
    
    # FTS5 is required even if table already exists (CREATE VIRTUAL TABLE IF NOT EXISTS)
    apply_sqlite_migrations()
    logger.info("Database initialization complete.")

def get_session():
    """Context manager for database sessions. Used as a FastAPI dependency."""
    with Session(engine) as session:
        yield session
