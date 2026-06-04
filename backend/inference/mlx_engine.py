import asyncio
import logging
import sys
import os
from typing import AsyncGenerator, Optional, Dict, Any

# Dynamically append the CMake build path to load the native C++ PyBind11 module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../build")))

try:
    import alluci_core
    ALLUCI_CORE_AVAILABLE = True
except ImportError as e:
    ALLUCI_CORE_AVAILABLE = False
    logging.getLogger("MLXEngine").error(f"Failed to import native alluci_core: {e}")

from backend.inference.profiler import HardwareProfiler

logger = logging.getLogger("MLXEngine")

class MLXEngine:
    """
    [ PPN-021 ] Native MLX Inference Singleton.
    Wraps the highly optimized C++ AlluciCognitiveEngine via PyBind11.
    """
    engine: Optional[Any] = None
    current_lora: Optional[str] = None
    is_loading: bool = False
    hardware_profile: Optional[Dict[str, Any]] = None
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MLXEngine, cls).__new__(cls)
            cls._instance.engine = None
            cls._instance.current_lora = None
            cls._instance.is_loading = False
            cls._instance.hardware_profile = HardwareProfiler.get_system_profile()
        return cls._instance

    def load_model_sync(self):
        """Synchronously initializes the native C++ engine."""
        if not ALLUCI_CORE_AVAILABLE:
            logger.warning("alluci_core not installed. Inference will fail.")
            raise ImportError("alluci_core is required for Native LCE.")

        if self.engine is not None:
            return

        self.is_loading = True
        try:
            if not self.hardware_profile:
                raise RuntimeError("Hardware profile not initialized.")
            target_model_id = self.hardware_profile["recommended_model"]
            logger.info(f"MLXEngine: Initializing Native Apple Silicon Engine with {target_model_id}...")
            
            # Load the compiled native C++ engine
            model_dir = os.path.abspath(f"alluci_vault/raw_family/{target_model_id}")
            self.engine = alluci_core.AlluciCognitiveEngine(model_dir)
            logger.info("MLXEngine: Native Engine allocated successfully.")
        except Exception as e:
            logger.error(f"MLXEngine Load Error: {e}")
            raise
        finally:
            self.is_loading = False

    async def ensure_loaded(self):
        """Asynchronously ensures the model is loaded."""
        if self.engine is None and not self.is_loading:
            await asyncio.to_thread(self.load_model_sync)
        while self.is_loading:
            await asyncio.sleep(0.1)

    def _apply_ace_logic(self, prompt: str, temperature: float) -> tuple[str, float]:
        """Injects ACE logic into the prompt and adjusts temperature."""
        from .. import services
        if services.ace:
            state = services.ace.current_state
            ace_state = state.get("ace_state", "<ACE_STATE_0>")
            
            prompt = f"{prompt}\n<A_C>{ace_state}</A_C>"
            
            if ace_state in ["<ACE_STATE_4>", "<ACE_STATE_5>"]:
                temperature = min(0.35, temperature)
            elif ace_state in ["<ACE_STATE_2>", "<ACE_STATE_3>"]:
                temperature = min(0.55, temperature)
            elif ace_state == "<ACE_STATE_1>":
                temperature = max(0.70, temperature)
                
        return prompt, temperature

    async def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """Generates a complete response via the Native C++ Engine."""
        await self.ensure_loaded()
        prompt, temperature = self._apply_ace_logic(prompt, temperature)
        
        def _sync_gen():
            return self.engine.evaluate_intent(prompt, max_tokens, temperature)  # type: ignore
            
        return await asyncio.to_thread(_sync_gen)

    async def generate_stream(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """
        Streams response via the Native C++ Engine. 
        Note: C++ PyBind11 evaluate_intent is synchronous currently, so it yields the full response immediately.
        """
        response = await self.generate(prompt, max_tokens, temperature)
        # Yield the response in chunks to simulate streaming for the UI
        chunk_size = 20
        for i in range(0, len(response), chunk_size):
            yield response[i:i+chunk_size]
            await asyncio.sleep(0.01)

    async def apply_context_moat(self, agent_id: str):
        """Injects LoRA adapters directly into the C++ Engine"""
        await self.ensure_loaded()
        lora_path = os.path.abspath(f"alluci_vault/lora_forge/latest/polytope_adapters.safetensors")
        
        if os.path.exists(lora_path) and self.current_lora != lora_path:
            logger.info(f"Injecting Native Polytope Adapters for Context Moat: {lora_path}")
            def _sync_inject():
                self.engine.inject_lora_adapters(lora_path)  # type: ignore
            await asyncio.to_thread(_sync_inject)
            self.current_lora = lora_path

engine = MLXEngine()
