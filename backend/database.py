import os
from sqlmodel import create_engine, SQLModel, Session
from .config import load_settings

settings = load_settings()

# Configurable database URL from settings
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

# Enable WAL mode for better concurrent read performance
def _enable_wal_mode():
    """Enable Write-Ahead Logging for SQLite — allows concurrent readers."""
    if "sqlite" in settings.DATABASE_URL:
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
            conn.exec_driver_sql("PRAGMA busy_timeout=5000;")
            conn.commit()

def create_db_and_tables():
    """Initializes the database schema and enables WAL mode."""
    SQLModel.metadata.create_all(engine)
    _enable_wal_mode()

def get_session():
    """Dependency for database sessions."""
    with Session(engine) as session:
        yield session
