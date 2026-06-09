import pytest

def test_objective_execute_success(app_client, auth_headers):
    """Sanity‑check that the /objective/execute endpoint returns 200 and a basic response.
    The test runs in testing mode where the manifest header is optional.
    """
    payload = {
        "objective": "Summarize the daily report",
        "autonomy_level": "SEMI_AUTONOMOUS"
    }

    response = app_client.post(
        "/api/v1/objective/execute",
        json=payload,
        headers=auth_headers
    )
    assert response.status_code == 200
    json_body = response.json()
    assert "status" in json_body
    assert json_body["status"] == "accepted"
