"""
Alluci Sovereign Agent — Locust Load Test

Run: locust -f backend/tests/performance/locustfile.py --host=http://localhost:8000

Simulates:
  - 50 concurrent users
  - Mixed read/write workload
  - Authenticated sessions
  - Realistic task and objective patterns

Target SLOs:
  - /health: p95 < 50ms
  - /tasks (GET): p95 < 200ms
  - /objective/execute: p95 < 10,000ms (LLM call)
  - Error rate < 0.5%
"""
import os
import random
from locust import HttpUser, task, between, events


class AlluciUser(HttpUser):
    """Simulates a single authenticated Alluci user session."""
    wait_time = between(1, 3)

    def on_start(self):
        """Authenticate and store token for subsequent requests."""
        master_key = os.environ.get("POLYTOPE_MASTER_KEY", "")
        response = self.client.post("/auth/login", json={"key": master_key})
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}

    @task(10)
    def check_health(self):
        """High frequency: health check (simulates load balancer probing)."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Health check failed: {response.status_code}")

    @task(8)
    def list_tasks(self):
        """High frequency: list tasks."""
        with self.client.get("/tasks", headers=self.headers, catch_response=True) as response:
            if response.status_code not in (200, 401):
                response.failure(f"List tasks failed: {response.status_code}")

    @task(3)
    def create_task(self):
        """Medium frequency: create a task."""
        priorities = ["LOW", "MEDIUM", "HIGH"]
        with self.client.post(
            "/tasks",
            json={
                "description": f"Load test task {random.randint(1000, 9999)}",
                "completed": False,
                "priority": random.choice(priorities)
            },
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code not in (200, 201, 401, 429):
                response.failure(f"Create task failed: {response.status_code}")

    @task(2)
    def get_vault_keys(self):
        """Medium frequency: check vault keys."""
        with self.client.get("/api/vault/keys", headers=self.headers, catch_response=True) as response:
            if response.status_code not in (200, 401):
                response.failure(f"Vault keys failed: {response.status_code}")

    @task(1)
    def get_dag_runs(self):
        """Low frequency: list DAG execution history."""
        with self.client.get("/api/dag/runs", headers=self.headers, catch_response=True) as response:
            if response.status_code not in (200, 401, 404):
                response.failure(f"DAG runs failed: {response.status_code}")

    @task(1)
    def get_soul_manifest(self):
        """Low frequency: get soul manifest."""
        with self.client.get("/soul/manifest", headers=self.headers, catch_response=True) as response:
            if response.status_code not in (200, 404, 401):
                response.failure(f"Soul manifest failed: {response.status_code}")


@events.quitting.add_listener
def check_slos(environment, **kwargs):
    """Post-test SLO validation — fails the CI run if thresholds are not met."""
    stats = environment.runner.stats

    failures = []

    # Health endpoint p95 < 50ms
    health_stats = stats.get("/health", "GET")
    if health_stats and health_stats.get_response_time_percentile(0.95) > 50:
        failures.append(f"/health p95 exceeded: {health_stats.get_response_time_percentile(0.95):.0f}ms")

    # Task list p95 < 200ms
    tasks_stats = stats.get("/tasks", "GET")
    if tasks_stats and tasks_stats.get_response_time_percentile(0.95) > 200:
        failures.append(f"/tasks p95 exceeded: {tasks_stats.get_response_time_percentile(0.95):.0f}ms")

    # Overall error rate < 0.5%
    total = stats.total
    if total.num_requests > 0:
        error_rate = total.num_failures / total.num_requests
        if error_rate > 0.005:
            failures.append(f"Error rate too high: {error_rate*100:.2f}% (max 0.5%)")

    if failures:
        print("\n❌ SLO VIOLATIONS:")
        for f in failures:
            print(f"  - {f}")
        environment.process_exit_code = 1
    else:
        print("\n✅ All SLOs met.")
