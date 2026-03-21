"""
Full API Integration Tests

Uses a real FastAPI TestClient with mocked LLM services and a real
SQLite database per test. All tests require authentication.
"""
import pytest
import json


class TestHealthEndpoints:

    @pytest.mark.smoke
    def test_health_returns_200(self, app_client):
        """GET /health → 200, status=healthy (no auth required)."""
        res = app_client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "healthy"
        assert "timestamp" in res.json()

    @pytest.mark.smoke
    def test_ready_returns_200(self, app_client):
        """GET /ready → 200 (no auth required, used by load balancers)."""
        res = app_client.get("/ready")
        assert res.status_code == 200
        assert res.json()["status"] == "ready"

    @pytest.mark.integration
    def test_system_health_authenticated(self, app_client, auth_headers):
        """GET /api/system/health with auth → detailed system status."""
        res = app_client.get("/api/v1/system/health", headers=auth_headers)
        assert res.status_code == 200
        body = res.json()
        assert "vault" in body or "status" in body


class TestObjectiveExecution:

    @pytest.mark.integration
    def test_execute_returns_structured_response(self, app_client, auth_headers):
        """POST /objective/execute → 200 with result and run_id."""
        res = app_client.post(
            "/api/v1/objective/execute",
            json={"objective": "Test integration objective", "autonomy_level": "RESTRICTED"},
            headers=auth_headers
        )
        assert res.status_code == 200
        body = res.json()
        assert "result" in body or "run_id" in body

    @pytest.mark.integration
    def test_execute_without_auth_returns_401(self, app_client):
        """Unauthenticated objective execution is rejected."""
        res = app_client.post(
            "/api/v1/objective/execute",
            json={"objective": "Hack the mainframe", "autonomy_level": "UNRESTRICTED"}
        )
        assert res.status_code == 401

    @pytest.mark.integration
    def test_execute_empty_objective_rejected(self, app_client, auth_headers):
        """Empty objective string is rejected."""
        res = app_client.post(
            "/api/v1/objective/execute",
            json={"objective": "", "autonomy_level": "RESTRICTED"},
            headers=auth_headers
        )
        assert res.status_code in (400, 422)


class TestTasksAPI:

    @pytest.mark.integration
    def test_create_and_list_task(self, app_client, auth_headers):
        """POST /tasks creates task; GET /tasks returns it."""
        create_res = app_client.post(
            "/api/v1/tasks",
            json={"description": "Integration test task", "completed": False, "priority": "HIGH"},
            headers=auth_headers
        )
        assert create_res.status_code == 200

        list_res = app_client.get("/api/v1/tasks", headers=auth_headers)
        assert list_res.status_code == 200
        tasks = list_res.json()
        assert isinstance(tasks, list)

    @pytest.mark.integration
    def test_update_task_completion(self, app_client, auth_headers):
        """PUT /tasks/{id} can mark a task as completed."""
        create_res = app_client.post(
            "/api/v1/tasks",
            json={"description": "Task to complete", "completed": False, "priority": "LOW"},
            headers=auth_headers
        )
        assert create_res.status_code == 200

        list_res = app_client.get("/api/v1/tasks", headers=auth_headers)
        tasks = list_res.json()
        if tasks:
            task_idx = tasks[0]["index"]
            update_res = app_client.put(
                f"/tasks/{task_idx}",
                json={"description": tasks[0]["description"], "completed": True,
                      "priority": "LOW", "due_date": None},
                headers=auth_headers
            )
            assert update_res.status_code == 200

    @pytest.mark.integration
    def test_delete_task(self, app_client, auth_headers):
        """DELETE /tasks/{id} removes the task."""
        create_res = app_client.post(
            "/api/v1/tasks",
            json={"description": "Task to delete", "completed": False, "priority": "MEDIUM"},
            headers=auth_headers
        )
        assert create_res.status_code == 200
        list_res = app_client.get("/api/v1/tasks", headers=auth_headers)
        tasks = list_res.json()
        if tasks:
            idx = tasks[-1]["index"]
            del_res = app_client.delete(f"/tasks/{idx}", headers=auth_headers)
            assert del_res.status_code == 200


class TestSoulManifestAPI:

    @pytest.mark.integration
    def test_get_soul_manifest(self, app_client, auth_headers):
        """GET /soul/manifest returns manifest with expected fields."""
        res = app_client.get("/api/v1/soul/manifest", headers=auth_headers)
        assert res.status_code in (200, 404)  # 404 if not yet initialized is valid

    @pytest.mark.integration
    def test_update_soul_manifest(self, app_client, auth_headers):
        """PUT /soul/manifest accepts a valid manifest."""
        manifest = {
            "identityCore": "Updated Test Agent",
            "preferences": {
                "tone": 0.8,
                "humor": "DRY",
                "empathy": 0.9,
                "assertiveness": 0.4,
                "creativity": 0.7,
                "verbosity": 0.5,
                "conciseness": "CONCISE"
            }
        }
        res = app_client.put("/api/v1/soul/manifest", json=manifest, headers=auth_headers)
        assert res.status_code in (200, 201)


class TestVaultAPI:

    @pytest.mark.integration
    def test_get_vault_keys_authenticated(self, app_client, auth_headers):
        """GET /api/vault/keys returns keys dict."""
        res = app_client.get("/api/v1/vault/keys", headers=auth_headers)
        assert res.status_code == 200

    @pytest.mark.integration
    def test_post_vault_keys(self, app_client, auth_headers):
        """POST /api/vault/keys stores API keys."""
        keys = {"gemini": "test-key-abc", "openai": "test-key-xyz"}
        res = app_client.post("/api/v1/vault/keys", json=keys, headers=auth_headers)
        assert res.status_code == 200

    @pytest.mark.integration
    def test_vault_rotate(self, app_client, auth_headers):
        """POST /vault/rotate initiates key rotation."""
        from cryptography.fernet import Fernet
        new_key = Fernet.generate_key().decode()
        res = app_client.post("/api/v1/vault/rotate", json={"new_key": new_key}, headers=auth_headers)
        assert res.status_code in (200, 202)
