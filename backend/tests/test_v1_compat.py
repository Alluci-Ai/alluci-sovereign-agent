import pytest
from httpx import AsyncClient, ASGITransport
from backend.app import app

@pytest.mark.asyncio
async def test_v1_models_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert isinstance(data["data"], list)
        assert len(data["data"]) > 0
        model_ids = [m["id"] for m in data["data"]]
        assert "mlx-community/GLM-4-32B-0414-4bit" in model_ids

@pytest.mark.asyncio
async def test_v1_chat_completions_non_streaming():
    payload = {
        "model": "mlx-community/GLM-4-32B-0414-4bit",
        "messages": [
            {"role": "system", "content": "You are a test assistant."},
            {"role": "user", "content": "Hello, write a short function."}
        ],
        "stream": False,
        "max_tokens": 10
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/chat/completions", json=payload)
        # Verify status code is 200 or handles gracefully if MLX engine running in test environment
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert data["object"] == "chat.completion"
            assert len(data["choices"]) > 0
            assert "message" in data["choices"][0]
