import os
import asyncio
import logging
from typing import AsyncGenerator, Optional, List, Any
from .cognitive_engine import CognitiveEngine
from ..config import settings
from .profiler import HardwareProfiler

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    Llama = None

logger = logging.getLogger("LlamaEngine")

class LlamaCppEngine(CognitiveEngine):
    """
    [ PPN-036 ] Native Windows/Linux PC inference engine using llama.cpp.
    Automatically offloads layers to CUDA (NVIDIA) or Vulkan (AMD).
    """

    def __init__(self):
        self.model = None
        self.active_agent_id = None
        self._lock = asyncio.Lock()
        self.current_tier = HardwareProfiler.get_system_profile()
        self.model_path = os.path.join(
            "mirror_cache", 
            self.current_tier["recommended_model"].split("/")[-1] + ".Q4_K_M.gguf" # GGUF format expected
        )
        # In reality, models will have various quant tags, this is simplified.
        # Fallback to a simpler name format if exact mapping doesn't exist
        if "bf16" in self.model_path:
            self.model_path = self.model_path.replace(".Q4_K_M.gguf", ".gguf")
            
        logger.info(f"[LlamaEngine] Initializing for PC platform. Target: {self.model_path}")

    def load_model_sync(self, lora_path: Optional[str] = None) -> None:
        if Llama is None:
            logger.error("[LlamaEngine] llama-cpp-python not installed. Cannot load GGUF model.")
            return

        if not os.path.exists(self.model_path):
            logger.error(f"[LlamaEngine] Model not found in mirror_cache: {self.model_path}")
            return

        logger.info(f"[LlamaEngine] Loading GGUF Model: {self.model_path}")
        
        try:
            self.model = Llama(
                model_path=self.model_path,
                n_gpu_layers=-1, # Offload all layers to GPU
                n_ctx=4096,
                lora_base=self.model_path if lora_path else None,
                lora_path=lora_path,
                verbose=False
            )
            logger.info("[LlamaEngine] Model loaded successfully onto GPU.")
        except Exception as e:
            logger.error(f"[LlamaEngine] Failed to load model: {e}")

    async def ensure_loaded(self) -> None:
        if self.model is None:
            await asyncio.to_thread(self.load_model_sync)

    async def apply_lora_adapter(self, agent_id: str) -> None:
        """Dynamically applies a trained LoRA (.gguf) by completely reloading the engine."""
        async with self._lock:
            if self.active_agent_id == agent_id:
                return
            
            lora_path = os.path.join("models", "loras", f"agent_{agent_id}_lora.gguf")
            if not os.path.exists(lora_path):
                logger.debug(f"[LlamaEngine] No LoRA adapter found for agent {agent_id}. Using base.")
                if self.active_agent_id is not None:
                    # Reload without LoRA if we currently have one active
                    self.active_agent_id = None
                    await asyncio.to_thread(self.load_model_sync)
                return

            logger.info(f"[LlamaEngine] Applying LoRA adapter: {lora_path}")
            # Free current model from VRAM
            if self.model:
                del self.model
                self.model = None
                
            # Reload with LoRA applied
            await asyncio.to_thread(self.load_model_sync, lora_path)
            self.active_agent_id = agent_id

    async def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        agent_id: Optional[str] = None
    ) -> str:
        if agent_id:
            await self.apply_lora_adapter(agent_id)
            
        await self.ensure_loaded()
        model = self.model
        if model is None:
            return "[SYSTEM ERROR]: PC Engine offline."
            
        # Combine system instruction
        if system_instruction:
            prompt = f"{system_instruction}\n\n{prompt}"

        def _generate():
            res = model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False
            )
            return res["choices"][0]["text"]  # type: ignore

        try:
            return await asyncio.to_thread(_generate)
        except Exception as e:
            logger.error(f"[LlamaEngine] Generation failed: {e}")
            return f"[SYSTEM ERROR]: {e}"

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        agent_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        
        if agent_id:
            await self.apply_lora_adapter(agent_id)
            
        await self.ensure_loaded()
        model = self.model
        if model is None:
            yield "[SYSTEM ERROR]: PC Engine offline."
            return

        if system_instruction:
            prompt = f"{system_instruction}\n\n{prompt}"

        def _generate():
            return model(
                prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )

        try:
            stream = await asyncio.to_thread(_generate)
            for chunk in stream:  # type: ignore
                if 'choices' in chunk and len(chunk['choices']) > 0:  # type: ignore
                    text = chunk['choices'][0].get('text', '')  # type: ignore
                    if text:
                        yield text
        except Exception as e:
            logger.error(f"[LlamaEngine] Generation failed: {e}")
            yield f"[SYSTEM ERROR]: {e}"

engine = LlamaCppEngine()
