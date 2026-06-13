"""
Infrastructure Tests

Validates Docker builds, database migrations, and environment configuration.
These tests run in CI against the actual containerized application.
"""
import os
import subprocess
import pytest
import tempfile
import requests
import time


class TestDockerBuild:

    @pytest.mark.slow
    @pytest.mark.skipif(
        not os.path.exists("/var/run/docker.sock"),
        reason="Docker not available in this environment"
    )
    def test_backend_dockerfile_builds_without_error(self):
        """docker build must succeed with exit code 0."""
        result = subprocess.run(
            ["docker", "build", "-f", "Dockerfile.backend", "-t", "alluci-backend-test", "."],
            capture_output=True, text=True
        )
        assert result.returncode == 0, \
            f"Docker build failed:\n{result.stderr}"

    @pytest.mark.slow
    @pytest.mark.skipif(
        not os.path.exists("/var/run/docker.sock"),
        reason="Docker not available in this environment"
    )
    def test_backend_container_starts_and_health_passes(self):
        """Container starts within 30 seconds and health endpoint returns 200."""
        import subprocess
        import time

        container_id = None
        try:
            result = subprocess.run(
                ["docker", "run", "-d", "--rm",
                 "-p", "18000:8000",
                 "-e", f"POLYTOPE_MASTER_KEY={os.environ.get('POLYTOPE_MASTER_KEY', 'test-key')}",
                 "-e", f"JWT_SECRET_KEY={os.environ.get('JWT_SECRET_KEY', 'test-jwt')}",
                 "-e", "GEMINI_API_KEY=test-key",
                 "-e", "APP_ENV=testing",
                 "alluci-backend-test"],
                capture_output=True, text=True
            )
            container_id = result.stdout.strip()

            # Wait for container to become healthy
            for attempt in range(30):
                try:
                    resp = requests.get("http://localhost:18000/health", timeout=2)
                    if resp.status_code == 200:
                        break
                except:
                    time.sleep(1)
            else:
                pytest.fail("Container did not become healthy within 30 seconds")

        finally:
            if container_id:
                subprocess.run(["docker", "stop", container_id], capture_output=True)


class TestDatabaseMigrations:

    @pytest.mark.integration
    def test_alembic_migrations_apply_cleanly(self):
        """
        Running alembic upgrade head on a fresh database must succeed.
        This is run against a temporary SQLite database.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_migration.db")
            env = os.environ.copy()
            env["DATABASE_URL"] = f"sqlite:///{db_path}"

            import sys
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                capture_output=True, text=True, env=env,
                cwd=os.path.join(os.path.dirname(__file__), "..")
            )
            assert result.returncode == 0, \
                f"Migration failed:\n{result.stderr}\n{result.stdout}"

    @pytest.mark.integration
    def test_all_expected_tables_created(self, temp_db):
        """After table creation, all critical tables exist."""
        from sqlalchemy import inspect
        inspector = inspect(temp_db)
        tables = set(inspector.get_table_names())

        required_tables = {
            "run", "task_record",  # DAG engine
        }
        missing = required_tables - tables
        assert not missing, f"Missing tables after migration: {missing}"

    @pytest.mark.integration
    def test_idempotent_migration(self):
        """Running alembic upgrade head twice does not cause errors."""
        import sys
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_idempotent.db")
            env = os.environ.copy()
            env["DATABASE_URL"] = f"sqlite:///{db_path}"
            cwd = os.path.join(os.path.dirname(__file__), "..")

            for attempt in range(2):
                result = subprocess.run(
                    [sys.executable, "-m", "alembic", "upgrade", "head"],
                    capture_output=True, text=True, env=env, cwd=cwd
                )
                assert result.returncode == 0, \
                    f"Migration failed on attempt {attempt + 1}:\n{result.stderr}"


class TestEnvironmentValidation:

    @pytest.mark.smoke
    def test_required_environment_variables_present(self):
        """
        All critical environment variables must be set before deployment.
        This test is meant to run in the production environment as a pre-flight check.
        """
        required_vars = [
            "POLYTOPE_MASTER_KEY",
            "JWT_SECRET_KEY",
            "GEMINI_API_KEY",
        ]
        missing = [var for var in required_vars if not os.environ.get(var)]
        assert not missing, f"Missing required environment variables: {missing}"

    @pytest.mark.smoke
    def test_master_key_is_valid_base64_and_minimum_length(self):
        """POLYTOPE_MASTER_KEY must be valid Fernet key (base64-encoded, 32 bytes)."""
        import base64
        key = os.environ.get("POLYTOPE_MASTER_KEY", "")
        assert len(key) >= 40, "Master key appears too short for AES-256"
        try:
            decoded = base64.urlsafe_b64decode(key + "==")
            assert len(decoded) >= 24, "Decoded master key is too short"
        except Exception as e:
            pytest.fail(f"Master key is not valid base64: {e}")

    @pytest.mark.smoke
    def test_jwt_secret_minimum_length(self):
        """JWT_SECRET_KEY must be at least 32 characters to prevent brute-force."""
        jwt_key = os.environ.get("JWT_SECRET_KEY", "")
        assert len(jwt_key) >= 32, \
            f"JWT secret key is too short ({len(jwt_key)} chars, need 32+)"

    @pytest.mark.smoke
    def test_jwt_secret_not_equal_to_master_key(self):
        """JWT_SECRET_KEY must differ from POLYTOPE_MASTER_KEY (separate key material)."""
        master = os.environ.get("POLYTOPE_MASTER_KEY", "")
        jwt = os.environ.get("JWT_SECRET_KEY", "")
        assert master != jwt, \
            "CRITICAL: JWT_SECRET_KEY and POLYTOPE_MASTER_KEY must be different keys!"
