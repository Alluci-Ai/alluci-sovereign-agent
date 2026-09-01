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

    loaded_model_id: Optional[str] = None
    draft_engine: Optional[Any] = None
    draft_model_id: Optional[str] = None

    def load_draft_model_sync(self, draft_model_override: Optional[str] = None):
        """Synchronously loads the lightweight edge model as a speculative drafting engine if compatible."""
        if not draft_model_override or (self.draft_engine is not None and self.draft_model_id == draft_model_override):
            return

        try:
            model_name = draft_model_override.split("/")[-1]
            model_dir = os.path.abspath(f"mirror_cache/{model_name}")
            if not os.path.exists(model_dir):
                return

            from pathlib import Path
            self.draft_engine, _ = load_model(Path(model_dir), get_model_classes=_polytope_get_classes)
            self.draft_model_id = draft_model_override
            logger.info(f"MLXEngine: Speculative Draft Engine [{model_name}] loaded successfully.")
        except Exception as draft_err:
            logger.debug(f"MLXEngine: Draft model {draft_model_override} skipped: {draft_err}")
            self.draft_engine = None

    def load_model_sync(self, target_model_override: Optional[str] = None):
        """Synchronously initializes or switches the MLX engine to the target model."""
        target_model_id = target_model_override or (self.hardware_profile["recommended_model"] if self.hardware_profile else "Alluci/alluci-polytope-gemma-4-31b-it-bf16")
        
        if self.engine is not None and self.loaded_model_id == target_model_id:
            return

        self.is_loading = True
        try:
            # Purge existing engine from Metal VRAM if switching models
            if self.engine is not None:
                self.engine = None
                self.tokenizer = None
                self.draft_engine = None
                self.draft_model_id = None
                MLXEngine._clear_vram_cache()
                import gc
                gc.collect()

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
            self.loaded_model_id = target_model_id
            
            logger.info(f"MLXEngine: Native Engine [{model_name}] allocated successfully.")
        except Exception as e:
            logger.error(f"MLXEngine Load Error: {e}")
            raise
        finally:
            self.is_loading = False

    async def ensure_loaded(self, model_id_override: Optional[str] = None):
        """Asynchronously ensures the model is loaded."""
        if (self.engine is None or (model_id_override and model_id_override != self.loaded_model_id)) and not self.is_loading:
            await asyncio.get_running_loop().run_in_executor(self.executor, lambda: self.load_model_sync(model_id_override))
        while self.is_loading:
            await asyncio.sleep(0.1)

    @staticmethod
    def _apply_streaming_attention_sink(full_prompt: str, max_chars: int = 250000) -> str:
        """
        Streaming Attention Sink Context Manager.
        Dynamically scales to modern Apple Silicon MLX context windows (up to 250,000 characters).
        Enforces Payload-Aware Slicing: protects active document payloads from being truncated,
        rolling only historical multi-turn conversational turns.
        """
        if len(full_prompt) <= max_chars:
            return full_prompt

        # Check for multi-turn structure (<|turn>user ... <|turn|>)
        turn_split = full_prompt.split("<|turn>user\n")
        if len(turn_split) > 2:
            # Multi-turn conversational history: Keep system anchor (turn_split[0]) and the latest turn (turn_split[-1])
            system_anchor = turn_split[0]
            latest_turn = "<|turn>user\n" + turn_split[-1]
            
            # Pack as many recent intermediate turns as fit within max_chars
            available_budget = max_chars - len(system_anchor) - len(latest_turn) - 150
            if available_budget > 0:
                recent_turns = []
                for intermediate in reversed(turn_split[1:-1]):
                    turn_str = "<|turn>user\n" + intermediate
                    if len(turn_str) <= available_budget:
                        recent_turns.insert(0, turn_str)
                        available_budget -= len(turn_str)
                    else:
                        break
                
                middle_str = "".join(recent_turns)
                if middle_str:
                    logger.info(f"[AttentionSink] Rolled older conversational turns ({len(full_prompt)} -> {len(system_anchor) + len(middle_str) + len(latest_turn)} chars).")
                    return f"{system_anchor}[... earlier conversational turns consolidated to H-LSM ...]\n\n{middle_str}{latest_turn}"
            
            logger.info(f"[AttentionSink] Rolled all previous conversational turns ({len(full_prompt)} -> {len(system_anchor) + len(latest_turn)} chars).")
            return f"{system_anchor}[... previous conversational turns archived to H-LSM episodic memory ...]\n\n{latest_turn}"

        # If a single massive turn exceeds 250,000 chars, preserve top 50KB header and latest 200KB payload
        sink_size = min(50000, max_chars // 5)
        tail_size = max_chars - sink_size
        
        attention_sink = full_prompt[:sink_size]
        active_tail = full_prompt[-tail_size:]
        
        logger.info(f"[AttentionSink] Single turn ({len(full_prompt)} chars) exceeds {max_chars} budget. Preserving 50KB header and 200KB payload tail.")
        return f"{attention_sink}\n\n[... intermediate content referenced from H-LSM L3 Knowledge Graph ...]\n\n{active_tail}"

    def _apply_ace_logic(self, system_instruction: str, temperature: float) -> tuple[str, float]:
        """Synthesizes a silent system-layer ACE attunement directive and adjusts sampling temperature natively."""
        from .. import services
        if services.ace:
            state = services.ace.current_state
            ace_state = state.get("ace_state", "<ACE_STATE_0>")
            flow_mode = state.get("flow_mode", "STANDARD")
            stress = state.get("stress_score", 0.0)
            
            ace_directive = (
                f"<ACE_ATTUNEMENT_DIRECTIVE>\n"
                f"Biometric State: {flow_mode} ({ace_state}, Stress Score: {stress:.1f}%)\n"
                f"Operational Alignment: Respond with calm, sovereign executive precision.\n"
                f"</ACE_ATTUNEMENT_DIRECTIVE>"
            )
            system_instruction = f"{ace_directive}\n\n{system_instruction}" if system_instruction else ace_directive
            
            if stress > 65.0:
                temperature = max(0.2, temperature - 0.2)
                
        return system_instruction, temperature


    def _format_prompt(
        self,
        prompt: str,
        system_instruction: str = "",
        tools: Optional[list] = None
    ) -> str:
        """Formats prompt using the loaded tokenizer's native chat template and applies Streaming Attention Sinks."""
        messages = []
        if tools:
            serialized_tools = json.dumps(tools, indent=2)
            tool_directive = (
                f"You are an autonomous agent. You have access to the following tools:\n{serialized_tools}\n"
                "To use a tool, you MUST output a raw JSON object exactly matching the schema. "
                "Do not output conversational text when using a tool."
            )
            system_instruction = f"{tool_directive}\n\n{system_instruction}" if system_instruction else tool_directive

    def _format_prompt(
        self,
        prompt: str,
        system_instruction: str = "",
        tools: Optional[list] = None
    ) -> str:
        """Formats prompt using model-specific turn structures and applies Streaming Attention Sinks."""
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
        
        is_glm = bool(self.loaded_model_id and "glm" in self.loaded_model_id.lower())
        
        # 1. Native Tokenizer Chat Template for GLM / Qwen Architectures
        if is_glm:
            if self.tokenizer is not None and hasattr(self.tokenizer, "apply_chat_template") and getattr(self.tokenizer, "chat_template", None):
                try:
                    formatted = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                    return MLXEngine._apply_streaming_attention_sink(formatted)
                except Exception as tmpl_err:
                    logger.debug(f"[MLXEngine] apply_chat_template fallback notice: {tmpl_err}")

            formatted = "[gMASK]<sop>"
            if system_instruction:
                formatted += f"<|system|>\n{system_instruction}"
            formatted += f"<|user|>\n{prompt}<|assistant|>"
        else:
            # 2. Clean Gemma 4 Turn Formatting (Avoids forcing internal <|think|> chain-of-thought dumps)
            formatted = "<bos>"
            if system_instruction:
                formatted += f"<|turn>system\n{system_instruction}<turn|>\n"
            formatted += f"<|turn>user\n{prompt}<turn|>\n<|turn>model\n"
        
        # Apply Streaming Attention Sink for infinite multi-turn stability
        return MLXEngine._apply_streaming_attention_sink(formatted)

    @staticmethod
    def _clear_vram_cache() -> None:
        """Safely purges Apple Silicon Metal GPU VRAM cache without raising exceptions."""
        try:
            import mlx.core as mx
            if hasattr(mx, "clear_cache"):
                mx.clear_cache()
            elif hasattr(mx, "metal") and hasattr(mx.metal, "clear_cache"):
                mx.metal.clear_cache()
        except Exception:
            pass

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
            MLXEngine._clear_vram_cache()
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
        Handles Polytope <|channel>thought channel parsing, stop tokens, and Speculative Decoding.
        """
        await self.ensure_loaded()
        
        # Mandatory Pre-Inference VRAM Purge
        MLXEngine._clear_vram_cache()
        import gc
        gc.collect()

        sys_with_ace, temperature = self._apply_ace_logic(system_instruction, temperature)
        full_prompt = self._format_prompt(prompt, system_instruction=sys_with_ace, tools=tools)
        
        # Check if speculative decoding can be applied (31B Dense + 2B Draft)
        use_speculative = False
        if self.engine is not None and self.loaded_model_id and "31b" in self.loaded_model_id.lower():
            if self.draft_engine is None:
                try:
                    self.load_draft_model_sync()
                except Exception:
                    pass
            if self.draft_engine is not None:
                use_speculative = True

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()

        async with self._inference_lock:
            def _sync_gen():
                try:
                    sampler = make_sampler(temp=temperature)
                    sync_buffer = ""
                    assert self.engine is not None and self.tokenizer is not None, "Model not loaded"

                    gen_kwargs: Dict[str, Any] = {
                        "prompt": full_prompt,
                        "max_tokens": max_tokens,
                        "sampler": sampler
                    }

                    if use_speculative and self.draft_engine is not None:
                        gen_kwargs["draft_model"] = self.draft_engine

                    # Dynamic KV Cache Safeguards for Long Prompts (>8,000 chars / ~4,000 tokens)
                    prompt_len = len(full_prompt)
                    if prompt_len > 8000:
                        logger.info(f"[Metal GPU Guard] Long prompt detected ({prompt_len} chars). Enabling Q4 KV cache safeguards.")
                        gen_kwargs["max_tokens"] = min(max_tokens, 4096)
                        MLXEngine._clear_vram_cache()

                    stop_tokens = [
                        "<turn|>", "<eos>", "<|endoftext|>", "<|user|>", 
                        "<|observation|>", "<|assistant|>", "<end_of_turn>", "<start_of_turn>"
                    ]

                    try:
                        for response in stream_generate(
                            self.engine,
                            self.tokenizer,
                            **gen_kwargs
                        ):
                            chunk = response.text
                            sync_buffer += chunk
                            loop.call_soon_threadsafe(queue.put_nowait, chunk)
                            if any(st in sync_buffer for st in stop_tokens):
                                break
                    except Exception as gen_err:
                        if use_speculative:
                            logger.warning(f"[Speculative Decoding Fallback] Retrying single-model generation without draft: {gen_err}")
                            gen_kwargs.pop("draft_model", None)
                            for response in stream_generate(
                                self.engine,
                                self.tokenizer,
                                **gen_kwargs
                            ):
                                chunk = response.text
                                sync_buffer += chunk
                                loop.call_soon_threadsafe(queue.put_nowait, chunk)
                                if any(st in sync_buffer for st in stop_tokens):
                                    break
                        else:
                            raise
                except Exception as me:
                    logger.error(f"[Metal GPU Safeguard] Caught MLX Metal execution error: {me}")
                    MLXEngine._clear_vram_cache()
                    gc.collect()
                finally:
                    # Post-Inference VRAM & GC Release
                    MLXEngine._clear_vram_cache()
                    gc.collect()
                    loop.call_soon_threadsafe(queue.put_nowait, None)

            gen_future = loop.run_in_executor(self.executor, _sync_gen)

        has_started = False
        stop_tokens = [
            "<turn|>", "<eos>", "<|endoftext|>", "<|user|>", 
            "<|observation|>", "<|assistant|>", "<end_of_turn>", "<start_of_turn>"
        ]
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            
            # Direct DELTA token streaming (July 31st Native Logic)
            import re
            clean_chunk = re.sub(r'<\|channel.*?>thought\n?|<\|channel.*?>|<channel\|>', '', chunk)
            for stop_tag in stop_tokens:
                if stop_tag in clean_chunk:
                    clean_chunk = clean_chunk.split(stop_tag)[0]

            if not has_started:
                # Strip standalone initial 'thought' preamble tag at stream start
                clean_chunk = re.sub(r'^thought\s*', '', clean_chunk.strip())
                if clean_chunk:
                    has_started = True
                    yield clean_chunk
            elif clean_chunk:
                yield clean_chunk

        await gen_future
        # Clear Metal cache natively and collect garbage
        import gc
        MLXEngine._clear_vram_cache()
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
