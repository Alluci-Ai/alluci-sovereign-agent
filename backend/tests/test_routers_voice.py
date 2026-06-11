import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.routers.voice import router
from backend.security.auth import verify_authenticated
from backend import services
import json

async def mock_auth():
    return True

app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)

@patch("backend.routers.voice.voice_orchestrator")
def test_ws_voice_stream_disconnect(mock_orch):
    mock_orch.configure_for_device.return_value = {"ok": 1}
    with client.websocket_connect("/voice/stream") as websocket:
        data = websocket.receive_json()
        assert data == {"type": "config", "ok": 1}
        # Client disconnects by exiting with block

@patch("backend.routers.voice.voice_orchestrator")
def test_ws_voice_stream_fragment(mock_orch):
    mock_orch.configure_for_device.return_value = {}
    mock_orch.process_200ms_fragment = AsyncMock(return_value={"text": "hello", "fragment_index": 1})
    with client.websocket_connect("/voice/stream") as websocket:
        websocket.receive_json() # config
        websocket.send_bytes(b"cGNt")
        res = websocket.receive_json()
        assert res["type"] == "fragment"
        assert res["text"] == "hello"

@patch("backend.routers.voice.voice_orchestrator")
def test_ws_voice_stream_silence(mock_orch):
    mock_orch.configure_for_device.return_value = {}
    mock_orch.process_200ms_fragment = AsyncMock(return_value={})
    mock_orch._fragment_count = 1
    mock_orch.finalize_utterance.return_value = {"text": "final", "fragment_count": 1, "requires_cognition": False}
    with client.websocket_connect("/voice/stream") as websocket:
        websocket.receive_json() # config
        for i in range(5):
            websocket.send_bytes(b"cGNt")
        res = websocket.receive_json()
        assert res["type"] == "utterance"
        assert res["text"] == "final"

@patch("backend.inference.voice_orchestrator.voice_orchestrator.synthesize_response", new_callable=AsyncMock)
@patch("backend.routers.voice.voice_orchestrator")
def test_ws_voice_stream_cognition(mock_orch, mock_synth):
    mock_orch.configure_for_device.return_value = {}
    mock_orch.process_200ms_fragment = AsyncMock(return_value={})
    mock_orch._fragment_count = 1
    mock_orch.finalize_utterance.return_value = {"text": "final", "fragment_count": 1, "requires_cognition": True}
    services.local_inference = AsyncMock()
    services.local_inference.transcribe.return_value = "cog_res"
    mock_synth.return_value = {"type": "audio_pcm", "data": b"audio"}
    
    with client.websocket_connect("/voice/stream") as websocket:
        websocket.receive_json() # config
        for i in range(5):
            websocket.send_bytes(b"cGNt")
        res1 = websocket.receive_json()
        assert res1["type"] == "utterance"
        res2 = websocket.receive_json()
        assert res2["type"] == "cognition"
        res3 = websocket.receive_bytes()
        assert res3 == b"audio"

@patch("backend.routers.voice.voice_orchestrator")
def test_ws_voice_stream_liveness(mock_orch):
    mock_orch.configure_for_device.return_value = {}
    with patch("backend.ace.anti_spoof.AntiSpoofKernel.verify_liveness") as mock_live:
        mock_live.return_value = False
        with pytest.raises(Exception): # websocket disconnect
            with client.websocket_connect("/voice/stream") as websocket:
                websocket.receive_json() # config
                websocket.send_json({"respiratoryRate": 15})
                websocket.receive_json()

@pytest.mark.asyncio
@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_transcribe_voice_not_ready(mock_csrf):
    services.local_inference = None
    res = client.post("/voice/transcribe", files={"file": ("t.wav", b"123")})
    assert res.status_code == 503

@pytest.mark.asyncio
@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_transcribe_voice_success(mock_csrf):
    services.local_inference = AsyncMock()
    services.local_inference.transcribe.return_value = "hi"
    res = client.post("/voice/transcribe", files={"file": ("t.wav", b"123")})
    assert res.status_code == 200
    assert res.json() == {"status": "SUCCESS", "text": "hi"}

@pytest.mark.asyncio
def test_synthesise_voice_not_ready():
    services.local_inference = None
    res = client.get("/voice/synthesise?text=hi")
    assert res.status_code == 503

@pytest.mark.asyncio
def test_synthesise_voice_success():
    services.local_inference = AsyncMock()
    services.local_inference.synthesise.return_value = b"wav"
    res = client.get("/voice/synthesise?text=hi")
    assert res.status_code == 200
    assert res.content == b"wav"

@patch("backend.inference.voice_orchestrator.voice_orchestrator.synthesize_response", new_callable=AsyncMock)
@patch("backend.routers.voice.voice_orchestrator")
def test_ws_voice_stream_cognition_json_tts(mock_orch, mock_synth):
    mock_orch.configure_for_device.return_value = {}
    mock_orch.process_200ms_fragment = AsyncMock(return_value={})
    mock_orch._fragment_count = 1
    mock_orch.finalize_utterance.return_value = {"text": "final", "fragment_count": 1, "requires_cognition": True}
    services.local_inference = AsyncMock()
    services.local_inference.transcribe.return_value = "cog_res"
    mock_synth.return_value = {"type": "not_audio", "data": "json"}
    
    with client.websocket_connect("/voice/stream") as websocket:
        websocket.receive_json()
        for i in range(5):
            websocket.send_bytes(b"cGNt")
        websocket.receive_json()
        websocket.receive_json()
        res = websocket.receive_json()
        assert res["type"] == "not_audio"

@patch("backend.routers.voice.voice_orchestrator")
def test_ws_voice_stream_invalid_tier(mock_orch):
    mock_orch.configure_for_device.return_value = {}
    with client.websocket_connect("/voice/stream?device_tier=INVALID_TIER") as websocket:
        websocket.receive_json()

@patch("backend.routers.voice.voice_orchestrator")
def test_ws_voice_stream_json_decode_error(mock_orch):
    mock_orch.configure_for_device.return_value = {}
    with client.websocket_connect("/voice/stream") as websocket:
        websocket.receive_json()
        websocket.send_text("{invalid_json_format")
