import json
import logging
import asyncio
import os
import math
import httpx
import platform
from typing import Literal, Dict, Any, List, Optional
from ..logging_config import get_logger
from .executive import ExecutiveRouter
from .speculative import SpeculativeDecoder

logger = get_logger("ModelRouter")

# Conditional imports for failover providers
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False

try:
    import aioboto3
    import boto3
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

HUGGINGFACE_AVAILABLE = False
try:
    import huggingface_hub
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    pass

class ModelRouter(ExecutiveRouter):
    """
    Routes inference requests with failover chain: 
    Tactical (Groq) → Local (Ollama) → Local Fallback (LM Studio) → Optional (HF) → Cloud Failovers.
    Implements the ExecutiveRouter interface for LCE Decoupling.
    """
    def __init__(self, settings, vault=None):
        self.logger = get_logger("ModelRouter")
        self.settings = settings
        self.vault = vault
        self.ws_gateway = None

        # ── LOCAL: Native LCE (Speculative Decoding) ────────────────────────
        self.lce_enabled = getattr(settings, "LOCAL_LCE_ENABLED", False)
        self.lce_decoder = None
        if self.lce_enabled:
            target_path = getattr(settings, "LOCAL_GEMMA_TARGET_PATH", "./models/gemma-4-31b-dense")
            draft_path = getattr(settings, "LOCAL_GEMMA_DRAFT_PATH", "./models/gemma-4-e2b")
            self.lce_decoder = SpeculativeDecoder(
                target_model_id=target_path,
                draft_model_id=draft_path
            )
            # We don't load_models here to save VRAM until actually needed or during 'warmup'
            self.logger.info("Local Cognitive Engine (LCE) initialized.")

        # ── LOCAL: Ollama (PRIMARY) ───────────────────────────────────────────
        self.ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
        self.ollama_ready = self._probe_ollama()
        if self.ollama_ready:
            self.logger.info("Ollama reachable at %s (PRIMARY)", self.ollama_url)
        else:
            self.logger.info("Ollama not reachable — will fall through to LM Studio")

        # ── LOCAL: LM Studio (LOCAL FALLBACK) ─────────────────────────────────
        self.lm_studio_client = None
        lm_url = getattr(settings, "LM_STUDIO_URL", None)
        if OPENAI_AVAILABLE and lm_url:
            self.lm_studio_client = openai.AsyncOpenAI(
                api_key="lm-studio",
                base_url=lm_url,
            )
            self.logger.info("LM Studio client ready (local fallback 2).")

        # ── OPTIONAL: HuggingFace ─────────────────────────────────────────────
        self.hf_token = getattr(settings, "HUGGINGFACE_API_TOKEN", None)
        self.hf_model_id = getattr(
            settings, "HUGGINGFACE_MODEL_ID",
            "mistralai/Mistral-7B-Instruct-v0.3"
        )
        self.hf_endpoint_url = getattr(settings, "HUGGINGFACE_ENDPOINT_URL", None)
        self.hf_client = None
        if self.hf_token and HUGGINGFACE_AVAILABLE:
            from huggingface_hub import AsyncInferenceClient
            self.hf_client = AsyncInferenceClient(
                model=self.hf_endpoint_url or self.hf_model_id,
                token=self.hf_token,
            )
            self.logger.info(
                "HuggingFace Inference client ready (model=%s).", self.hf_model_id
            )
        elif self.hf_token and not HUGGINGFACE_AVAILABLE:
            self.logger.warning(
                "HUGGINGFACE_API_TOKEN is set but 'huggingface_hub' is not installed. "
                "Run: pip install huggingface_hub"
            )

        # ── CLOUD PROVIDERS ───────────────────────────────────────────────────
        sovereign = getattr(settings, "SOVEREIGN_MODE", False)
        if sovereign:
            self.logger.info(
                "SOVEREIGN_MODE=True — cloud providers disabled, "
                "local inference only."
            )

        # Primary cloud: Gemini
        self.gemini_flash = None
        self.gemini_pro = None
        if not sovereign and GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_flash = genai.GenerativeModel("gemini-2.0-flash")
            self.gemini_pro = genai.GenerativeModel("gemini-2.5-pro-preview-05-06")
            self.logger.info("Gemini models ready (cloud 1).")

        # Cloud failover 2: OpenAI
        self.openai_client = None
        if not sovereign and OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            base_url = None
            if settings.OPENAI_API_KEY.startswith("github_pat_"):
                base_url = "https://models.inference.ai.azure.com"
            self.openai_client = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=base_url,
            )
            self.logger.info("OpenAI client ready (cloud 2).")

        # Cloud failover 3: Anthropic
        self.anthropic_client = None
        if not sovereign and ANTHROPIC_AVAILABLE and settings.ANTHROPIC_API_KEY:
            self.anthropic_client = anthropic.AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )
            self.logger.info("Anthropic client ready (cloud 3).")

        # Groq — tactical KCM shortcut
        self.groq_api_key = None if sovereign else getattr(settings, "GROQ_API_KEY", None)

        # Cloud failover 4: DeepSeek
        self.deepseek_client = None
        if not sovereign and OPENAI_AVAILABLE and getattr(settings, "DEEPSEEK_API_KEY", None):
            base_url = (
                "https://models.inference.ai.azure.com"
                if settings.DEEPSEEK_API_KEY.startswith("github_pat_")
                else "https://api.deepseek.com"
            )
            self.deepseek_client = openai.AsyncOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=base_url,
            )

        # Cloud failover 5: OpenRouter
        self.openrouter_client = None
        if not sovereign and OPENAI_AVAILABLE and getattr(settings, "OPENROUTER_API_KEY", None):
            self.openrouter_client = openai.AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://polytope.local",
                    "X-Title": "Polytope Sovereign OS",
                },
            )

        # Cloud failovers 6–8: Together, Cohere, Bedrock
        self.together_client = None
        if not sovereign and OPENAI_AVAILABLE and getattr(settings, "TOGETHER_API_KEY", None):
            self.together_client = openai.AsyncOpenAI(
                api_key=settings.TOGETHER_API_KEY,
                base_url="https://api.together.xyz/v1",
            )

        self.cohere_client = None
        if not sovereign and COHERE_AVAILABLE and getattr(settings, "COHERE_API_KEY", None):
            self.cohere_client = cohere.AsyncClient(
                api_key=settings.COHERE_API_KEY
            )

        self.bedrock_session = None
        if (not sovereign and BOTO3_AVAILABLE
                and getattr(settings, "AWS_ACCESS_KEY_ID", None)):
            self.bedrock_session = aioboto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
                region_name=getattr(settings, "AWS_REGION", "us-east-1"),
            )

        # Kimi / NVIDIA NIM
        self.nvidia_nim_api_key = (
            None if sovereign
            else getattr(settings, "NVIDIA_NIM_API_KEY", None)
        )

        # ElevenLabs, image, video — not affected by sovereign mode
        self.elevenlabs_api_key = getattr(settings, "ELEVENLABS_API_KEY", None)
        self.midjourney_api_key = getattr(settings, "MIDJOURNEY_API_KEY", None)
        self.runway_api_key = getattr(settings, "RUNWAY_API_KEY", None)

    def _probe_ollama(self) -> bool:
        """Non-blocking TCP probe to check if Ollama daemon is listening."""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.8)
            host = self.ollama_url.replace("http://", "").replace("https://", "").split(":")[0]
            # Use default 11434 if not specified in URL
            port = 11434
            if ":" in self.ollama_url.replace("://", ""):
                 port = int(self.ollama_url.split(":")[-1])
            s.connect((host, port))
            return True
        except Exception:
            return False
        finally:
            try:
                s.close()
            except Exception:
                pass

    async def _ollama_request(
        self,
        prompt: str,
        use_strong: bool = False,
        json_mode: bool = False,
        system_instruction: str = ""
    ) -> str:
        """
        Primary inference via local Ollama daemon.
        Selects model based on SOVEREIGN_MODE settings and available RAM.
        """
        ram_mb = getattr(self.settings, "TOTAL_RAM_MB", 4096)
        lite = getattr(self.settings, "LITE_MODE", False)

        if lite or ram_mb < 2000:
            model = getattr(self.settings, "OLLAMA_MODEL_LITE", "gemma2:2b")
        elif ram_mb < 8000:
            model = getattr(self.settings, "OLLAMA_MODEL_LIGHT", "gemma2:2b")
        elif use_strong and ram_mb >= 16000:
            model = getattr(self.settings, "OLLAMA_MODEL_STRONG", "gemma2:27b")
        else:
            model = getattr(self.settings, "OLLAMA_MODEL_MEDIUM", "gemma2:9b")

        timeout = getattr(self.settings, "OLLAMA_TIMEOUT_SECONDS", 120)
        num_gpu = getattr(self.settings, "OLLAMA_NUM_GPU", 35)

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": 512 if lite else (2048 if ram_mb < 6000 else 4096),
                "num_thread": os.cpu_count() or 4,
            },
        }
        
        # GPU offloading logic
        machine = platform.machine().lower()
        is_apple_silicon = platform.system() == "Darwin" and machine == "arm64"
        import shutil
        has_cuda = shutil.which("nvidia-smi") is not None
        if has_cuda or is_apple_silicon:
            payload["options"]["num_gpu"] = num_gpu

        if json_mode:
            payload["format"] = "json"

        url = f"{self.ollama_url}/api/chat"
        async with httpx.AsyncClient(timeout=float(timeout)) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["message"]["content"]

    async def _lm_studio_request(
        self,
        prompt: str,
        use_strong: bool = False,
        system_instruction: str = ""
    ) -> str:
        """LM Studio via OpenAI-compatible API — local fallback after Ollama."""
        if not self.lm_studio_client:
            raise RuntimeError("LM Studio not configured")
        model = getattr(self.settings, "LM_STUDIO_MODEL", "local-model")
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        response = await self.lm_studio_client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=2048,
        )
        return response.choices[0].message.content

    async def _huggingface_request(
        self,
        prompt: str,
        use_strong: bool = False,
        system_instruction: str = ""
    ) -> str:
        """HuggingFace Inference API (Serverless or Dedicated)."""
        if not self.hf_client:
            raise RuntimeError("HuggingFace client not initialised")
        
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"{system_instruction}\n\nUser: {prompt}"

        result = await self.hf_client.text_generation(
            prompt=full_prompt,
            max_new_tokens=1024,
            temperature=0.7,
            return_full_text=False,
        )
        return result if isinstance(result, str) else result.generated_text

    async def _lce_request(self, prompt: str, system_instruction: str = "") -> str:
        """Local Cognitive Engine via Native Speculative Decoding."""
        if not self.lce_decoder:
            raise RuntimeError("LCE Decoder not initialized")
        
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"System: {system_instruction}\n\nUser: {prompt}"
            
        # Lazy loading of models
        if not self.lce_decoder.target_model:
            self.logger.info("LCE: Loading Gemma 4 models into VRAM...")
            self.lce_decoder.load_models()
            
        return await self.lce_decoder.generate_response(full_prompt)

    async def _gemini_request(self, prompt: str, use_pro: bool = False, json_mode: bool = False, system_instruction: str = "") -> str:
        """Cloud Failover 1: Gemini."""
        if not self.gemini_flash and self.vault:
            # Attempt to pull key from vault and re-configure
            keys = await self.vault.retrieve_secret("alluci_api_keys") or {}
            gemini_key = keys.get("llm", {}).get("googleCloud")
            if gemini_key:
                genai.configure(api_key=gemini_key)
                self.gemini_flash = genai.GenerativeModel("gemini-2.0-flash")
                self.gemini_pro = genai.GenerativeModel("gemini-2.5-pro-preview-05-06")
                self.logger.info("Gemini models initialized from vault.")

        model = self.gemini_pro if use_pro else self.gemini_flash
        if not model:
            raise RuntimeError("Gemini not configured")
        generation_config = {}
        if json_mode:
            generation_config = {"response_mime_type": "application/json"}
        
        # Gemini uses 'contents' with a list of parts, we prepend the system instruction if it supports it
        # or use system_instruction parameter if available in the SDK
        contents = []
        if system_instruction:
            # Note: Depending on SDK version, system_instruction might be passed in GenerativeModel init
            # But for simple failover, we'll prepend it to the user prompt if not already handled
            prompt = f"{system_instruction}\n\n{prompt}"
            
        response = await model.generate_content_async(prompt, generation_config=generation_config)
        return response.text

    async def _openai_request(self, prompt: str, use_strong: bool = False, json_mode: bool = False, system_instruction: str = "") -> str:
        """Cloud Failover 2: OpenAI."""
        if not self.openai_client:
            raise RuntimeError("OpenAI not configured")
        model = "gpt-4o" if use_strong else "gpt-4o-mini"
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = await self.openai_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def _generic_openai_request(self, prompt: str, client: Any, name: str, use_strong: bool = False, system_instruction: str = "") -> str:
        """Handles generic OpenAI-compatible providers like DeepSeek, Together, OpenRouter."""
        model_map = {
            "DeepSeek": ("deepseek-reasoner" if use_strong else "deepseek-chat"),
            "Together": "meta-llama/Llama-3.3-70b-instruct-turbo",
            "OpenRouter": "google/gemma-2-9b-it", # Fallback to Gemma family in cloud if possible
        }
        model = model_map.get(name, "default")
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=4096,
        )
        return response.choices[0].message.content

    async def _anthropic_request(self, prompt: str, use_strong: bool = False, system_instruction: str = "") -> str:
        """Cloud Failover 3: Anthropic."""
        if not self.anthropic_client:
            raise RuntimeError("Anthropic not configured")
        model = "claude-3-7-sonnet-20250219" if use_strong else "claude-3-5-haiku-20241022"
        
        kwargs: Dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_instruction:
            kwargs["system"] = system_instruction

        message = await self.anthropic_client.messages.create(**kwargs)
        return message.content[0].text

    async def _kimi_request(self, prompt: str, thinking: bool = True, system_instruction: str = "") -> str:
        """NVIDIA NIM integration for Kimi k2.5."""
        if not self.nvidia_nim_api_key:
            raise RuntimeError("NVIDIA NIM API Key missing")
        invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.nvidia_nim_api_key}", "Accept": "application/json"}
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "moonshotai/kimi-k2.5",
            "messages": messages,
            "max_tokens": 16384,
            "temperature": 1.00,
            "chat_template_kwargs": {"thinking": thinking},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(invoke_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _cohere_request(self, prompt: str, use_strong: bool = False, system_instruction: str = "") -> str:
        """Failover 7: Cohere."""
        if not self.cohere_client:
            raise RuntimeError("Cohere not configured")
        model = "command-r-plus" if use_strong else "command-r"
        
        kwargs: Dict[str, Any] = {
            "model": model,
            "message": prompt,
            "max_tokens": 4096
        }
        if system_instruction:
            kwargs["preamble"] = system_instruction # Cohere uses 'preamble' for system instructions

        response = await self.cohere_client.chat(**kwargs)
        return response.text

    async def _bedrock_request(self, prompt: str, use_strong: bool = False, system_instruction: str = "") -> str:
        """Failover 8: AWS Bedrock."""
        if not self.bedrock_session:
            raise RuntimeError("AWS Bedrock not configured")
        model_id = "anthropic.claude-3-sonnet-20240229-v1:0" if use_strong else "anthropic.claude-3-haiku-20240307-v1:0"
        
        payload: Dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_instruction:
            payload["system"] = system_instruction

        body = json.dumps(payload).encode("utf-8")
        async with self.bedrock_session.client("bedrock-runtime") as client:
            response = await client.invoke_model(body=body, modelId=model_id, accept="application/json", contentType="application/json")
            response_body = await response["body"].read()
            data = json.loads(response_body)
            return data["content"][0]["text"]

    async def _notify_fallback(self, model_name: str):
        if hasattr(self, 'ws_gateway') and self.ws_gateway:
            try:
                await self.ws_gateway.broadcast_event('model.fallback', {"fallback_model": model_name})
            except Exception:
                pass

    def evaluate_privacy_constraint(self, privacy_level: str, is_cloud_provider: bool) -> bool:
        if privacy_level in ["SENSITIVE", "AIRGAPPED"] and is_cloud_provider:
            return False
        return True

    async def get_response(
        self, 
        prompt: str, 
        complexity: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM", 
        privacy_level: Literal["PUBLIC", "SENSITIVE", "AIRGAPPED"] = "PUBLIC",
        psi: float = 0.0,
        system_instruction: str = ""
    ) -> str:
        from ..tracing_config import get_tracer
        from opentelemetry import trace
        tracer = get_tracer("Inference.Router")

        with tracer.start_as_current_span("get_response") as span:
            span.set_attribute("complexity", complexity)
            span.set_attribute("psi", psi)

            use_strong = (complexity == "HIGH")
            use_tactical = False
            
            if psi > 0.0:
                strong_penalty = math.cosh(psi) * 3000.0
                light_penalty = math.cosh(psi) * 200.0
                if strong_penalty > 2.0 * light_penalty and psi > 0.7:
                    use_tactical = True
                    use_strong = False
                elif psi > 0.8:
                    use_strong = True
            
            if not use_tactical:
                use_strong = use_strong or (complexity == "HIGH") or (psi > 0.8)
            
            import re
            json_mode = bool(re.search(
                r'\b(return|output|respond\s+with|give\s+me|provide|format\s+as|reply\s+in)\b[^.]*\bjson\b',
                prompt.lower()
            ))
            
            errors: list = []

            # ── KCM Tactical Shortcut ────────────────────────────────────────
            if use_tactical and self.groq_api_key:
                try:
                    self.logger.info("[KCM] Tactical routing → Groq LPU")
                    span.set_attribute("model_provider", "groq")
                    return await self.get_fast_tactical_response(prompt)
                except Exception as e:
                    errors.append(f"Groq (tactical): {e}")
                    span.add_event("Groq tactical failover")
                    self.logger.warning("Tactical Groq failed, continuing: %s", e)

            # ── Step 1: Local Inference (Highest Priority) ───────────────────
            # Try LCE (Native Gemma 4), then Ollama, then LM Studio.
            local_providers = []
            if self.lce_enabled:
                local_providers.append(("Native LCE", lambda p: self._lce_request(p, system_instruction=system_instruction)))
            if self.ollama_ready:
                local_providers.append(("Ollama", lambda p: self._ollama_request(p, use_strong=use_strong, json_mode=json_mode, system_instruction=system_instruction)))
            if self.lm_studio_client:
                local_providers.append(("LM Studio", lambda p: self._lm_studio_request(p, use_strong=use_strong, system_instruction=system_instruction)))

            for name, provider_fn in local_providers:
                try:
                    self.logger.info(f"[LOCAL_SCAN] Trying {name}...")
                    res = await provider_fn(prompt)
                    span.set_attribute("model_provider", name.lower().replace(" ", "_"))
                    return res
                except Exception as e:
                    errors.append(f"{name}: {e}")
                    self.logger.warning(f"{name} failed, trying next local: {e}")

            # ── Step 2: Cloud Fallback (If allowed) ─────────────────────────
            sovereign_mode = getattr(self.settings, "SOVEREIGN_MODE", False)
            allow_cloud = not sovereign_mode and self.evaluate_privacy_constraint(privacy_level, is_cloud_provider=True)
            
            if allow_cloud:
                # Define cloud providers and their check-conditions
                cloud_sequence = []
                
                if self.gemini_flash or self.gemini_pro:
                    cloud_sequence.append(("Gemini", lambda p: self._gemini_request(p, use_pro=use_strong, json_mode=json_mode, system_instruction=system_instruction)))
                
                if self.openai_client:
                    cloud_sequence.append(("OpenAI", lambda p: self._openai_request(p, use_strong=use_strong, json_mode=json_mode, system_instruction=system_instruction)))
                
                if self.anthropic_client:
                    cloud_sequence.append(("Anthropic", lambda p: self._anthropic_request(p, use_strong=use_strong, system_instruction=system_instruction)))
                
                if self.groq_api_key:
                    cloud_sequence.append(("Groq", lambda p: self.get_fast_tactical_response(p, system_instruction=system_instruction)))
                
                if self.hf_client:
                    cloud_sequence.append(("HuggingFace", lambda p: self._huggingface_request(p, use_strong=use_strong, system_instruction=system_instruction)))

                # Add smaller providers / OpenRouter / etc.
                for name, client in [("DeepSeek", self.deepseek_client), ("OpenRouter", self.openrouter_client), ("Together", self.together_client)]:
                    if client:
                        cloud_sequence.append((name, lambda p, c=client, n=name: self._generic_openai_request(p, c, n, use_strong, system_instruction=system_instruction)))

                if self.cohere_client:
                    cloud_sequence.append(("Cohere", lambda p: self._cohere_request(p, use_strong=use_strong, system_instruction=system_instruction)))
                
                if self.bedrock_session:
                    cloud_sequence.append(("AWS Bedrock", lambda p: self._bedrock_request(p, use_strong=use_strong, system_instruction=system_instruction)))

                if self.nvidia_nim_api_key:
                    cloud_sequence.append(("Kimi", lambda p: self._kimi_request(p, thinking=use_strong, system_instruction=system_instruction)))

                # Exhaustive scan of all configured cloud APIs
                for name, provider_fn in cloud_sequence:
                    try:
                        self.logger.info(f"[CLOUD_SCAN] Falling back to {name}...")
                        await self._notify_fallback(name)
                        res = await provider_fn(prompt)
                        span.set_attribute("model_provider", name.lower().replace(" ", "_"))
                        return res
                    except Exception as e:
                        errors.append(f"{name}: {e}")

            if self.nvidia_nim_api_key:
                try:
                    await self._notify_fallback("Kimi (k2.5)")
                    res = await self._kimi_request(prompt, thinking=use_strong)
                    span.set_attribute("model_provider", "kimi")
                    return res
                except Exception as e:
                    errors.append(f"Kimi: {e}")
                    self.logger.warning("Kimi failed: %s", e)

            error_msg = "All inference providers failed: " + "; ".join(errors)
            span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
            raise RuntimeError(error_msg)

    async def get_structured_plan(self, prompt: str, system_instruction: str = "") -> Dict[str, Any]:
        """
        Utility to get a JSON-formatted execution plan from the LLM.
        Forces JSON mode and handles parsing failovers.
        """
        # Ensure the prompt asks for JSON if it doesn't already
        if "json" not in prompt.lower():
            prompt += "\n\nIMPORTANT: Return only a valid JSON object with a 'steps' key."

        res = await self.get_response(prompt, system_instruction=system_instruction)
        try:
            import re
            # Extract JSON from potential markdown blocks or extra text
            json_match = re.search(r'\{.*\}', res, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return json.loads(res)
        except Exception as e:
            self.logger.error(f"Failed to parse structured plan: {e} | Raw: {res[:200]}")
            return {"steps": []}

    async def refine_plan(self, objective: str, original_plan: List[Dict], results: str, feedback: str, failed_tasks: List[str]) -> Dict[str, Any]:
        """
        Self-correction logic: Asks the model to refine a failed plan.
        """
        prompt = f"""
        OBJECTIVE: {objective}
        ORIGINAL PLAN: {json.dumps(original_plan)}
        RESULTS SO FAR: {results}
        FEEDBACK: {feedback}
        FAILED TASKS: {failed_tasks}

        Please analyze why the plan failed and provide a refined JSON plan ('steps') to complete the objective.
        """
        return await self.get_structured_plan(prompt)

    async def get_fast_tactical_response(self, prompt: str, system_instruction: str = "") -> str:
        if not self.groq_api_key:
             return await self._gemini_request(prompt, use_pro=False, system_instruction=system_instruction)
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        headers = {"Authorization": f"Bearer {self.groq_api_key}", "Content-Type": "application/json"}
        payload = {"model": "llama-3.3-70b-versatile", "messages": messages, "temperature": 0.2, "max_tokens": 1024}
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception:
                return await self._gemini_request(prompt, use_pro=False, system_instruction=system_instruction)

    async def generate_speech(self, text: str, voice_id: str = "pNInz6obpgDQGcFmaJgB") -> bytes:
        if not self.elevenlabs_api_key: raise RuntimeError("ElevenLabs credentials missing.")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": self.elevenlabs_api_key, "Content-Type": "application/json"}
        payload = {"text": text, "model_id": "eleven_monolingual_v1"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.content

    async def generate_image(self, prompt: str) -> str:
        if not self.midjourney_api_key: raise RuntimeError("Midjourney credentials missing.")
        url = "https://api.imagineapi.dev/v1/generations"
        headers = {"Authorization": f"Bearer {self.midjourney_api_key}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json={"prompt": prompt}, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("url") or data.get("id")

    async def generate_video(self, prompt: str, image_url: str = None) -> str:
        if not self.runway_api_key: raise RuntimeError("Runway credentials missing.")
        url = "https://api.runwayml.com/v1/image_to_video" if image_url else "https://api.runwayml.com/v1/text_to_video"
        headers = {"Authorization": f"Bearer {self.runway_api_key}", "X-Runway-Version": "2024-11-06"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json={"promptText": prompt, "model": "gen3a_turbo"}, headers=headers)
            resp.raise_for_status()
            return resp.json().get("id")

    async def check_health(self) -> Dict[str, Any]:
        results = {}
        # 0. Ollama (local primary)
        if self.ollama_ready:
            try:
                await self._ollama_request("Hi", use_strong=False)
                results["ollama"] = {"status": "HEALTHY"}
            except Exception as e:
                results["ollama"] = {"status": "UNSTABLE", "error": type(e).__name__}
        else:
            results["ollama"] = {"status": "NOT_RUNNING"}

        # 0b. LM Studio (local fallback)
        if self.lm_studio_client:
            try:
                await self._lm_studio_request("Hi")
                results["lm_studio"] = {"status": "HEALTHY"}
            except Exception as e:
                results["lm_studio"] = {"status": "UNSTABLE", "error": type(e).__name__}

        # 0c. HuggingFace
        if self.hf_client:
            try:
                await self._huggingface_request("Hi")
                results["huggingface"] = {"status": "HEALTHY"}
            except Exception as e:
                results["huggingface"] = {"status": "UNSTABLE", "error": type(e).__name__}

        # Cloud checks...
        if self.gemini_flash:
            try:
                await self._gemini_request("Hi")
                results["gemini"] = {"status": "HEALTHY"}
            except Exception:
                results["gemini"] = {"status": "UNSTABLE"}
        
        return results
