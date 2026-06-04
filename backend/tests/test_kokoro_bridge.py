import pytest
import asyncio
import numpy as np
from unittest.mock import patch, MagicMock, mock_open
import sys

# We must mock mlx.core and kokoro_mlx before importing KokoroBridge
# if they are not installed, to test the KOKORO_AVAILABLE = True path.
mock_mx = MagicMock()
mock_mx.default_device.return_value = "gpu"
mock_mx.gpu = "gpu"
sys.modules['mlx'] = MagicMock()
sys.modules['mlx.core'] = mock_mx

mock_kokoro_tts = MagicMock()
mock_kokoro_tts.from_pretrained.return_value = mock_kokoro_tts
sys.modules['kokoro_mlx'] = MagicMock()
sys.modules['kokoro_mlx'].KokoroTTS = mock_kokoro_tts

from backend.voice.kokoro_bridge import AlluciKokoroBridge

@pytest.fixture(autouse=True)
def reset_singleton():
    AlluciKokoroBridge._instance = None

def test_singleton_pattern():
    bridge1 = AlluciKokoroBridge()
    bridge2 = AlluciKokoroBridge()
    assert bridge1 is bridge2

@patch("os.path.exists")
def test_init_no_manifest(mock_exists):
    mock_exists.return_value = False
    bridge = AlluciKokoroBridge("fake_path.json")
    assert bridge.manifest == {}

@patch("os.path.exists")
@patch("builtins.open", new_callable=mock_open, read_data='{"voice_profiles": {"am_adam": {}}, "model_parameters": {"sample_rate": 24000}}')
def test_init_with_manifest(mock_file, mock_exists):
    mock_exists.return_value = True
    bridge = AlluciKokoroBridge("real_path.json")
    assert "am_adam" in bridge.profiles
    assert bridge.model_meta["sample_rate"] == 24000

@pytest.mark.asyncio
async def test_synthesize_empty_text():
    bridge = AlluciKokoroBridge()
    res = await bridge.synthesize_text_to_pcm("")
    assert res == b''

@pytest.mark.asyncio
@patch("backend.voice.kokoro_bridge.KOKORO_AVAILABLE", True)
@patch("os.path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='{"voice_profiles": {"am_adam": {}}, "model_parameters": {"sample_rate": 24000}}')
async def test_synthesize_success(mock_file, mock_exists):
    bridge = AlluciKokoroBridge("real_path.json")
    
    # Mock TTS generate to return a dummy float array
    bridge.tts = MagicMock()
    bridge.tts.generate.return_value = np.array([0.5, -0.5, 1.5], dtype=np.float32)
    
    pcm = await bridge.synthesize_text_to_pcm("Hello world", voice_profile="am_adam")
    
    assert bridge.tts.generate.called
    kwargs = bridge.tts.generate.call_args[1]
    assert kwargs["text"] == "Hello world"
    assert kwargs["voice"] == "am_adam"
    
    # 1.5 should be clipped to 1.0 (32767)
    # 0.5 is ~16383, -0.5 is ~-16383
    # Check length (3 samples * 2 bytes = 6 bytes)
    assert len(pcm) == 6

@pytest.mark.asyncio
@patch("backend.voice.kokoro_bridge.KOKORO_AVAILABLE", True)
@patch("os.path.exists", return_value=True)
@patch("builtins.open", new_callable=mock_open, read_data='{"voice_profiles": {"custom_voice": {}}}')
async def test_synthesize_fallback_profile(mock_file, mock_exists):
    bridge = AlluciKokoroBridge("real_path.json")
    bridge.tts = MagicMock()
    bridge.tts.generate.return_value = np.array([0.1], dtype=np.float32)
    
    # Profile 'unknown' should fallback to 'am_adam'
    await bridge.synthesize_text_to_pcm("Test", voice_profile="unknown")
    kwargs = bridge.tts.generate.call_args[1]
    assert kwargs["voice"] == "am_adam"

@pytest.mark.asyncio
async def test_synthesize_tts_not_initialized():
    bridge = AlluciKokoroBridge()
    bridge.tts = None
    res = await bridge.synthesize_text_to_pcm("Hello")
    assert res == b''

@pytest.mark.asyncio
async def test_synthesize_generate_returns_none():
    bridge = AlluciKokoroBridge()
    bridge.tts = MagicMock()
    bridge.tts.generate.return_value = None
    res = await bridge.synthesize_text_to_pcm("Hello")
    assert res == b''

@pytest.mark.asyncio
async def test_synthesize_exception_handling():
    bridge = AlluciKokoroBridge()
    bridge.tts = MagicMock()
    bridge.tts.generate.side_effect = Exception("TTS Failed")
    res = await bridge.synthesize_text_to_pcm("Hello")
    assert res == b''
