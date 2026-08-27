import pytest
from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_get_all_tools():
    response = client.get("/api/v1/tools")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_save_and_delete_tool():
    tool_payload = {
        "id": "test_tool_99",
        "name": "Test Tool",
        "description": "A tool for testing."
    }
    
    # Save tool
    response = client.put("/api/v1/tools/test_tool_99", json=tool_payload)
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
    
    # Delete tool
    response = client.delete("/api/v1/tools/test_tool_99")
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
