import pytest
pytestmark = pytest.mark.unit

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.routers.dag import router
from backend.security.auth import verify_authenticated

async def mock_auth():
    return True

app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)

@patch("backend.routers.dag.Session")
def test_list_dag_runs(mock_session_class):
    mock_session = MagicMock()
    mock_session.__enter__.return_value = mock_session
    mock_session_class.return_value = mock_session
    
    mock_run = MagicMock()
    mock_run.id = "run1"
    mock_run.objective = "obj"
    mock_run.status = "COMPLETED"
    mock_run.created_at = "2024-01-01"
    
    mock_task = MagicMock()
    mock_task.id = "task1"
    mock_task.task_dag_id = "dag1"
    mock_task.status = "COMPLETED"
    
    # exec(stmt).all() for runs, then tasks, then count
    mock_session.exec.return_value.all.side_effect = [[mock_run], [mock_task], [mock_run]]
    
    res = client.get("/dag/runs?status=COMPLETED")
    assert res.status_code == 200
    data = res.json()
    assert "runs" in data
    assert len(data["runs"]) == 1
    assert data["runs"][0]["id"] == "run1"
    assert data["runs"][0]["task_count"] == 1
    assert data["runs"][0]["tasks"][0]["id"] == "task1"

@patch("backend.routers.dag.Session")
def test_delete_dag_run(mock_session_class):
    mock_session = MagicMock()
    mock_session.__enter__.return_value = mock_session
    mock_session_class.return_value = mock_session
    
    mock_run = MagicMock()
    mock_run.id = 1
    mock_session.get.return_value = mock_run
    mock_session.exec.return_value.all.return_value = []

    res = client.delete("/dag/runs/1")
    assert res.status_code == 200
    assert res.json()["status"] == "success"

@patch("backend.routers.dag.Session")
def test_clear_dag_runs(mock_session_class):
    mock_session = MagicMock()
    mock_session.__enter__.return_value = mock_session
    mock_session_class.return_value = mock_session
    mock_session.exec.return_value.all.return_value = []

    res = client.delete("/dag/runs")
    assert res.status_code == 200
    assert res.json()["status"] == "success"

