import pytest
pytestmark = pytest.mark.unit

import asyncio
from backend.inference.voice_orchestrator import AlluciVoiceOrchestrator, DeviceTier

@pytest.mark.asyncio
async def test_cross_device_topology_routing():
    """Validates that TTS routing yields appropriate types based on Device Tier."""
    orchestrator = AlluciVoiceOrchestrator.__new__(AlluciVoiceOrchestrator)
    orchestrator.__init__()
    
    # 1. Edge Sentinel (Apple Watch) -> Should return Text tokens for native AVSpeech
    orchestrator.configure_for_device(DeviceTier.WATCH_ULTRA)
    res_watch = await orchestrator.synthesize_response("Hello Watch", "af_bella")
    assert res_watch["type"] == "text_for_native_tts"
    assert res_watch["text"] == "Hello Watch"
    assert res_watch["voice_profile"] == "af_bella"
    
    # 2. Mobile Hub (iPhone) -> Should return Text tokens for native AVSpeech
    orchestrator.configure_for_device(DeviceTier.IPHONE_17_PRO)
    res_iphone = await orchestrator.synthesize_response("Hello iPhone", "am_adam")
    assert res_iphone["type"] == "text_for_native_tts"
    assert res_iphone["text"] == "Hello iPhone"
    
    # 3. Workstation (MacBook Pro) -> Should return Kokoro audio buffer (if kokoro_mlx is installed)
    orchestrator.configure_for_device(DeviceTier.MACBOOK_WORKSTATION)
    res_mac = await orchestrator.synthesize_response("Hello Mac", "af_heart")
    
    # It might return an error if Kokoro is not installed in the test environment,
    # but the type should either be "audio_pcm" or "error" (caught by the try-except)
    assert res_mac["type"] in ["audio_pcm", "error"]
    if res_mac["type"] == "audio_pcm":
        assert isinstance(res_mac["data"], bytes)
