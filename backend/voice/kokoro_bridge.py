# -*- coding: utf-8 -*-
"""
Copyright © 2026 Alluci-Ai. All Rights Reserved.
Sovereign-by-Design voice synthesis orchestration kernel.
"""

import os
import json
import logging
import asyncio
import numpy as np

# Enforce a strict zero-trust local execution perimeter
os.environ["HF_HUB_OFFLINE"] = "1"

logger = logging.getLogger("KokoroBridge")

try:
    import mlx.core as mx
    from kokoro_mlx import KokoroTTS
    KOKORO_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False
    logger.warning("Missing 'kokoro-mlx' extension. Execute: pip install kokoro-mlx")

class AlluciKokoroBridge:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False  # type: ignore
        return cls._instance

    def __init__(self, manifest_config_path: str = "./backend/config/tts_manifest.json"):
        if self._initialized:  # type: ignore
            return
        self._initialized = True
        
        if not os.path.exists(manifest_config_path):
            logger.error(f"Manifest not found: {manifest_config_path}")
            self.manifest = {}
        else:
            with open(manifest_config_path, 'r') as file:
                self.manifest = json.load(file)
            
        self.model_meta = self.manifest.get("model_parameters", {})
        self.profiles = self.manifest.get("voice_profiles", {})
        
        self.tts = None
        self.load_model()

    def load_model(self):
        """Lazily load the Kokoro model if not already loaded."""
        if self.tts is not None:
            return
        if KOKORO_AVAILABLE:
            try:
                # Verify the system detects compatible Apple Silicon hardware
                import mlx.core as mx
                assert mx.default_device() == mx.gpu, "[FATAL] Alluci Audio Pipeline requires hardware-accelerated Apple Silicon Unified Memory."
                
                weight_path = self.model_meta.get('weight_path', '')
                model_id = "mlx-community/Kokoro-82M-bf16" if not os.path.exists(weight_path) else weight_path
                logger.info(f"[SOVEREIGN VOICE] Binding Kokoro-82M from: {model_id}")
                
                self.tts = KokoroTTS.from_pretrained(model_id_or_path=model_id)
            except Exception as e:
                logger.error(f"Failed to initialize Kokoro: {e}")

    def unload_model(self):
        """Unload Kokoro model weights from unified memory."""
        if self.tts is not None:
            self.tts = None
            import gc
            gc.collect()
            try:
                import mlx.core as mx
                mx.clear_cache()
            except ImportError:
                pass
            logger.info("[SOVEREIGN VOICE] Kokoro model weights unloaded from VRAM.")

    async def synthesize_text_to_pcm(self, text_payload: str, voice_profile: str = "am_adam") -> bytes:
        """
        Synthesizes text directly into a complete PCM byte buffer (16-bit 48kHz).
        Offloads processing to an asyncio thread.
        """
        self.load_model()
        if not text_payload.strip() or not self.tts:
            return b''

        # If an unknown profile is passed, fallback
        if voice_profile not in self.profiles:
            voice_profile = "am_adam"

        logger.debug(f"[VOICE SYNTHESIS] Generating audio for profile [{voice_profile}].")
        
        def _generate():
            # Generate the full audio array
            result = self.tts.generate(  # type: ignore
                text=text_payload,
                voice=voice_profile,
                speed=1.0,
                sample_rate=self.model_meta.get("sample_rate", 48000)
            )
            
            # The kokoro-mlx generate method returns a TTSResult object containing the audio array
            audio_array = result.audio if hasattr(result, 'audio') else result

            # Convert float32 [-1, 1] to int16 PCM
            if audio_array is not None:
                audio_array = np.clip(audio_array, -1.0, 1.0)
                return (audio_array * 32767).astype(np.int16).tobytes()
            return b''

        try:
            pcm_bytes = _generate()
            return pcm_bytes
        except Exception as e:
            logger.error(f"Kokoro synthesis failed for profile '{voice_profile}': {e}. Ensure the voice profile (.npz) is cached locally if running with HF_HUB_OFFLINE=1.")
            return b''

kokoro_bridge = AlluciKokoroBridge()
