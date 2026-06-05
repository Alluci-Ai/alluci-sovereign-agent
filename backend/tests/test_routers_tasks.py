import pytest
from unittest.mock import patch, AsyncMock
from backend.models import TaskUpdate, TaskPriority

def test_get_tasks_success(app_client, auth_headers):
    with patch("backend.routers.tasks.services.task_manager") as mock_tm:
        mock_tm.get_tasks = AsyncMock(return_value=[{"id": 1}])
        response = app_client.get("/api/v1/tasks", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == [{"id": 1}]

def test_get_tasks_not_ready(app_client, auth_headers):
    with patch("backend.routers.tasks.services.task_manager", None):
        response = app_client.get("/api/v1/tasks", headers=auth_headers)
        assert response.status_code == 503

def test_add_task_success(app_client, auth_headers):
    with patch("backend.routers.tasks.services.task_manager") as mock_tm:
        mock_tm.add_task = AsyncMock(return_value={"id": 1, "description": "test"})
        payload = {"description": "test", "completed": False, "priority": "MEDIUM"}
        response = app_client.post("/api/v1/tasks", json=payload, headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"id": 1, "description": "test"}

def test_add_task_not_ready(app_client, auth_headers):
    with patch("backend.routers.tasks.services.task_manager", None):
        payload = {"description": "test", "completed": False, "priority": "MEDIUM"}
        response = app_client.post("/api/v1/tasks", json=payload, headers=auth_headers)
        assert response.status_code == 503

def test_update_task_success(app_client, auth_headers):
    with patch("backend.routers.tasks.services.task_manager") as mock_tm:
        mock_tm.update_task = AsyncMock(return_value={"id": 1, "description": "test2"})
        payload = {"description": "test2", "completed": True, "priority": "HIGH"}
        response = app_client.put("/api/v1/tasks/1", json=payload, headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"id": 1, "description": "test2"}

def test_update_task_not_found(app_client, auth_headers):
    with patch("backend.routers.tasks.services.task_manager") as mock_tm:
        mock_tm.update_task = AsyncMock(return_value=None)
        payload = {"description": "test2", "completed": True, "priority": "HIGH"}
        response = app_client.put("/api/v1/tasks/1", json=payload, headers=auth_headers)
        assert response.status_code == 404

def test_update_task_not_ready(app_client, auth_headers):
    with patch("backend.routers.tasks.services.task_manager", None):
        payload = {"description": "test2", "completed": True, "priority": "HIGH"}
        response = app_client.put("/api/v1/tasks/1", json=payload, headers=auth_headers)
        assert response.status_code == 503

def test_delete_task_success(app_client, auth_headers):
    with patch("backend.routers.tasks.services.task_manager") as mock_tm:
        mock_tm.delete_task = AsyncMock(return_value=True)
        response = app_client.delete("/api/v1/tasks/1", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"status": "deleted"}

def test_delete_task_not_found(app_client, auth_headers):
    with patch("backend.routers.tasks.services.task_manager") as mock_tm:
        mock_tm.delete_task = AsyncMock(return_value=False)
        response = app_client.delete("/api/v1/tasks/1", headers=auth_headers)
        assert response.status_code == 404

def test_delete_task_not_ready(app_client, auth_headers):
    with patch("backend.routers.tasks.services.task_manager", None):
        response = app_client.delete("/api/v1/tasks/1", headers=auth_headers)
        assert response.status_code == 503
