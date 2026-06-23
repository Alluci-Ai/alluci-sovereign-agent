import asyncio
import logging
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
    _lock: Optional[asyncio.Lock] = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MLXEngine, cls).__new__(cls)
            cls._instance.engine = None
            cls._instance.model = None
            cls._instance.tokenizer = None
            cls._instance.current_lora = None
            cls._instance.is_loading = False
            cls._instance.hardware_profile = HardwareProfiler.get_system_profile()
            cls._instance._lock = asyncio.Lock()
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
                "TIER_1_MAX": "mirror_cache/alluci-gemma-4-31b-it-4bit",
                "TIER_2_PRO": "mirror_cache/alluci-gemma-4-26b-a4b-it-4bit",
                "TIER_3_BASE": "mirror_cache/alluci-gemma-4-12B-it-4bit",
                "TIER_4_EDGE": "mirror_cache/alluci-gemma-4-e2b-it-4bit"
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

            logger.info(f"MLXEngine: Loading MLX-VLM Unified Graph from {target_model_path}...")
            
            # mlx_vlm handles the complex Vision/Text alignment schemas automatically
            from mlx_vlm import load
            self.model, self.tokenizer = load(target_model_path)

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

    def _apply_ace_logic(self, prompt: str, system_instruction: str, temperature: float) -> tuple[str, str, float]:
        """Injects ACE logic into the system instructions and adjusts temperature."""
        from .. import services
        if services.ace:
            state = services.ace.current_state
            ace_state = state.get("ace_state", "<ACE_STATE_0>")
            
            ace_system_inject = f"\nYour current affective computing state is: {ace_state}. Adjust your emotional valence to match this state, but do not echo or output this state token or brackets in your response."
            if system_instruction:
                system_instruction = system_instruction + ace_system_inject
            else:
                system_instruction = ace_system_inject.strip()
            
            if ace_state in ["<ACE_STATE_4>", "<ACE_STATE_5>"]:
                temperature = min(0.35, temperature)
            elif ace_state in ["<ACE_STATE_2>", "<ACE_STATE_3>"]:
                temperature = min(0.55, temperature)
            elif ace_state == "<ACE_STATE_1>":
                temperature = max(0.70, temperature)
                
        return prompt, system_instruction, temperature

    async def generate(self, prompt: str, system_instruction: str = "", max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """Generates a complete response via the native MLX model."""
        await self.ensure_loaded()
        model = self.model
        tokenizer = self.tokenizer
        if model is None or tokenizer is None:
            raise RuntimeError("Model or tokenizer not loaded.")
        prompt, system_instruction, temperature = self._apply_ace_logic(prompt, system_instruction, temperature)
        
        # [ PPN-022 ] Enforce memory limits to prevent macOS Metal Segfaults on massive DAG context
        MAX_CHARS = 32000
        if len(prompt) > MAX_CHARS:
            logger.warning(f"Prompt exceeded {MAX_CHARS} chars. Truncating to prevent MLX memory crash.")
            prompt = "...[Truncated DAG Context]...\n" + prompt[-MAX_CHARS:]

        # Prepare input using tokenizer's chat template
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        formatted_prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
        from mlx_vlm import generate
        def _sync_gen():
            # MTP acceleration enabled natively via generate kwargs in MLX-VLM
            return generate(model, tokenizer, prompt=formatted_prompt, max_tokens=max_tokens, temperature=temperature)
            
        if self._lock is None:
            self._lock = asyncio.Lock()
            
        async with self._lock:
            return await asyncio.to_thread(_sync_gen)

    async def generate_stream(self, prompt: str, system_instruction: str = "", max_tokens: int = 1024, temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """Streams response token-by-token natively using mlx_lm.stream_generate."""
        await self.ensure_loaded()
        model = self.model
        tokenizer = self.tokenizer
        if model is None or tokenizer is None:
            raise RuntimeError("Model or tokenizer not loaded.")
        prompt, system_instruction, temperature = self._apply_ace_logic(prompt, system_instruction, temperature)
        
        # [ PPN-022 ] Enforce memory limits to prevent macOS Metal Segfaults on massive DAG context
        MAX_CHARS = 32000
        if len(prompt) > MAX_CHARS:
            logger.warning(f"Prompt exceeded {MAX_CHARS} chars. Truncating to prevent MLX memory crash.")
            prompt = "...[Truncated DAG Context]...\n" + prompt[-MAX_CHARS:]
            
        # Prepare input using tokenizer's chat template
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        formatted_prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True)
        
        from mlx_vlm import generate
        # mlx_vlm doesn't currently expose stream_generate directly at the top level
        # We wrap standard generate to behave asynchronously for streams, 
        # but in production, we use the mlx_vlm.utils generator.
        from mlx_vlm.utils import stream_generate

        q: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def _run_generator():
            try:
                for response in stream_generate(model, tokenizer, prompt=formatted_prompt, max_tokens=max_tokens, temperature=temperature):
                    loop.call_soon_threadsafe(q.put_nowait, response.text)
                loop.call_soon_threadsafe(q.put_nowait, None)  # sentinel
            except Exception as e:
                logger.error(f"stream_generate error: {e}")
                loop.call_soon_threadsafe(q.put_nowait, e)

        gen_task = None
        if self._lock is None:
            self._lock = asyncio.Lock()
            
        async with self._lock:
            gen_task = asyncio.create_task(asyncio.to_thread(_run_generator))
            try:
                while True:
                    item = await q.get()
                    if item is None:
                        break
                    if isinstance(item, Exception):
                        raise item
                    yield item
            finally:
                if gen_task:
                    await gen_task

    async def apply_context_moat(self, agent_id: str):
        """Loads LoRA adapters if present. Currently a no-op for pure MLX models."""
        await self.ensure_loaded()
        # Placeholder: MLX models can load adapters via tokenizer or model method if supported.
        # For now, simply log if an adapter path exists.
        import re
        import os
        safe_agent_id = re.sub(r'[^a-zA-Z0-9_-]', '_', agent_id)
        lora_path = os.path.abspath(os.path.join("models", "loras", f"agent_{safe_agent_id}_lora.safetensors"))
        if os.path.exists(lora_path) and self.current_lora != lora_path:
            logger.info(f"LoRA adapter found at {lora_path}, but loading not implemented for MLX. Skipping.")
            self.current_lora = lora_path

engine = MLXEngine()
