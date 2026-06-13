import asyncio
import logging
import sys
import os
from typing import AsyncGenerator, Optional, Dict, Any

# Dynamically append the CMake build path to load the native C++ PyBind11 module
# Removed C++ PyBind11 module import; will use mlx_lm for inference.


from backend.inference.profiler import HardwareProfiler

logger = logging.getLogger("MLXEngine")

class MLXEngine:
    """
    [ PPN-021 ] Native MLX Inference Singleton.
    Wraps the highly optimized C++ AlluciCognitiveEngine via PyBind11.
    """
    engine: Optional[Any] = None
    model: Optional[Any] = None
    tokenizer: Optional[Any] = None
    current_lora: Optional[str] = None
    is_loading: bool = False
    hardware_profile: Optional[Dict[str, Any]] = None
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MLXEngine, cls).__new__(cls)
            cls._instance.engine = None
            cls._instance.model = None
            cls._instance.tokenizer = None
            cls._instance.current_lora = None
            cls._instance.is_loading = False
            cls._instance.hardware_profile = HardwareProfiler.get_system_profile()
        return cls._instance

    def load_model_sync(self):
        """Synchronously loads the MLX model and tokenizer using mlx_lm."""
        if self.model is not None:
            return

        self.is_loading = True
        try:
            if not self.hardware_profile:
                raise RuntimeError("Hardware profile not initialized.")

            # ── Alluci Polytope Local Model Routing MOAT ──
            tier = self.hardware_profile.get("tier", "TIER_4_EDGE")
            local_mapping = {
                "TIER_1_MAX": "mirror_cache/gemma-4-31b-it-4bit",
                "TIER_2_PRO": "mirror_cache/gemma-4-26B-A4B-it-OptiQ-4bit",
                "TIER_3_BASE": "mirror_cache/gemma-4-12B-it-OptiQ-4bit",
                "TIER_4_EDGE": "mirror_cache/gemma-4-e2b-it-4bit"
            }

            target_model_path = self.hardware_profile["recommended_model"]

            # Resolve absolute path to the local model folder in the project workspace
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            local_path = os.path.join(base_dir, local_mapping.get(tier, ""))

            if local_path and os.path.exists(local_path):
                target_model_path = local_path
                logger.info(f"MLXEngine: Native Alluci Polytope local model detected in cache. Routing to: {target_model_path}")
            else:
                logger.info(f"MLXEngine: Local cache not found. Fallback to HF repository: {target_model_path}")

            logger.info(f"MLXEngine: Loading MLX model from {target_model_path}...")
            # Use mlx_lm to load model and tokenizer
            from mlx_lm import load
            self.model, self.tokenizer, *_ = load(target_model_path)
            logger.info("MLXEngine: Model and tokenizer loaded successfully.")
        except Exception as e:
            logger.error(f"MLXEngine load error: {e}")
            raise
        finally:
            self.is_loading = False

    async def ensure_loaded(self):
        """Asynchronously ensures the model is loaded."""
        if self.model is None and not self.is_loading:
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
        """Generates a complete response via the native MLX model."""
        await self.ensure_loaded()
        prompt, temperature = self._apply_ace_logic(prompt, temperature)
        # Prepare input using tokenizer's chat template
        messages = [{"role": "user", "content": prompt}]
        formatted_prompt = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True)
        from mlx_lm import generate
        def _sync_gen():
            return generate(self.model, self.tokenizer, prompt=formatted_prompt, max_tokens=max_tokens, temperature=temperature)
        return await asyncio.to_thread(_sync_gen)

    async def generate_stream(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """Streams response by chunking the generated text for UI consumption."""
        response = await self.generate(prompt, max_tokens, temperature)
        chunk_size = 20
        for i in range(0, len(response), chunk_size):
            yield response[i:i+chunk_size]
            await asyncio.sleep(0.01)

    async def apply_context_moat(self, agent_id: str):
        """Loads LoRA adapters if present. Currently a no-op for pure MLX models."""
        await self.ensure_loaded()
        # Placeholder: MLX models can load adapters via tokenizer or model method if supported.
        # For now, simply log if an adapter path exists.
        import re, os
        safe_agent_id = re.sub(r'[^a-zA-Z0-9_-]', '_', agent_id)
        lora_path = os.path.abspath(os.path.join("models", "loras", f"agent_{safe_agent_id}_lora.safetensors"))
        if os.path.exists(lora_path) and self.current_lora != lora_path:
            logger.info(f"LoRA adapter found at {lora_path}, but loading not implemented for MLX. Skipping.")
            self.current_lora = lora_path

engine = MLXEngine()
