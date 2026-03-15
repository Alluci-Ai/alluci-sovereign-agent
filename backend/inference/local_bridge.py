
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
    Manages local singleton processes for Whisper.cpp (ASR), Ollama (LLM), and Piper (TTS).
    """
    def __init__(self, settings):
        self.settings = settings
        self.whisper_path = getattr(settings, "WHISPER_CPP_PATH", "whisper-cpp")
        self.ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
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
        self.whisper_ready = shutil.which(self.whisper_path) is not None
        self.ollama_ready = self._check_ollama()
        self.piper_ready = shutil.which(self.piper_path) is not None
        
        logger.info(f"[ BRIDGE_STATUS ]: Arch: {self.machine}, Platform: {self.sysname}")
        logger.info(f"[ BRIDGE_STATUS ]: Whisper: {self.whisper_ready}, Ollama: {self.ollama_ready}, Piper: {self.piper_ready}")
        if self.has_cuda:
            logger.info("[ BRIDGE_ACCELERATION ]: CUDA_DETECTED")
        if self.has_rocm:
            logger.info("[ BRIDGE_ACCELERATION ]: ROCM_DETECTED")

    def _check_ollama(self) -> bool:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # Simple socket check for Ollama API
            s.settimeout(1)
            s.connect(("localhost", 11434))
            return True
        except Exception:
            return False
        finally:
            s.close()
        
    async def transcribe(self, audio_data: bytes) -> str:
        """
        Transcribes a chunk of audio using whisper.cpp.
        In a full implementation, this would pipe to a long-running whisper process.
        For now, we use a temporary file approach for stability.
        """
        tmp_wav = "/tmp/aspiration_chunk.wav"
        with open(tmp_wav, "wb") as f:
            f.write(audio_data)
            
        cmd = [self.whisper_path, "-m", "models/ggml-small.en.bin", "-f", tmp_wav, "-otxt"]
        if self.is_apple_silicon:
            # Metal is usually auto-enabled in recent whisper.cpp builds on Mac
            pass
            
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
                        return f.read().strip()
            return ""
        except Exception as e:
            logger.error(f"Whisper ASR Error: {e}")
            return ""

    async def chat_ollama(self, prompt: str, model: str = None) -> AsyncGenerator[str, None]:
        """
        Streams responses from local Ollama instance with RAM-aware model selection.
        """
        import httpx
        url = f"{self.ollama_url}/api/chat"
        
        # RAM-aware model selection
        ram_mb = getattr(self.settings, "TOTAL_RAM_MB", 4096)
        is_lite = getattr(self.settings, "LITE_MODE", False)
        
        if model is None:
            if is_lite or ram_mb < 2000:
                model = "tinyllama:1.1b"
            elif ram_mb < 8000:
                model = "phi3:mini"
            else:
                model = "mistral:7b-instruct-v0.3-q4_K_M"
        
        # Dynamic Tuning
        num_ctx = 2048
        if is_lite or ram_mb < 2000:
            num_ctx = 512 # Reduce context for RPi / Lite
            
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "options": {
                "num_ctx": num_ctx,
                "num_thread": os.cpu_count() or 4
            }
        }
        
        if self.has_cuda or self.is_apple_silicon:
            payload["options"]["num_gpu"] = 35 # Offload layers if GPU present
        
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", url, json=payload) as response:
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data:
                            yield data["message"]["content"]
                        if data.get("done"):
                            break

    async def synthesise(self, text: str) -> bytes:
        """
        Synthesizes speech using Piper TTS.
        """
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
