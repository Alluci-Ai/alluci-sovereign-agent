
import os
import asyncio
import json
import logging
from ..logging_config import get_logger
import shutil
from typing import AsyncGenerator

logger = get_logger("LocalBridge")

class LocalInferenceBridge:
    """
    Manages local singleton processes for Whisper.cpp (ASR), MLX (LLM), and Piper (TTS).
    """
    def __init__(self, settings):
        self.settings = settings
        self.whisper_path = getattr(settings, "WHISPER_CPP_PATH", "whisper-cpp")
        self.piper_path = getattr(settings, "PIPER_PATH", "piper")
        self.voice_model = getattr(settings, "PIPER_MODEL", "en_US-amy-medium.onnx")
        
        # Hardware & Acceleration Detection
        uname = os.uname()
        self.sysname = uname.sysname
        self.machine = uname.machine
        
        self.is_apple_silicon = self.sysname == 'Darwin' and self.machine == 'arm64'
        self.is_apple_intel = self.sysname == 'Darwin' and self.machine == 'x86_64'
        self.is_linux = self.sysname == 'Linux'
        self.is_raspberry_pi = self.is_linux and (self.machine.startswith('arm') or self.machine == 'aarch64')
        
        # GPU Detection (Linux)
        self.has_cuda = self.is_linux and shutil.which("nvidia-smi") is not None
        self.has_rocm = self.is_linux and shutil.which("rocm-smi") is not None
        
        # Check binary availability
        
        try:
            from backend.inference.mlx_engine import engine
            self.mlx_ready = True
        except ImportError:
            self.mlx_ready = False
            
        self.piper_ready = shutil.which(self.piper_path) is not None
        
        logger.info(f"[ BRIDGE_STATUS ]: Arch: {self.machine}, Platform: {self.sysname}")
        logger.info(f"[ BRIDGE_STATUS ]: Whisper: {self.whisper_ready}, MLX: {self.mlx_ready}, Piper: {self.piper_ready}")
        if self.has_cuda:
            logger.info("[ BRIDGE_ACCELERATION ]: CUDA_DETECTED")
        if self.has_rocm:
            logger.info("[ BRIDGE_ACCELERATION ]: ROCM_DETECTED")
    @property
    def whisper_ready(self):
        """Check if either mlx-whisper (preferred) or whisper.cpp is available."""
        try:
            import mlx_whisper
            return True
        except ImportError:
            return shutil.which(self.whisper_path) is not None
        
    async def transcribe(self, audio_data: bytes) -> str:
        """
        Transcribes audio using native MLX-Whisper on Apple Silicon (preferred)
        or falls back to whisper.cpp subprocess on other platforms.
        """
        # ── Sovereign Path: Native MLX-Whisper (Apple Silicon GPU) ──
        if self.is_apple_silicon:
            try:
                import mlx_whisper
                import numpy as np

                # Convert raw audio bytes to numpy float32 array
                audio_array = np.frombuffer(audio_data, dtype=np.float32)
                if len(audio_array) == 0:
                    # Attempt int16 WAV interpretation
                    audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

                result = await asyncio.to_thread(
                    mlx_whisper.transcribe,
                    audio_array,
                    path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                    fp16=True,
                )
                return result.get("text", "").strip()

            except ImportError:
                logger.warning("[TRANSCRIBE] mlx-whisper not installed. Falling back to whisper.cpp.")
            except Exception as e:
                logger.error(f"[TRANSCRIBE] MLX-Whisper error: {e}. Falling back to whisper.cpp.")

        # ── Fallback: whisper.cpp subprocess (non-Apple-Silicon / missing mlx-whisper) ──
        import tempfile
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_wav = tmp.name
            
        model_path = "models/ggml-small.en.bin"
        if not os.path.exists(model_path):
            logger.error(f"Whisper model missing at {model_path}. Transcribe failed.")
            return ""
            
        cmd = [self.whisper_path, "-m", model_path, "-f", tmp_wav, "-otxt"]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                # whisper.cpp -otxt creates [file].txt
                txt_path = tmp_wav + ".txt"
                if os.path.exists(txt_path):
                    with open(txt_path, "r") as f:
                        result = f.read().strip()
                    os.remove(txt_path)
                    return result
            return ""
        except Exception as e:
            logger.error(f"Whisper ASR Error: {e}")
            return ""
        finally:
            if os.path.exists(tmp_wav):
                os.remove(tmp_wav)

    async def chat_mlx(self, prompt: str, model: str = None) -> AsyncGenerator[str, None]:
        """
        Streams responses from the local MLX Engine instance with RAM-aware model selection.
        """
        if not self.mlx_ready:
            logger.error("MLX Engine is not available.")
            return

        from backend.inference.mlx_engine import engine
        
        # MLX Engine automatically handles hardware profiling
        async for chunk in engine.stream_generate(prompt):
            yield chunk

    async def synthesise(self, text: str) -> bytes:
        """
        Synthesizes speech using Piper TTS.
        """
        if not os.path.exists(self.voice_model):
            logger.error(f"Piper model missing at {self.voice_model}. Synthesis failed.")
            return b""
            
        cmd = [
            self.piper_path,
            "--model", self.voice_model,
            "--output_raw"
        ]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate(input=text.encode())
            if process.returncode == 0:
                return stdout
            else:
                logger.error(f"Piper error: {stderr.decode()}")
                return b""
        except Exception as e:
            logger.error(f"Piper TTS Error: {e}")
            return b""
