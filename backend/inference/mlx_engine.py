import asyncio
import logging
import sys
import os
import json
from typing import AsyncGenerator, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

# Dynamically append the CMake build path to load the native C++ PyBind11 module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../build")))

try:
    import alluci_core # type: ignore
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
    executor: Optional[ThreadPoolExecutor] = None
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MLXEngine, cls).__new__(cls)
            cls._instance.engine = None
            cls._instance.current_lora = None
            cls._instance.is_loading = False
            cls._instance.hardware_profile = HardwareProfiler.get_system_profile()
            cls._instance.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mlx_compute")
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
            model_name = target_model_id.split("/")[-1]
            logger.info(f"MLXEngine: Initializing Native Apple Silicon Engine with {model_name}...")
            
            # Load the compiled native C++ engine
            model_dir = os.path.abspath(f"mirror_cache/{model_name}")
            self.engine = alluci_core.AlluciCognitiveEngine(model_dir) # type: ignore
            logger.info("MLXEngine: Native Engine allocated successfully.")
        except Exception as e:
            logger.error(f"MLXEngine Load Error: {e}")
            raise
        finally:
            self.is_loading = False

    async def ensure_loaded(self):
        """Asynchronously ensures the model is loaded."""
        if self.engine is None and not self.is_loading:
            await asyncio.get_running_loop().run_in_executor(self.executor, self.load_model_sync)
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

    async def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        agent_id: Optional[str] = None,
        tools: Optional[list] = None
    ) -> str:
        """Generates a complete response via the Native C++ Engine."""
        await self.ensure_loaded()
        
        if tools:
            serialized_tools = json.dumps(tools, indent=2)
            tool_directive = (
                f"You are an autonomous agent. You have access to the following tools:\n{serialized_tools}\n"
                "To use a tool, you MUST output a raw JSON object exactly matching the schema. "
                "Do not output conversational text when using a tool."
            )
            system_instruction = f"{tool_directive}\n\n{system_instruction}" if system_instruction else tool_directive
            
        if system_instruction:
            prompt = f"{system_instruction}\n\n{prompt}"
        prompt, temperature = self._apply_ace_logic(prompt, temperature)
        
        # Explicitly enforce the structural attention keys the model was trained on
        prompt = f"<start_of_turn>user\n{prompt}<end_of_turn>\n<start_of_turn>model\n"
        
        def _sync_gen():
            return self.engine.evaluate_intent(prompt, max_tokens, temperature)  # type: ignore
            
        return await asyncio.get_running_loop().run_in_executor(self.executor, _sync_gen)

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        agent_id: Optional[str] = None,
        tools: Optional[list] = None
    ) -> AsyncGenerator[str, None]:
        """
        Streams response via the Native C++ Engine. 
        Note: C++ PyBind11 evaluate_intent is synchronous currently, so it yields the full response immediately.
        """
        response = await self.generate(
            prompt,
            system_instruction=system_instruction,
            max_tokens=max_tokens,
            temperature=temperature,
            agent_id=agent_id,
            tools=tools
        )
        # Yield the response in chunks to simulate streaming for the UI
        chunk_size = 20
        for i in range(0, len(response), chunk_size):
            yield response[i:i+chunk_size]
            await asyncio.sleep(0.01)

    async def apply_lora_adapter(self, agent_id: str) -> None:
        """Alias for apply_context_moat to comply with CognitiveEngine protocol."""
        await self.apply_context_moat(agent_id)

    async def apply_context_moat(self, agent_id: str):
        """Injects LoRA adapters directly into the C++ Engine"""
        await self.ensure_loaded()
        import re
        safe_agent_id = re.sub(r'[^a-zA-Z0-9_-]', '_', agent_id)
        lora_path = os.path.abspath(os.path.join("models", "loras", f"agent_{safe_agent_id}_lora.safetensors"))
        
        if os.path.exists(lora_path) and self.current_lora != lora_path:
            logger.info(f"Injecting Native Polytope Adapters for Context Moat: {lora_path}")
            def _sync_inject():
                self.engine.inject_lora_adapters(lora_path)  # type: ignore
            await asyncio.get_running_loop().run_in_executor(self.executor, _sync_inject)
            self.current_lora = lora_path

engine = MLXEngine()
