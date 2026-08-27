import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, patch, MagicMock
from sqlmodel import Session
from backend.models import SessionConfig, AgentRecord

@pytest.fixture
def mock_db_session():
    with patch("backend.routers.sessions.Session") as mock_session:
        yield mock_session

def test_get_current_session_success(app_client, auth_headers):
    class DummyOrchestrator:
        _cached_soul = {"soul": "manifest"}
        
    with patch("backend.routers.sessions.services.orchestrator", DummyOrchestrator()):
        response = app_client.get("/api/v1/session", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["soul"] == {"soul": "manifest"}
        assert data["connections"] == []

def test_get_current_session_error(app_client, auth_headers):
    class DummyOrchestratorErr:
        @property
        def _cached_soul(self):
            raise Exception("Boom")
    
    with patch("backend.routers.sessions.services.orchestrator", DummyOrchestratorErr()):
        response = app_client.get("/api/v1/session", headers=auth_headers)
        assert response.status_code == 500

def test_list_sessions_success(app_client, auth_headers):
    with patch("backend.routers.sessions.services.usage_tracker") as mock_tracker:
        mock_tracker.get_sessions.return_value = [{"session": "1"}]
        response = app_client.get("/api/v1/sessions?limit=10", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == [{"session": "1"}]

def test_list_sessions_not_ready(app_client, auth_headers):
    with patch("backend.routers.sessions.services.usage_tracker", None):
        response = app_client.get("/api/v1/sessions", headers=auth_headers)
        assert response.status_code == 503

def test_get_session_config_found(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    mock_config = MagicMock()
    mock_config.session_key = "abc"
    mock_config.model_override = "gpt-4"
    # Need to make sure dict() works or just return a dict mock
    mock_session_instance.exec.return_value.first.return_value = {"session_key": "abc", "model_override": "gpt-4"}
    response = app_client.get("/api/v1/sessions/abc/config", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["session_key"] == "abc"

def test_get_session_config_not_found(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    mock_session_instance.exec.return_value.first.return_value = None
    response = app_client.get("/api/v1/sessions/abc/config", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == {"session_key": "abc", "overrides": {}}

def test_get_agents_empty(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    mock_session_instance.exec.return_value.all.return_value = []
    response = app_client.get("/api/v1/agents", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["agents"] == []

def test_get_agents_with_data(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    agent = MagicMock()
    agent.id = "123"
    agent.name = "Test Agent"
    agent.model = "gpt-4"
    agent.status = "ACTIVE"
    agent.description = "desc"
    agent.fallback_chain = "chain"
    agent.heartbeat_orders = "[]"
    agent.created_at = None
    mock_session_instance.exec.return_value.all.return_value = [agent]
    response = app_client.get("/api/v1/agents", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["agents"][0]["id"] == "123"

def test_get_agent_found(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    agent = MagicMock()
    agent.id = "123"
    agent.name = "Test Agent"
    agent.model = "gpt-4"
    agent.status = "ACTIVE"
    agent.description = "desc"
    agent.fallback_chain = "chain"
    agent.system_prompt = "prompt"
    agent.heartbeat_orders = "[]"
    agent.soul_manifest_override = "{}"
    agent.created_at = None
    agent.updated_at = None
    mock_session_instance.get.return_value = agent
    response = app_client.get("/api/v1/agents/123", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["agent"]["id"] == "123"

def test_get_agent_not_found(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    mock_session_instance.get.return_value = None
    response = app_client.get("/api/v1/agents/123", headers=auth_headers)
    assert response.status_code == 404

def test_create_agent(app_client, auth_headers, mock_db_session):
    response = app_client.post("/api/v1/agents", json={"name": "New Agent"}, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["agent"]["name"] == "New Agent"
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    mock_session_instance.add.assert_called_once()
    mock_session_instance.commit.assert_called_once()

def test_update_agent_success(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    agent = MagicMock()
    mock_session_instance.get.return_value = agent
    response = app_client.put("/api/v1/agents/123", json={
        "name": "Updated Agent",
        "heartbeat_orders": [{"id": 1}],
        "soul_manifest_override": {"a": 1}
    }, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
    assert agent.name == "Updated Agent"
    mock_session_instance.commit.assert_called_once()

def test_update_agent_fallback_chain(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    agent = MagicMock()
    mock_session_instance.get.return_value = agent
    response = app_client.put("/api/v1/agents/123", json={
        "fallback_chain": "claude",
        "heartbeat_orders": "not a list"
    }, headers=auth_headers)
    assert response.status_code == 200
    assert agent.fallback_chain == "claude"
    assert agent.heartbeat_orders == "[]"

def test_update_agent_not_found(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    mock_session_instance.get.return_value = None
    response = app_client.put("/api/v1/agents/123", json={"name": "x"}, headers=auth_headers)
    assert response.status_code == 404

def test_delegate_to_agent(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    agent = MagicMock()
    agent.name = "Test Agent"
    agent.system_prompt = "system prompt"
    mock_session_instance.get.return_value = agent
    
    with patch("backend.routers.sessions.services.orchestrator", new_callable=AsyncMock) as mock_orch:
        mock_orch.execute_objective.return_value = {"status": "ok"}
        response = app_client.post("/api/v1/agents/delegate", json={
            "agent_id": "123", "task": "do work"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_orch.execute_objective.assert_called_once()
        args = mock_orch.execute_objective.call_args[1]
        assert "Test Agent" in args["objective"]

def test_delegate_to_agent_orchestrator_not_ready(app_client, auth_headers):
    with patch("backend.routers.sessions.services.orchestrator", None):
        response = app_client.post("/api/v1/agents/delegate", json={"agent_id": "123", "task": "do work"}, headers=auth_headers)
        assert response.status_code == 503

def test_delegate_to_agent_no_system_prompt(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    agent = MagicMock()
    agent.name = "Test Agent"
    agent.system_prompt = None
    mock_session_instance.get.return_value = agent
    
    with patch("backend.routers.sessions.services.orchestrator", new_callable=AsyncMock) as mock_orch:
        mock_orch.execute_objective.return_value = {"status": "ok"}
        response = app_client.post("/api/v1/agents/delegate", json={
            "agent_id": "123", "task": "do work"
        }, headers=auth_headers)
        assert response.status_code == 200
        args = mock_orch.execute_objective.call_args[1]
        assert "[Agent:123] do work" in args["objective"]

def test_delete_agent_success(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    agent = MagicMock()
    mock_session_instance.get.return_value = agent
    response = app_client.delete("/api/v1/agents/123", headers=auth_headers)
    assert response.status_code == 200
    mock_session_instance.delete.assert_called_once_with(agent)
    mock_session_instance.commit.assert_called_once()

def test_delete_agent_not_found(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    mock_session_instance.get.return_value = None
    response = app_client.delete("/api/v1/agents/123", headers=auth_headers)
    assert response.status_code == 404

def test_get_agent_heartbeat_history(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    record = MagicMock()
    record.order_id = "1"
    record.fired_at = 123.0
    record.probe_type = "a"
    record.action_type = "b"
    record.outcome = "c"
    record.detail = "d"
    record.signal_stored = True
    mock_session_instance.exec.return_value.all.return_value = [record]
    
    response = app_client.get("/api/v1/agents/123/heartbeat/history", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["agent_id"] == "123"
    assert response.json()["history"][0]["order_id"] == "1"

def test_get_root_heartbeat_history(app_client, auth_headers, mock_db_session):
    mock_session_instance = mock_db_session.return_value.__enter__.return_value
    record = MagicMock()
    record.order_id = "1"
    record.fired_at = 123.0
    record.probe_type = "a"
    record.action_type = "b"
    record.outcome = "c"
    record.detail = "d"
    mock_session_instance.exec.return_value.all.return_value = [record]
    
    response = app_client.get("/api/v1/heartbeat/history", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["history"][0]["order_id"] == "1"

def test_get_agent_heartbeat_history_not_migrated(app_client, auth_headers):
    with patch("backend.routers.sessions.HeartbeatOrderRecord", None):
        response = app_client.get("/api/v1/agents/123/heartbeat/history", headers=auth_headers)
        assert response.status_code == 501

def test_get_root_heartbeat_history_not_migrated(app_client, auth_headers):
    with patch("backend.routers.sessions.HeartbeatOrderRecord", None):
        response = app_client.get("/api/v1/heartbeat/history", headers=auth_headers)
        assert response.status_code == 501
