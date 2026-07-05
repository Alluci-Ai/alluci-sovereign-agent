import asyncio
import logging
import os
from typing import AsyncGenerator, Optional, Dict, Any

# Dynamically append the CMake build path to load the native C++ PyBind11 module
# Removed C++ PyBind11 module import; will use mlx_lm for inference.


from .cognitive_engine import CognitiveEngine
from backend.inference.profiler import HardwareProfiler

logger = logging.getLogger("MLXEngine")

class MLXEngine(CognitiveEngine):
    """
    [ PPN-021 ] Native MLX Inference Singleton.
    Wraps the highly optimized C++ AlluciCognitiveEngine via PyBind11.
    """
    engine: Optional[Any] = None
    model: Optional[Any] = None
    tokenizer: Optional[Any] = None
    current_lora: Optional[str] = None
    base_weights_backup: Optional[Dict[str, Any]] = None
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
            cls._instance.base_weights_backup = None
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
            target_model_path = self.hardware_profile["recommended_model"]

            # Resolve absolute path to the local model folder in the project workspace
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            local_path = os.path.join(base_dir, "mirror_cache", target_model_path.split("/")[-1])

            if local_path and os.path.exists(local_path):
                target_model_path = local_path
                logger.info(f"MLXEngine: Native Alluci Polytope local model detected in cache. Routing to: {target_model_path}")
            else:
                logger.info(f"MLXEngine: Local cache not found. Fallback to HF repository: {target_model_path}")

            logger.info(f"MLXEngine: Loading MLX-VLM Unified Graph from {target_model_path}...")
            
            # mlx_vlm handles the complex Vision/Text alignment schemas automatically
            from mlx_vlm import load
            self.model, self.tokenizer = load(target_model_path, trust_remote_code=True)
            self.is_vlm = True

            logger.info("MLXEngine: Model and tokenizer loaded successfully.")
        except Exception as e:
            logger.error(f"MLXEngine load error: {e}")
            raise
        finally:
            self.is_loading = False

    async def ensure_loaded(self):
        """Asynchronously ensures the model is loaded."""
        while self.is_loading:
            await asyncio.sleep(0.1)
        if self.model is None or self.tokenizer is None:
            self.load_model_sync()

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

    async def generate(self, prompt: str, system_instruction: str = "", max_tokens: int = 1024, temperature: float = 0.7, agent_id: Optional[str] = None) -> str:
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
        if getattr(self, "is_vlm", True):
            from mlx_vlm import generate
        else:
            from mlx_lm import generate
            
        def _sync_gen() -> str:
            # MTP acceleration enabled natively via generate kwargs
            res = generate(model, tokenizer, prompt=formatted_prompt, max_tokens=max_tokens, temperature=temperature)
            out = getattr(res, "text", res) if not isinstance(res, str) else res
            return str(out) if out is not None else ""
            
        if self._lock is None:
            self._lock = asyncio.Lock()
            # Run synchronously on the main thread to avoid MLX Stream GPU thread mismatch
        return _sync_gen()

    async def generate_stream(self, prompt: str, system_instruction: str = "", max_tokens: int = 1024, temperature: float = 0.75, agent_id: Optional[str] = None) -> AsyncGenerator[str, None]:
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
        
        if getattr(self, "is_vlm", True):
            from mlx_vlm import stream_generate
        else:
            from mlx_lm import stream_generate

        if self._lock is None:
            self._lock = asyncio.Lock()
            
        async with self._lock:
            try:
                for response in stream_generate(model, tokenizer, prompt=formatted_prompt, max_tokens=max_tokens, temperature=temperature, repetition_penalty=1.15, repetition_context_size=20):
                    val = getattr(response, "text", response) if not isinstance(response, str) else response
                    yield str(val)
                    # Yield control to the FastAPI event loop so WebSocket chunks can flush
                    await asyncio.sleep(0)
            except Exception as e:
                logger.error(f"stream_generate error: {e}")
                raise e

    async def apply_lora_adapter(self, agent_id: str):
        """
        Dynamically applies the True LoRA (PEFT) adapter to the active model.
        Updates the model graph natively via MLX in-memory hot-swapping.
        """
        import re
        import os
        import mlx.core as mx
        from mlx.utils import tree_unflatten, tree_flatten
        
        safe_agent_id = re.sub(r'[^a-zA-Z0-9_-]', '_', agent_id)
        lora_path = os.path.abspath(os.path.join("models", "loras", f"agent_{safe_agent_id}_lora.safetensors"))
        
        if self._lock is None:
            self._lock = asyncio.Lock()
            
        async with self._lock:
            await self.ensure_loaded()
            
            if self.current_lora == lora_path:
                return # Already loaded
                
            if not os.path.exists(lora_path):
                logger.debug(f"[MLXEngine] No LoRA adapter found for {agent_id}. Using base model.")
                if self.current_lora is not None:
                    # Unload current LoRA and reset to base using in-memory backup
                    if self.base_weights_backup is not None and self.model is not None:
                        self.model.update(tree_unflatten(list(self.base_weights_backup.items())))
                    self.base_weights_backup = None
                    self.current_lora = None
                return

            logger.info(f"[MLXEngine] Applying LoRA adapter: {lora_path}")
            try:
                # Revert to base model first if we have another LoRA loaded
                if self.current_lora is not None and self.base_weights_backup is not None and self.model is not None:
                    # Safely load backup weights without tree_unflatten which can cause PyBind11 casting errors
                    backup_items = list(self.base_weights_backup.items()) if isinstance(self.base_weights_backup, dict) else self.base_weights_backup
                    self.model.load_weights(backup_items, strict=False)
                    self.base_weights_backup = None
                    self.current_lora = None

                # Load adapters natively into MLX base model
                lora_weights = mx.load(lora_path)
                
                # Backup original weights
                if self.model is not None:
                    flat_model = dict(tree_flatten(self.model.parameters()))
                    
                    # Ensure lora_weights is a dict to safely iterate over keys
                    if not isinstance(lora_weights, dict):
                        raise TypeError(f"Expected lora_weights to be a dict, got {type(lora_weights)}")
                    self.base_weights_backup = {k: flat_model[k] for k in lora_weights.keys() if k in flat_model}

                    # Use load_weights instead of update(tree_unflatten(...)) to bypass Pybind11 items() recursion errors
                    self.model.load_weights(list(lora_weights.items()), strict=False)
                    self.current_lora = lora_path
                    logger.info(f"[MLXEngine] LoRA adapter successfully injected into unified graph.")
                else:
                    logger.warning("[MLXEngine] Base model is not loaded, skipping LoRA application.")
            except Exception as e:
                logger.error(f"[MLXEngine] Failed to apply LoRA adapter: {e}")

engine = MLXEngine()
