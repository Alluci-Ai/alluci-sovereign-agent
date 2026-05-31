"""
[ PPN-030 ] Voice Pipeline Validation Suite.
Tests audio segmentation, device tiering, and orchestrator model routing.
"""

import pytest
import numpy as np


def test_audio_window_splitting():
    """Confirms that incoming audio streams are correctly partitioned into standard 200ms sample frames."""
    sampling_rate = 16000
    target_window_duration = 0.200  # 200ms window size
    expected_sample_count = int(sampling_rate * target_window_duration)

    # Generate 1 second of mock audio data
    mock_one_second_stream = np.random.randn(16000).astype(np.float32)

    chunks = []
    # Split the audio array into distinct blocks
    for idx in range(0, len(mock_one_second_stream), expected_sample_count):
        chunk = mock_one_second_stream[idx:idx + expected_sample_count]
        if len(chunk) == expected_sample_count:
            chunks.append(chunk)

    assert len(chunks) == 5, f"Expected 5 chunks, got {len(chunks)}"
    assert len(chunks[0]) == 3200, f"Expected 3200 samples per chunk, got {len(chunks[0])}"


def test_rms_energy_calculation():
    """Validates that the RMS energy filter correctly distinguishes speech from silence."""
    energy_threshold = 0.035

    # Simulate silence (low-energy noise)
    silence = np.random.randn(3200).astype(np.float32) * 0.001
    rms_silence = np.sqrt(np.mean(silence ** 2))
    assert rms_silence < energy_threshold, f"Silence RMS {rms_silence} exceeded threshold"

    # Simulate active speech (high-energy signal)
    speech = np.random.randn(3200).astype(np.float32) * 0.15
    rms_speech = np.sqrt(np.mean(speech ** 2))
    assert rms_speech > energy_threshold, f"Speech RMS {rms_speech} below threshold"


def test_device_tier_assignment():
    """Validates that the orchestrator loads the correct model sizes based on the target device."""
    from backend.inference.voice_orchestrator import AlluciVoiceOrchestrator, DeviceTier

    orchestrator = AlluciVoiceOrchestrator.__new__(AlluciVoiceOrchestrator)
    orchestrator._initialized = False
    orchestrator.__init__()

    # Validate WATCH_ULTRA tier
    config = orchestrator.configure_for_device(DeviceTier.WATCH_ULTRA)
    assert "whisper-tiny" in config["whisper_model"]
    assert config["gemma_model"] is None  # Watch delegates to Workstation

    # Validate IPHONE_17_PRO tier
    config = orchestrator.configure_for_device(DeviceTier.IPHONE_17_PRO)
    assert "whisper-base" in config["whisper_model"]
    assert "polytope_e2b" in config["gemma_model"]

    # Validate MACBOOK_WORKSTATION tier
    config = orchestrator.configure_for_device(DeviceTier.MACBOOK_WORKSTATION)
    assert "whisper-large" in config["whisper_model"]
    assert "polytope_31b" in config["gemma_model"]


def test_watch_cannot_reason_locally():
    """The Watch Ultra must always delegate cognition to the Workstation."""
    from backend.inference.voice_orchestrator import AlluciVoiceOrchestrator, DeviceTier

    orchestrator = AlluciVoiceOrchestrator.__new__(AlluciVoiceOrchestrator)
    orchestrator._initialized = False
    orchestrator.__init__()

    orchestrator.configure_for_device(DeviceTier.WATCH_ULTRA)
    assert orchestrator.can_reason_locally() is False


def test_utterance_finalization():
    """Validates that fragment buffering and utterance finalization works correctly."""
    from backend.inference.voice_orchestrator import AlluciVoiceOrchestrator, DeviceTier

    orchestrator = AlluciVoiceOrchestrator.__new__(AlluciVoiceOrchestrator)
    orchestrator._initialized = False
    orchestrator.__init__()

    orchestrator.configure_for_device(DeviceTier.MACBOOK_WORKSTATION)

    # Simulate fragments arriving
    orchestrator._transcript_buffer = ["Hello", "how", "are", "you"]
    orchestrator._fragment_count = 4

    result = orchestrator.finalize_utterance()
    assert result["text"] == "Hello how are you"
    assert result["fragment_count"] == 4
    assert result["is_final"] is True
    assert result["requires_cognition"] is True

    # Buffer should be reset after finalization
    assert orchestrator._fragment_count == 0
    assert len(orchestrator._transcript_buffer) == 0
