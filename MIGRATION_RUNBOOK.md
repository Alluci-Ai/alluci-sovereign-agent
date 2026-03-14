# Database Migration Runbook

This guide outlines the process for managing database schema changes and migrating between **SQLite** (Development) and **PostgreSQL** (Production).

## 1. Overview
The Alluci Sovereign Agent uses **SQLModel** (SQLAlchemy + Pydantic) for its ORM and **Alembic** for schema migrations. 

- **Development**: Uses SQLite by default (`polytope_data.db`).
- **Production**: Requires PostgreSQL. The app enforces this in `config.py` when `APP_ENV=production`.

## 2. Setting Up Migrations (Initial)
If the `migrations/` directory is missing or you are starting fresh:
```bash
cd backend
alembic init migrations
```
*Note: The project already includes a pre-configured `backend/alembic.ini` and `backend/migrations/env.py`.*

## 3. Creating a New Migration
When you modify `backend/models.py`, you must generate a new migration script:

```bash
cd backend
export PYTHONPATH=$PYTHONPATH:..
alembic revision --autogenerate -m "description_of_change"
```

Inspect the generated file in `backend/migrations/versions/` before applying it.

## 4. Applying Migrations
To apply the latest migrations to your configured database:

```bash
cd backend
export PYTHONPATH=$PYTHONPATH:..
alembic upgrade head
```

## 5. SQLite to PostgreSQL Migration
### A. Migration to Production (PostgreSQL)
1. Set up your PostgreSQL instance (e.g., via `docker-compose up -d db`).
2. Set your production environment variables:
   ```bash
   APP_ENV=production
   PROD_DATABASE_URL=postgresql+psycopg2://user:password@host:port/dbname
   ```
3. Run the migrations against the new production database:
   ```bash
   cd backend
   export PYTHONPATH=$PYTHONPATH:..
   alembic upgrade head
   ```
4. (Optional) If you need to move data from SQLite to PostgreSQL, use a tool like `pgloader` or export/import via CSV/JSON. **Alembic does not sync data, only schema.**

### B. Production Driver Optimization
While migrations use the sync `psycopg2` driver, the application can use the async `asyncpg` driver for better performance. 

To use async in production, set:
`PROD_DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname`

Alembic's `env.py` is configured to automatically strip the `+asyncpg` suffix to ensure migration compatibility.

## 6. Common Commands
- **Check current version**: `alembic current`
- **View history**: `alembic history --verbose`
- **Rollback one step**: `alembic downgrade -1`
- **Rollback to base**: `alembic downgrade base`

## 7. Troubleshooting
- **IsSQLite Error**: If a migration fails with "batch mode" errors on PostgreSQL, ensure `render_as_batch=False` is set in `env.py` (our `env.py` handles this automatically).
- **PYTHONPATH Issues**: Always ensure the root directory is on your `PYTHONPATH` so Alembic can find the `backend` module.
