import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, patch, MagicMock
import sys
sys.modules["mnemonic"] = MagicMock()

from sqlmodel import Session
from backend.models import PCLOpportunity

@pytest.fixture
def mock_db_session():
    with patch("backend.routers.system.Session") as mock_session:
        yield mock_session

@pytest.mark.asyncio
async def test_health_public():
    from backend.routers.system import health
    response = await health()
    assert response["status"] == "healthy"
    assert "timestamp" in response

def test_system_health_success(app_client, auth_headers):
    with patch("backend.routers.system.Session"):
        response = app_client.get("/api/v1/system/health", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "healthy"
        assert "uptime" in data

def test_system_health_db_failure(app_client, auth_headers):
    with patch("backend.routers.system.Session", side_effect=Exception("DB down")):
        response = app_client.get("/api/v1/system/health", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "unhealthy"

@pytest.mark.asyncio
async def test_readiness_check_success():
    from backend.routers.system import readiness_check
    with patch("backend.routers.system.Session"):
        with patch("backend.routers.system.services.redis_client", new_callable=AsyncMock) as mock_redis:
            response = await readiness_check()
            assert response["status"] == "ready"
            assert response["checks"]["database"] == "stable"
            assert response["checks"]["redis"] == "stable"

@pytest.mark.asyncio
async def test_readiness_check_db_failure():
    from backend.routers.system import readiness_check
    from fastapi import HTTPException
    with patch("backend.routers.system.Session", side_effect=Exception("DB down")):
        with pytest.raises(HTTPException) as excinfo:
            await readiness_check()
        assert excinfo.value.status_code == 503

@pytest.mark.asyncio
async def test_readiness_check_redis_failure():
    from backend.routers.system import readiness_check
    with patch("backend.routers.system.Session"):
        with patch("backend.routers.system.services.redis_client", new_callable=AsyncMock) as mock_redis:
            mock_redis.ping.side_effect = Exception("Redis down")
            response = await readiness_check()
            assert response["checks"]["redis"] == "failing"

def test_api_readiness_check(app_client, auth_headers):
    with patch("backend.routers.system.readiness_check", new_callable=AsyncMock) as mock_rc:
        mock_rc.return_value = {"status": "ready"}
        response = app_client.get("/api/v1/system/ready", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}

def test_system_status(app_client, auth_headers):
    response = app_client.get("/api/v1/system/status", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert "cpu" in data["resources"]

def test_prometheus_metrics(app_client):
    response = app_client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

@patch("backend.security.audit_ledger.read_audit_log", new_callable=AsyncMock)
def test_get_audit_ledger(mock_read, app_client, auth_headers):
    mock_read.return_value = [{"event": "login"}]
    response = app_client.get("/api/v1/audit/ledger", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == [{"event": "login"}]

@patch("backend.security.audit_ledger.sync_audit_entry", new_callable=AsyncMock)
def test_add_audit_entry(mock_sync, app_client, auth_headers):
    mock_sync.return_value = {"status": "ok"}
    payload = {
        "id": "123",
        "event": "login",
        "details": '{"user": "admin"}',
        "timestamp": "2023-01-01T00:00:00Z"
    }
    response = app_client.post("/api/v1/audit/entry", json=payload, headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_get_pcl_status_success(app_client, auth_headers):
    with patch("backend.routers.system.services.pcl", new_callable=AsyncMock) as mock_pcl:
        mock_pcl.get_status.return_value = {"status": "active"}
        response = app_client.get("/api/v1/system/pcl/status", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"status": "active"}

def test_get_pcl_status_not_init(app_client, auth_headers):
    with patch("backend.routers.system.services.pcl", None):
        response = app_client.get("/api/v1/system/pcl/status", headers=auth_headers)
        assert response.status_code == 503

def test_trigger_pcl_cycle_success(app_client, auth_headers):
    with patch("backend.routers.system.services.pcl", new_callable=AsyncMock) as mock_pcl:
        mock_pcl.run_cycle.return_value = {"cycle": "done"}
        response = app_client.post("/api/v1/system/pcl/cycle", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"cycle": "done"}

def test_trigger_pcl_cycle_not_init(app_client, auth_headers):
    with patch("backend.routers.system.services.pcl", None):
        response = app_client.post("/api/v1/system/pcl/cycle", headers=auth_headers)
        assert response.status_code == 503

def test_get_pcl_opportunities(app_client, auth_headers):
    with patch("backend.routers.system.Session") as mock_session_cls:
        mock_session = mock_session_cls.return_value.__enter__.return_value
        mock_session.exec.return_value.all.return_value = []
        response = app_client.get("/api/v1/system/pcl/opportunities", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

@patch("backend.security.recovery.MasterKeyRecovery")
def test_get_recovery_phrase(mock_mkr, app_client, auth_headers):
    mock_instance = mock_mkr.return_value
    mock_instance.generate_recovery_phrase.return_value = "twelve words here"
    response = app_client.get("/api/v1/system/recovery-phrase", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["phrase"] == "twelve words here"
