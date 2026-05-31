import asyncio
import logging
from typing import AsyncGenerator, Optional, Dict, Any

try:
    import mlx.core as mx
    import mlx_lm
    MLX_LM_AVAILABLE = True
except ImportError:
    MLX_LM_AVAILABLE = False

from backend.inference.profiler import HardwareProfiler

logger = logging.getLogger("MLXEngine")

class MLXEngine:
    """
    [ PPN-021 ] Native MLX Inference Singleton.
    Manages loading the Base Gemma 4 model into VRAM based on Hardware Tier,
    and dynamically applying LoRA adapters for the Context Moat.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MLXEngine, cls).__new__(cls)
            cls._instance.model = None
            cls._instance.tokenizer = None
            cls._instance.current_lora = None
            cls._instance.is_loading = False
            cls._instance.hardware_profile = HardwareProfiler.get_system_profile()
        return cls._instance

    def load_model_sync(self):
        """Synchronously loads the model using mlx-lm."""
        if not MLX_LM_AVAILABLE:
            logger.warning("mlx-lm not installed. Inference will fail.")
            raise ImportError("mlx-lm is required for Native LCE.")

        if self.model is not None:
            return

        self.is_loading = True
        try:
            target_model_id = self.hardware_profile["recommended_model"]
            logger.info(f"MLXEngine: Loading {target_model_id} into Unified Memory...")
            
            # mlx_lm handles quantization and Apple Silicon optimizations natively
            self.model, self.tokenizer = mlx_lm.load(target_model_id)
            logger.info("MLXEngine: Model loaded successfully.")
        except Exception as e:
            logger.error(f"MLXEngine Load Error: {e}")
            raise
        finally:
            self.is_loading = False

    async def ensure_loaded(self):
        """Asynchronously ensures the model is loaded."""
        if self.model is None and not self.is_loading:
            await asyncio.to_thread(self.load_model_sync)
        while self.is_loading:
            await asyncio.sleep(0.1)

    async def generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> str:
        """Generates a complete response synchronously in a background thread."""
        await self.ensure_loaded()
        
        def _sync_gen():
            return mlx_lm.generate(
                self.model, 
                self.tokenizer, 
                prompt=prompt, 
                max_tokens=max_tokens, 
                temp=temperature
            )
            
        return await asyncio.to_thread(_sync_gen)

    async def stream_generate(self, prompt: str, max_tokens: int = 1024, temperature: float = 0.7) -> AsyncGenerator[str, None]:
        """Streams tokens from mlx-lm generator."""
        await self.ensure_loaded()
        
        # mlx_lm.stream_generate is a synchronous generator. 
        # To not block the asyncio event loop while the model computes tokens,
        # we pull from it in a thread, or yield sleep. 
        # A simple implementation pulls chunks in a thread.
        def _get_stream():
            for response in mlx_lm.stream_generate(self.model, self.tokenizer, prompt=prompt, max_tokens=max_tokens, temp=temperature):
                yield response
                
        # To properly stream async, we yield from the generator
        # Note: Since the generator yields fast on Apple Silicon, blocking the loop briefly per token is usually acceptable, 
        # but for true async, we wrap it.
        gen = _get_stream()
        while True:
            try:
                # Get next token in a thread to avoid blocking the event loop
                chunk = await asyncio.to_thread(next, gen)
                yield chunk
            except StopIteration:
                break
            except Exception as e:
                logger.error(f"MLX Stream Error: {e}")
                break

    async def apply_context_moat(self, agent_id: str):
        """
        [ PPN-022 ] Dynamically applies an Agent-Scoped LoRA adapter (Context Moat) to the base model.
        Uses mx.load() to merge LoRA delta weights directly into the active base model tree, caching base weights to hot-swap.
        """
        await self.ensure_loaded()
        
        import re
        import os
        safe_agent_id = re.sub(r'[^a-zA-Z0-9_-]', '_', agent_id)
        lora_path = os.path.join(os.getcwd(), "models", "loras", f"agent_{safe_agent_id}_lora.safetensors")
        
        if self.current_lora == agent_id:
            return # Already applied
            
        try:
            logger.info(f"Applying Context Moat for agent '{agent_id}' from {lora_path}...")
            if MLX_LM_AVAILABLE:
                # Cache base model weights the first time we apply a LoRA to allow reverting
                if not hasattr(self, 'base_model_cache') or self.base_model_cache is None:
                    from mlx.utils import tree_flatten
                    self.base_model_cache = {k: v for k, v in tree_flatten(self.model.parameters())}

                if not os.path.exists(lora_path):
                    logger.warning(f"LoRA path {lora_path} does not exist. Operating on base logic.")
                    if self.current_lora is not None:
                         logger.info("Reverting to base model logic.")
                         self.model.update(self.base_model_cache)
                         self.current_lora = None
                    return
                
                # Start from the base model cache
                new_weights = dict(self.base_model_cache)

                # Load LoRA delta weights natively
                lora_weights = mx.load(lora_path)
                
                # Apply them directly to the active model tree cache
                import mlx.core as mx
                for k, delta in lora_weights.items():
                    if k in new_weights:
                        new_weights[k] = new_weights[k] + delta
                
                # Hot-swap the tensors into VRAM
                self.model.update(new_weights)
                
            self.current_lora = agent_id
            logger.info(f"Context Moat for '{agent_id}' natively established in MLX tree.")
        except Exception as e:
            logger.error(f"Failed to apply Context Moat: {e}")

# Global instance
engine = MLXEngine()
