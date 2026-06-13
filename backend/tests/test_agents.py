import pytest
pytestmark = pytest.mark.unit

"""
Agent Constellation CRUD — Production Test Suite
=================================================
Covers:
  - GET /agents (empty → synthetic root agent; populated → real records)
  - GET /agents/{agent_id}
  - POST /agents (create)
  - PUT /agents/{agent_id} (update, including heartbeat_orders)
  - DELETE /agents/{agent_id}
  - POST /agents/delegate
  - GET /agents/{agent_id}/heartbeat/history
  - GET /heartbeat/history (root)
"""
import json
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from sqlmodel import Session, select


# ─── Fixtures ─────────────────────────────────────────────────────────────────

# Use app_client and auth_headers from conftest.py
# (No need to redefine them here)


# ─── GET /agents — empty db ───────────────────────────────────────────────────

def test_get_agents_returns_synthetic_root_when_empty(app_client, auth_headers, temp_db):
    resp = app_client.get("/api/v1/agents", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data
    assert len(data["agents"]) >= 1
    root = data["agents"][0]
    assert root["id"] == "root"
    assert root["name"] == "Sovereign Root"
    assert isinstance(root["heartbeat_orders"], list)


# ─── POST /agents ─────────────────────────────────────────────────────────────

def test_create_agent(app_client, auth_headers, temp_db):
    payload = {
        "name": "Research Agent",
        "model": "gemini-2.0-flash",
        "status": "DRAFT",
        "description": "Autonomous research specialist",
        "heartbeat_orders": [],
    }
    resp = app_client.post(
        "/api/v1/agents",
        json=payload,
        headers={**auth_headers, "X-CSRF-Token": "test"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "agent" in data
    assert data["agent"]["name"] == "Research Agent"
    assert data["agent"]["status"] == "DRAFT"
    return data["agent"]["id"]


# ─── GET /agents — with records ───────────────────────────────────────────────

def test_get_agents_returns_db_records(app_client, auth_headers, temp_db):
    from backend.models import AgentRecord
    with Session(temp_db) as session:
        session.add(AgentRecord(
            id="agt_list_01", name="List Agent", model="gpt-4o",
            status="ACTIVE", created_at=datetime.now(timezone.utc),
        ))
        session.commit()

    resp = app_client.get("/api/v1/agents", headers=auth_headers)
    assert resp.status_code == 200
    agents = resp.json()["agents"]
    ids = [a["id"] for a in agents]
    assert "agt_list_01" in ids


# ─── GET /agents/{id} ─────────────────────────────────────────────────────────

def test_get_single_agent(app_client, auth_headers, temp_db):
    from backend.models import AgentRecord
    hb_orders = json.dumps([{
        "id": "ord_test_01", "label": "Test Order", "active": True,
        "probe_type": "cron_expression", "probe_config": {},
        "action_type": "log_only", "action_config": {},
        "interval_minutes": 15,
    }])
    with Session(temp_db) as session:
        session.add(AgentRecord(
            id="agt_single_01", name="Single Agent", model="gpt-4o",
            status="ACTIVE", heartbeat_orders=hb_orders,
            created_at=datetime.now(timezone.utc),
        ))
        session.commit()

    resp = app_client.get("/api/v1/agents/agt_single_01", headers=auth_headers)
    assert resp.status_code == 200
    agent = resp.json()["agent"]
    assert agent["id"] == "agt_single_01"
    assert agent["name"] == "Single Agent"
    assert isinstance(agent["heartbeat_orders"], list)
    assert len(agent["heartbeat_orders"]) == 1
    assert agent["heartbeat_orders"][0]["label"] == "Test Order"


def test_get_single_agent_404(app_client, auth_headers):
    resp = app_client.get("/api/v1/agents/nonexistent_id", headers=auth_headers)
    assert resp.status_code == 404


# ─── PUT /agents/{id} ─────────────────────────────────────────────────────────

def test_update_agent_name_and_model(app_client, auth_headers, temp_db):
    from backend.models import AgentRecord
    with Session(temp_db) as session:
        session.add(AgentRecord(
            id="agt_update_01", name="Old Name", model="gpt-4o",
            status="DRAFT", created_at=datetime.now(timezone.utc),
        ))
        session.commit()

    resp = app_client.put(
        "/api/v1/agents/agt_update_01",
        json={"name": "New Name", "model": "gemini-2.0-flash", "status": "ACTIVE"},
        headers={**auth_headers, "X-CSRF-Token": "test"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"

    with Session(temp_db) as session:
        updated = session.get(AgentRecord, "agt_update_01")
    assert updated.name == "New Name"  # type: ignore
    assert updated.model == "gemini-2.0-flash"  # type: ignore
    assert updated.status == "ACTIVE"  # type: ignore


def test_update_agent_heartbeat_orders(app_client, auth_headers, temp_db):
    from backend.models import AgentRecord
    with Session(temp_db) as session:
        session.add(AgentRecord(
            id="agt_hb_update_01", name="HB Agent",
            status="ACTIVE", created_at=datetime.now(timezone.utc),
        ))
        session.commit()

    new_orders = [{
        "id": "new_ord_01", "label": "New Order", "active": True,
        "probe_type": "file_watch", "probe_config": {"path": "TASKS.md"},
        "action_type": "pcl_signal", "action_config": {"priority": 2},
        "interval_minutes": 30,
    }]
    resp = app_client.put(
        "/api/v1/agents/agt_hb_update_01",
        json={"heartbeat_orders": new_orders},
        headers={**auth_headers, "X-CSRF-Token": "test"},
    )
    assert resp.status_code == 200

    with Session(temp_db) as session:
        updated = session.get(AgentRecord, "agt_hb_update_01")
    orders = json.loads(updated.heartbeat_orders)  # type: ignore
    assert len(orders) == 1
    assert orders[0]["action_type"] == "pcl_signal"


def test_update_nonexistent_agent_404(app_client, auth_headers):
    resp = app_client.put(
        "/api/v1/agents/nonexistent",
        json={"name": "X"},
        headers={**auth_headers, "X-CSRF-Token": "test"},
    )
    assert resp.status_code == 404


# ─── DELETE /agents/{id} ──────────────────────────────────────────────────────

def test_delete_agent(app_client, auth_headers, temp_db):
    from backend.models import AgentRecord
    with Session(temp_db) as session:
        session.add(AgentRecord(
            id="agt_del_01", name="To Delete",
            status="DRAFT", created_at=datetime.now(timezone.utc),
        ))
        session.commit()

    resp = app_client.delete(
        "/api/v1/agents/agt_del_01",
        headers={**auth_headers, "X-CSRF-Token": "test"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "DELETED"

    with Session(temp_db) as session:
        deleted = session.get(AgentRecord, "agt_del_01")
    assert deleted is None


def test_delete_nonexistent_agent_404(app_client, auth_headers):
    resp = app_client.delete(
        "/api/v1/agents/nonexistent",
        headers={**auth_headers, "X-CSRF-Token": "test"},
    )
    assert resp.status_code == 404


# ─── POST /agents/delegate ────────────────────────────────────────────────────

def test_delegate_to_agent(app_client, auth_headers, temp_db):
    from backend.models import AgentRecord
    from backend import services as svc
    with Session(temp_db) as session:
        session.add(AgentRecord(
            id="agt_delegate_01", name="Delegate Agent",
            status="ACTIVE",
            system_prompt="You are a specialist.",
            created_at=datetime.now(timezone.utc),
        ))
        session.commit()

    mock_orch = AsyncMock()
    mock_orch.execute_objective = AsyncMock(
        return_value={"status": "completed", "result": "Delegation done"}
    )
    original = svc.orchestrator
    svc.orchestrator = mock_orch
    try:
        resp = app_client.post(
            "/api/v1/agents/delegate",
            json={"agent_id": "agt_delegate_01", "task": "Summarise Q3 results"},
            headers={**auth_headers, "X-CSRF-Token": "test"},
        )
        assert resp.status_code == 200
        mock_orch.execute_objective.assert_awaited_once()
        objective = mock_orch.execute_objective.call_args[1]["objective"]
        assert "[Agent:agt_delegate_01]" in objective
        assert "Summarise Q3 results" in objective
    finally:
        svc.orchestrator = original


# ─── GET /agents/{id}/heartbeat/history ───────────────────────────────────────

def test_agent_heartbeat_history(app_client, auth_headers, temp_db):
    from backend.models import HeartbeatOrderRecord, AgentRecord
    from sqlmodel import Session
    from datetime import timedelta

    with Session(temp_db) as session:
        session.add(AgentRecord(
            id="agt_hist_01", name="History Agent",
            status="ACTIVE", created_at=datetime.now(timezone.utc),
        ))
        for i in range(3):
            session.add(HeartbeatOrderRecord(
                order_id=f"ord_hist_{i:02d}",
                agent_id="agt_hist_01",
                fired_at=datetime.now(timezone.utc) - timedelta(seconds=i*60),
                probe_type="cron_expression",
                action_type="log_only",
                outcome="success",
                detail=f"Run {i}",
            ))
        session.commit()

    resp = app_client.get(
        "/api/v1/agents/agt_hist_01/heartbeat/history",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == "agt_hist_01"
    assert len(data["history"]) == 3
    assert all("order_id" in h for h in data["history"])


# ─── GET /heartbeat/history (root) ────────────────────────────────────────────

def test_root_heartbeat_history(app_client, auth_headers, temp_db):
    from backend.models import HeartbeatOrderRecord
    from sqlmodel import Session
    from datetime import timedelta

    with Session(temp_db) as session:
        for i in range(2):
            session.add(HeartbeatOrderRecord(
                order_id=f"root_hist_{i:02d}",
                agent_id=None,
                fired_at=datetime.now(timezone.utc) - timedelta(seconds=i*120),
                probe_type="task_deadline",
                action_type="notify_ws",
                outcome="success",
                detail=f"Root run {i}",
            ))
        session.commit()

    resp = app_client.get("/api/v1/heartbeat/history", headers=auth_headers)
    assert resp.status_code == 200
    history = resp.json()["history"]
    assert len(history) == 2
    assert all(h.get("order_id", "").startswith("root_hist") for h in history)
