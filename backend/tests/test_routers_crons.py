import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.routers.crons import router
from backend.security.auth import verify_authenticated
from backend import services

async def mock_auth():
    return True

app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)

def test_list_cron_jobs_not_ready():
    services.cron_engine = None
    res = client.get("/cron/jobs")
    assert res.status_code == 503

def test_list_cron_jobs():
    services.cron_engine = MagicMock()
    services.cron_engine.list_jobs.return_value = [{"id": 1}]
    res = client.get("/cron/jobs")
    assert res.status_code == 200
    assert res.json() == [{"id": 1}]

def test_get_cron_job_not_ready():
    services.cron_engine = None
    res = client.get("/cron/jobs/1")
    assert res.status_code == 503

def test_get_cron_job_not_found():
    services.cron_engine = MagicMock()
    services.cron_engine.get_job.return_value = None
    res = client.get("/cron/jobs/1")
    assert res.status_code == 404

def test_get_cron_job():
    services.cron_engine = MagicMock()
    services.cron_engine.get_job.return_value = {"id": 1}
    res = client.get("/cron/jobs/1")
    assert res.status_code == 200
    assert res.json() == {"id": 1}

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_create_cron_job_not_ready(mock_csrf):
    services.cron_engine = None
    res = client.post("/cron/jobs", json={"rule": "*"})
    assert res.status_code == 503

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_create_cron_job(mock_csrf):
    services.cron_engine = MagicMock()
    services.cron_engine.create_job.return_value = {"id": 2}
    res = client.post("/cron/jobs", json={"rule": "*"})
    assert res.status_code == 200
    assert res.json() == {"id": 2}

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_delete_cron_job_not_ready(mock_csrf):
    services.cron_engine = None
    res = client.delete("/cron/jobs/1")
    assert res.status_code == 503

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_delete_cron_job_not_found(mock_csrf):
    services.cron_engine = MagicMock()
    services.cron_engine.delete_job.return_value = False
    res = client.delete("/cron/jobs/1")
    assert res.status_code == 404

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_delete_cron_job(mock_csrf):
    services.cron_engine = MagicMock()
    services.cron_engine.delete_job.return_value = True
    res = client.delete("/cron/jobs/1")
    assert res.status_code == 200
    assert res.json() == {"status": "SUCCESS"}
