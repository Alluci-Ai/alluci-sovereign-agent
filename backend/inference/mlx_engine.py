import asyncio
import logging
import os
import json
from typing import AsyncGenerator, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

import mlx.core as mx
from mlx_lm import generate, stream_generate
from mlx_lm.sample_utils import make_sampler
from mlx_lm.utils import load_model, hf_repo_to_path, load_adapters, load_tokenizer

from backend.inference.profiler import HardwareProfiler

logger = logging.getLogger("MLXEngine")

def _polytope_get_classes(config: dict):
    if config.get("model_type") == "gemma4_assistant" or config.get("model_type") == "gemma4_text" or config.get("model_type") == "gemma4":
        import mlx_lm.models.gemma4 as g4
        return g4.Model, g4.ModelArgs
    from mlx_lm.utils import _get_classes
    return _get_classes(config)

class MLXEngine:
    """
    [ PPN-021 ] Native MLX Inference Singleton.
    Fully Python native. Uses mlx_lm and custom Polytope architecture class.
    """
    engine: Optional[Any] = None
    tokenizer: Optional[Any] = None
    current_lora: Optional[str] = None
    is_loading: bool = False
    hardware_profile: Optional[Dict[str, Any]] = None
    executor: ThreadPoolExecutor
    session_caches: Dict[str, Any] = {}
    
    # Strictly one inference operation at a time to prevent MLX Graph Panics
    _inference_lock: asyncio.Lock = asyncio.Lock()
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MLXEngine, cls).__new__(cls)
            cls._instance.engine = None
            cls._instance.tokenizer = None
            cls._instance.current_lora = None
            cls._instance.is_loading = False
            cls._instance.hardware_profile = HardwareProfiler.get_system_profile()
            cls._instance.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="mlx_compute")
        return cls._instance

    def load_model_sync(self):
        """Synchronously initializes the MLX engine."""
        if self.engine is not None:
            return

        self.is_loading = True
        try:
            if not self.hardware_profile:
                raise RuntimeError("Hardware profile not initialized.")
            target_model_id = self.hardware_profile["recommended_model"]
            model_name = target_model_id.split("/")[-1]
            logger.info(f"MLXEngine: Initializing Native Apple Silicon Engine with {model_name}...")
            
            model_dir = os.path.abspath(f"mirror_cache/{model_name}")
            from pathlib import Path; model_path = Path(model_dir)
            
            # Configure Metal GPU VRAM cache ceiling to prevent command buffer OOM panics
            try:
                import mlx.core as mx
                if hasattr(mx, "set_cache_limit"):
                    mx.set_cache_limit(4 * 1024 * 1024 * 1024) # 4GB VRAM cache ceiling
                if hasattr(mx, "set_memory_limit"):
                    import psutil
                    total_ram_gb = psutil.virtual_memory().total / (1024**3)
                    safe_limit_bytes = int(min(total_ram_gb * 0.75, 48.0) * (1024**3))
                    mx.set_memory_limit(safe_limit_bytes)
                logger.info("MLXEngine: Configured native Metal GPU memory cache limits.")
            except Exception as mem_err:
                logger.warning(f"MLXEngine: Could not set Metal cache limits: {mem_err}")

            self.engine, _ = load_model(model_path, get_model_classes=_polytope_get_classes)
            self.tokenizer = load_tokenizer(model_path)
            
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

    def _format_prompt(
        self,
        prompt: str,
        system_instruction: str = "",
        tools: Optional[list] = None
    ) -> str:
        """Formats prompt using native Gemma 4 turn structures."""
        messages = []
        if tools:
            serialized_tools = json.dumps(tools, indent=2)
            tool_directive = (
                f"You are an autonomous agent. You have access to the following tools:\n{serialized_tools}\n"
                "To use a tool, you MUST output a raw JSON object exactly matching the schema. "
                "Do not output conversational text when using a tool."
            )
            system_instruction = f"{tool_directive}\n\n{system_instruction}" if system_instruction else tool_directive

        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
            
        messages.append({"role": "user", "content": prompt})
        
        if self.tokenizer and hasattr(self.tokenizer, 'apply_chat_template'):
            return self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            # Fallback if tokenizer is not fully loaded or doesn't have apply_chat_template
            formatted = ""
            if system_instruction:
                formatted += f"<bos><|turn>system\n{system_instruction}<|turn|>\n"
            formatted += f"<|turn>user\n{prompt}<|turn|>\n<|turn>model\n"
            return formatted

    async def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        max_tokens: int = 8192,
        temperature: float = 0.7,
        agent_id: Optional[str] = None,
        tools: Optional[list] = None
    ) -> str:
        """Generates a complete response via the Native MLX Engine with Metal OOM Protection."""
        try:
            result = ""
            async for chunk in self.generate_stream(
                prompt, system_instruction, max_tokens, temperature, agent_id, tools
            ):
                result += chunk
            import re
            result = re.sub(r'<A_C>.*?</A_C>', '', result).strip()
            return result
        except Exception as ge:
            logger.error(f"[Metal GPU Safeguard] MLX generation notice: {ge}")
            try:
                import mlx.core as mx
                mx.clear_cache()
            except Exception:
                pass
            import gc
            gc.collect()
            raise RuntimeError(f"MLX Engine Local Hardware Failure: {ge}")

    async def generate_stream(
        self,
        prompt: str,
        system_instruction: str = "",
        max_tokens: int = 8192,
        temperature: float = 0.7,
        agent_id: Optional[str] = None,
        tools: Optional[list] = None
    ) -> AsyncGenerator[str, None]:
        """
        Streams response via the Native MLX Engine with real-time callbacks.
        Handles Polytope <|channel>thought channel parsing and stop tokens natively.
        """
        await self.ensure_loaded()
        
        prompt_with_ace, temperature = self._apply_ace_logic(prompt, temperature)
        full_prompt = self._format_prompt(prompt_with_ace, system_instruction=system_instruction, tools=tools)
        
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

        async with self._inference_lock:
            def _sync_gen():
                try:
                    sampler = make_sampler(temp=temperature)
                    sync_buffer = ""
                    assert self.engine is not None and self.tokenizer is not None, "Model not loaded"

                    gen_kwargs = {
                        "prompt": full_prompt,
                        "max_tokens": max_tokens,
                        "sampler": sampler
                    }

                    for response in stream_generate(
                        self.engine,
                        self.tokenizer,
                        **gen_kwargs
                    ):
                        chunk = response.text
                        sync_buffer += chunk
                        loop.call_soon_threadsafe(queue.put_nowait, chunk)
                        if "<turn|>" in sync_buffer or "<eos>" in sync_buffer or "<|endoftext|>" in sync_buffer:
                            break
                except Exception as me:
                    logger.error(f"[Metal GPU Safeguard] Caught MLX Metal execution error: {me}")
                    try:
                        import mlx.core as mx
                        mx.clear_cache()
                    except Exception:
                        pass
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None)

            gen_future = loop.run_in_executor(self.executor, _sync_gen)

        buffer = ""
        in_thought = False
        emitted_thought = False

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
                    
            buffer += chunk
            
            # Check for opening thought channel
            if not in_thought and not emitted_thought:
                if "<|channel>thought" in buffer:
                    in_thought = True
                    buffer = buffer.split("<|channel>thought", 1)[1]
                        
                # Check for closing thought channel
                if in_thought:
                    if "<channel|>" in buffer:
                        in_thought = False
                        emitted_thought = True
                        buffer = buffer.split("<channel|>", 1)[1]
                    else:
                        # Retain trailing characters in case of a partial '<channel|>' split across chunks
                        buffer = buffer[-20:]
                        continue

                if not in_thought:
                    # Check for stop tokens and halt streaming to the frontend
                    if "<turn|>" in buffer:
                        yield_text = buffer.split("<turn|>")[0]
                        if yield_text:
                            yield yield_text
                        break
                    elif "<eos>" in buffer:
                        yield_text = buffer.split("<eos>")[0]
                        if yield_text:
                            yield yield_text
                        break
                    elif "<|endoftext|>" in buffer:
                        yield_text = buffer.split("<|endoftext|>")[0]
                        if yield_text:
                            yield yield_text
                        break
                        
                    # Yield text safely, keeping a 20-char tail for potential split tags
                    if len(buffer) > 20:
                        yield buffer[:-20]
                        buffer = buffer[-20:]

            # Yield any remaining non-thought text in the buffer
            if buffer and not in_thought:
                for stop_tag in ["<turn|>", "<eos>", "<|endoftext|>"]:
                    buffer = buffer.split(stop_tag)[0]
                if buffer:
                    yield buffer

            await gen_future
            # Clear Metal cache natively and collect garbage
            import gc
            mx.clear_cache()
            gc.collect()

    async def apply_lora_adapter(self, agent_id: str) -> None:
        """Alias for apply_context_moat to comply with CognitiveEngine protocol."""
        await self.apply_context_moat(agent_id)

    async def apply_context_moat(self, agent_id: str):
        """Injects LoRA adapters directly into the MLX Engine"""
        await self.ensure_loaded()
        import re
        safe_agent_id = re.sub(r'[^a-zA-Z0-9_-]', '_', agent_id)
        lora_path = os.path.abspath(os.path.join("models", "loras", f"agent_{safe_agent_id}_lora.safetensors"))
        
        if os.path.exists(lora_path) and self.current_lora != lora_path:
            logger.info(f"Injecting Native Polytope Adapters for Context Moat: {lora_path}")
            def _sync_inject():
                assert self.engine is not None, "Engine not loaded"
                load_adapters(self.engine, adapter_path=lora_path)
            await asyncio.get_running_loop().run_in_executor(self.executor, _sync_inject)
            self.current_lora = lora_path

engine = MLXEngine()
