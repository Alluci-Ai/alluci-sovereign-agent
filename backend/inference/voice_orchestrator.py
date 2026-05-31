"""
[ PPN-030 ] AlluciVoiceOrchestrator
Cross-Device Dynamic Model Tiering for Native MLX-Whisper & Gemma 4.

Strictly isolated from MLXEngine to preserve the Sovereign single-responsibility
architecture. This module handles all audio-to-text processing natively on
Apple Silicon, routing to the optimal whisper/gemma model based on the
requesting device's hardware tier.
"""

import os
import logging
import asyncio
import struct
import numpy as np
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger("VoiceOrchestrator")

try:
    import mlx.core as mx
    import mlx_whisper
    MLX_WHISPER_AVAILABLE = True
except ImportError:
    MLX_WHISPER_AVAILABLE = False
    logger.warning("mlx-whisper not installed. Voice pipeline will be unavailable.")


class DeviceTier(str, Enum):
    """Hardware tiers for cross-device model routing."""
    WATCH_ULTRA = "WATCH_ULTRA"
    IPHONE_17_PRO = "IPHONE_17_PRO"
    MACBOOK_WORKSTATION = "MACBOOK_WORKSTATION"


# ────────────────────────────────────────────────────────
# Model Topology Map: Device → (Whisper Repo, Gemma Path)
# ────────────────────────────────────────────────────────
TIER_MODEL_MAP: Dict[DeviceTier, Dict[str, Any]] = {
    DeviceTier.WATCH_ULTRA: {
        "whisper_repo": "mlx-community/whisper-tiny-4bit",
        "gemma_path": None,  # Watch delegates reasoning to Workstation
        "description": "Edge Sentinel — VAD + Pre-transcribe only",
    },
    DeviceTier.IPHONE_17_PRO: {
        "whisper_repo": "mlx-community/whisper-base-8bit",
        "gemma_path": "/usr/local/bin/alluci/models/polytope_e2b",
        "description": "Mobile Hub — Offline voice + Gemma 4 E2B conformer",
    },
    DeviceTier.MACBOOK_WORKSTATION: {
        "whisper_repo": "mlx-community/whisper-large-v3-turbo",
        "gemma_path": "/usr/local/bin/alluci/models/polytope_31b_fp16",
        "description": "Cognitive Core — Full unquantized Whisper + Gemma 4 31B Dense",
    },
}


class AlluciVoiceOrchestrator:
    """
    Singleton orchestrator that processes streaming 200ms PCM audio fragments
    using Apple Silicon native MLX-Whisper, then hands off pure text tokens
    to the MLXEngine for Gemma 4 cognition.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Active tier configuration (set per-session)
        self._active_tier: Optional[DeviceTier] = None
        self._whisper_repo: Optional[str] = None
        self._gemma_path: Optional[str] = None

        # Rolling transcript buffer for predictive prefetching
        self._transcript_buffer: list[str] = []
        self._fragment_count: int = 0

        logger.info("[VOICE ORCHESTRATOR] Singleton initialized. Awaiting device tier assignment.")

    def configure_for_device(self, tier: DeviceTier) -> Dict[str, Any]:
        """
        Dynamically loads the optimal Whisper + Gemma models for the requesting device.
        Called once when the WebSocket session is established.
        """
        if tier not in TIER_MODEL_MAP:
            raise ValueError(f"Unknown device tier: {tier}")

        config = TIER_MODEL_MAP[tier]
        self._active_tier = tier
        self._whisper_repo = config["whisper_repo"]
        self._gemma_path = config["gemma_path"]
        self._transcript_buffer = []
        self._fragment_count = 0

        logger.info(
            f"[VOICE ORCHESTRATOR] Configured for {tier.value}: "
            f"Whisper={self._whisper_repo}, Gemma={self._gemma_path or 'DELEGATE_TO_WORKSTATION'}"
        )

        return {
            "tier": tier.value,
            "whisper_model": self._whisper_repo,
            "gemma_model": self._gemma_path,
            "description": config["description"],
        }

    async def process_200ms_fragment(self, pcm_bytes: bytes) -> Dict[str, Any]:
        """
        Processes a single 200ms PCM audio fragment (3200 float32 samples at 16kHz).
        Returns the transcribed text fragment and metadata.
        """
        if not MLX_WHISPER_AVAILABLE:
            return {"text": "", "error": "mlx-whisper not available", "is_final": False}

        if not self._whisper_repo:
            return {"text": "", "error": "Device tier not configured", "is_final": False}

        try:
            # Convert raw PCM bytes to numpy float32 array
            sample_count = len(pcm_bytes) // 4  # 4 bytes per float32
            audio_array = np.frombuffer(pcm_bytes, dtype=np.float32, count=sample_count)

            # Run MLX-Whisper natively on Apple Silicon GPU
            result = await asyncio.to_thread(
                mlx_whisper.transcribe,
                audio_array,
                path_or_hf_repo=self._whisper_repo,
                fp16=True,
            )

            fragment_text = result.get("text", "").strip()
            self._fragment_count += 1

            if fragment_text:
                self._transcript_buffer.append(fragment_text)
                logger.debug(
                    f"[VOICE STREAM] Fragment #{self._fragment_count}: '{fragment_text}'"
                )

            return {
                "text": fragment_text,
                "fragment_index": self._fragment_count,
                "is_final": False,
                "tier": self._active_tier.value if self._active_tier else "UNKNOWN",
            }

        except Exception as e:
            logger.error(f"[VOICE ORCHESTRATOR] Transcription error: {e}")
            return {"text": "", "error": str(e), "is_final": False}

    def finalize_utterance(self) -> Dict[str, Any]:
        """
        Called when the frontend detects end-of-speech (sustained silence).
        Merges all buffered 200ms fragments into a single coherent utterance
        and returns it for Gemma 4 cognition.
        """
        full_transcript = " ".join(self._transcript_buffer).strip()
        fragment_count = self._fragment_count

        # Reset for next utterance
        self._transcript_buffer = []
        self._fragment_count = 0

        logger.info(
            f"[VOICE ORCHESTRATOR] Finalized utterance ({fragment_count} fragments): "
            f"'{full_transcript[:80]}...'"
        )

        return {
            "text": full_transcript,
            "fragment_count": fragment_count,
            "is_final": True,
            "tier": self._active_tier.value if self._active_tier else "UNKNOWN",
            "requires_cognition": self._gemma_path is not None,
        }

    def can_reason_locally(self) -> bool:
        """
        Returns True if the current device tier has a local Gemma model loaded.
        Watch Ultra devices return False — they must delegate to the Workstation.
        """
        return self._gemma_path is not None and os.path.exists(self._gemma_path)


# Global singleton
voice_orchestrator = AlluciVoiceOrchestrator()
