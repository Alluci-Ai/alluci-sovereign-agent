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

# Create the primary sync engine
if "sqlite" in db_url:
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        echo=False,
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

def create_db_and_tables():
    """Initializes the database schema and performs environment-specific tuning."""
    SQLModel.metadata.create_all(engine)
    _enable_wal_mode()

def get_session():
    """Context manager for database sessions. Used as a FastAPI dependency."""
    with Session(engine) as session:
        yield session
