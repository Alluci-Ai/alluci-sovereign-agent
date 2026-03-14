"""
Alembic environment configuration for Polytope Sovereign OS.
Reads DATABASE_URL from the app's config and uses SQLModel metadata
for autogenerate support.
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Ensure the project root is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- SQLModel / Application Integration ---
from sqlmodel import SQLModel  # noqa: E402
from backend.config import load_settings  # noqa: E402
from backend import models  # noqa: F401, E402 — force models to register with SQLModel metadata

app_settings = load_settings()

# Point Alembic at SQLModel's metadata for autogenerate support
target_metadata = SQLModel.metadata

def get_url() -> str:
    """Retrieves the sync-compatible database URL for Alembic."""
    url = app_settings.DATABASE_URL
    # Ensure synchronous driver is used for migrations (SQLModel/SQLAlchemy sync engine)
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://")
    return url

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = get_url()
    is_sqlite = "sqlite" in url
    
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=is_sqlite,  # Only use batch for SQLite
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode with a live connection."""
    url = get_url()
    is_sqlite = "sqlite" in url
    
    # We create a sync engine for the migration runner
    from sqlalchemy import create_engine
    connectable = create_engine(url)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,  # Only use batch for SQLite
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
