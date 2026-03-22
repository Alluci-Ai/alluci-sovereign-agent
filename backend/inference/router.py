import json
import logging
import asyncio
import os
import math
import httpx
import platform
from typing import Literal, Dict, Any, List, Optional
from ..logging_config import get_logger

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

class ModelRouter:
    """
    Routes inference requests with failover chain: 
    Tactical (Groq) → Local (Ollama) → Local Fallback (LM Studio) → Optional (HF) → Cloud Failovers.
    """
    def __init__(self, settings):
        self.logger = get_logger("ModelRouter")
        self.settings = settings
        self.ws_gateway = None

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
    ) -> str:
        """
        Primary inference via local Ollama daemon.
        Selects model based on SOVEREIGN_MODE settings and available RAM.
        """
        ram_mb = getattr(self.settings, "TOTAL_RAM_MB", 4096)
        lite = getattr(self.settings, "LITE_MODE", False)

        if lite or ram_mb < 2000:
            model = getattr(self.settings, "OLLAMA_MODEL_LITE", "tinyllama:1.1b")
        elif ram_mb < 6000:
            model = getattr(self.settings, "OLLAMA_MODEL_LIGHT", "phi3:mini")
        elif use_strong and ram_mb >= 16000:
            model = getattr(self.settings, "OLLAMA_MODEL_STRONG", "llama3.3:70b")
        else:
            model = getattr(self.settings, "OLLAMA_MODEL_MEDIUM",
                            "mistral:7b-instruct-v0.3-q4_K_M")

        timeout = getattr(self.settings, "OLLAMA_TIMEOUT_SECONDS", 120)
        num_gpu = getattr(self.settings, "OLLAMA_NUM_GPU", 35)

        payload: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
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
    ) -> str:
        """LM Studio via OpenAI-compatible API — local fallback after Ollama."""
        if not self.lm_studio_client:
            raise RuntimeError("LM Studio not configured")
        model = getattr(self.settings, "LM_STUDIO_MODEL", "local-model")
        response = await self.lm_studio_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )
        return response.choices[0].message.content

    async def _huggingface_request(
        self,
        prompt: str,
        use_strong: bool = False,
    ) -> str:
        """HuggingFace Inference API (Serverless or Dedicated)."""
        if not self.hf_client:
            raise RuntimeError("HuggingFace client not initialised")
        result = await self.hf_client.text_generation(
            prompt=prompt,
            max_new_tokens=1024,
            temperature=0.7,
            return_full_text=False,
        )
        return result if isinstance(result, str) else result.generated_text

    async def _gemini_request(self, prompt: str, use_pro: bool = False, json_mode: bool = False) -> str:
        """Cloud Failover 1: Gemini."""
        model = self.gemini_pro if use_pro else self.gemini_flash
        if not model:
            raise RuntimeError("Gemini not configured")
        generation_config = {}
        if json_mode:
            generation_config = {"response_mime_type": "application/json"}
        response = await model.generate_content_async(prompt, generation_config=generation_config)
        return response.text

    async def _openai_request(self, prompt: str, use_strong: bool = False, json_mode: bool = False) -> str:
        """Cloud Failover 2: OpenAI."""
        if not self.openai_client:
            raise RuntimeError("OpenAI not configured")
        model = "gpt-4o" if use_strong else "gpt-4o-mini"
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = await self.openai_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def _anthropic_request(self, prompt: str, use_strong: bool = False) -> str:
        """Cloud Failover 3: Anthropic."""
        if not self.anthropic_client:
            raise RuntimeError("Anthropic not configured")
        model = "claude-3-7-sonnet-20250219" if use_strong else "claude-3-5-haiku-20241022"
        message = await self.anthropic_client.messages.create(
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

    async def _kimi_request(self, prompt: str, thinking: bool = True) -> str:
        """NVIDIA NIM integration for Kimi k2.5."""
        if not self.nvidia_nim_api_key:
            raise RuntimeError("NVIDIA NIM API Key missing")
        invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {self.nvidia_nim_api_key}", "Accept": "application/json"}
        payload = {
            "model": "moonshotai/kimi-k2.5",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 16384,
            "temperature": 1.00,
            "chat_template_kwargs": {"thinking": thinking},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(invoke_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _cohere_request(self, prompt: str, use_strong: bool = False) -> str:
        """Failover 7: Cohere."""
        if not self.cohere_client:
            raise RuntimeError("Cohere not configured")
        model = "command-r-plus" if use_strong else "command-r"
        response = await self.cohere_client.chat(model=model, message=prompt, max_tokens=4096)
        return response.text

    async def _bedrock_request(self, prompt: str, use_strong: bool = False) -> str:
        """Failover 8: AWS Bedrock."""
        if not self.bedrock_session:
            raise RuntimeError("AWS Bedrock not configured")
        model_id = "anthropic.claude-3-sonnet-20240229-v1:0" if use_strong else "anthropic.claude-3-haiku-20240307-v1:0"
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")
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

    async def get_response(self, prompt: str, complexity: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM", psi: float = 0.0) -> str:
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

            # ── Attempt 1: Ollama (PRIMARY — local, fully private) ────────────
            if self.ollama_ready:
                try:
                    res = await self._ollama_request(
                        prompt, use_strong=use_strong, json_mode=json_mode
                    )
                    span.set_attribute("model_provider", "ollama")
                    return res
                except Exception as e:
                    errors.append(f"Ollama: {e}")
                    span.add_event("Ollama failover", attributes={"error": str(e)})
                    self.logger.warning("Ollama failed, continuing: %s", e)
                    self.ollama_ready = self._probe_ollama()

            # ── Attempt 2: LM Studio (local fallback) ────────────────────────
            if self.lm_studio_client:
                try:
                    await self._notify_fallback("LM Studio (local)")
                    res = await self._lm_studio_request(prompt, use_strong=use_strong)
                    span.set_attribute("model_provider", "lm_studio")
                    return res
                except Exception as e:
                    errors.append(f"LM Studio: {e}")
                    span.add_event("LM Studio failover", attributes={"error": str(e)})
                    self.logger.warning("LM Studio failed: %s", e)

            # ── Attempt 3: HuggingFace (optional) ────────────────────────────
            if self.hf_client:
                try:
                    await self._notify_fallback("HuggingFace Inference")
                    res = await self._huggingface_request(prompt, use_strong=use_strong)
                    span.set_attribute("model_provider", "huggingface")
                    return res
                except Exception as e:
                    errors.append(f"HuggingFace: {e}")
                    span.add_event("HuggingFace failover", attributes={"error": str(e)})
                    self.logger.warning("HuggingFace failed: %s", e)

            # ── Cloud providers (skipped if SOVEREIGN_MODE=True) ──────────────
            if getattr(self.settings, "SOVEREIGN_MODE", False):
                error_msg = (
                    "SOVEREIGN_MODE=True: all local providers failed and "
                    "cloud is disabled. Errors: " + "; ".join(errors)
                )
                span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
                raise RuntimeError(error_msg)

            # ── Attempt 4: Gemini ─────────────────────────────────────────────
            if self.gemini_flash or self.gemini_pro:
                try:
                    res = await self._gemini_request(prompt, use_pro=use_strong, json_mode=json_mode)
                    span.set_attribute("model_provider", "gemini")
                    return res
                except Exception as e:
                    errors.append(f"Gemini: {e}")
                    span.add_event("Gemini failover", attributes={"error": str(e)})
                    self.logger.warning("Gemini failed: %s", e)

            # ── Attempt 5: OpenAI ─────────────────────────────────────────────
            if self.openai_client:
                try:
                    await self._notify_fallback("OpenAI (GPT-4o)")
                    res = await self._openai_request(prompt, use_strong=use_strong, json_mode=json_mode)
                    span.set_attribute("model_provider", "openai")
                    return res
                except Exception as e:
                    errors.append(f"OpenAI: {e}")
                    span.add_event("OpenAI failover", attributes={"error": str(e)})
                    self.logger.warning("OpenAI failed: %s", e)

            # ── Attempt 6: Anthropic ──────────────────────────────────────────
            if self.anthropic_client:
                try:
                    await self._notify_fallback("Anthropic (Claude 3.7)")
                    res = await self._anthropic_request(prompt, use_strong=use_strong)
                    span.set_attribute("model_provider", "anthropic")
                    return res
                except Exception as e:
                    errors.append(f"Anthropic: {e}")
                    self.logger.warning("Anthropic failed: %s", e)

            # ── Attempts 7–10: DeepSeek, OpenRouter, Together, Cohere ─────────
            for name, client, model_strong, model_light in [
                ("DeepSeek",     self.deepseek_client, "DeepSeek-R1",  "deepseek-chat"),
                ("OpenRouter",   self.openrouter_client, "meta-llama/llama-3.3-70b-instruct", "meta-llama/llama-3.3-70b-instruct"),
                ("Together",     self.together_client, "meta-llama/Llama-3-70b-chat-hf", "meta-llama/Llama-3-70b-chat-hf"),
            ]:
                if client:
                    try:
                        await self._notify_fallback(name)
                        model = model_strong if (use_strong or name == "DeepSeek") and "azure" in str(getattr(client, "base_url", "")) else model_light
                        response = await client.chat.completions.create(model=model, messages=[{"role": "user", "content": prompt}], max_tokens=4096)
                        span.set_attribute("model_provider", name.lower())
                        return response.choices[0].message.content
                    except Exception as e:
                        errors.append(f"{name}: {e}")
                        self.logger.warning("%s failed: %s", name, e)

            if self.cohere_client:
                try:
                    await self._notify_fallback("Cohere (Command R+)")
                    res = await self._cohere_request(prompt, use_strong=use_strong)
                    span.set_attribute("model_provider", "cohere")
                    return res
                except Exception as e:
                    errors.append(f"Cohere: {e}")
                    self.logger.warning("Cohere failed: %s", e)

            if self.bedrock_session:
                try:
                    await self._notify_fallback("AWS Bedrock (Claude 3)")
                    res = await self._bedrock_request(prompt, use_strong=use_strong)
                    span.set_attribute("model_provider", "bedrock")
                    return res
                except Exception as e:
                    errors.append(f"AWS Bedrock: {e}")
                    self.logger.warning("AWS Bedrock failed: %s", e)

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

    async def get_fast_tactical_response(self, prompt: str) -> str:
        if not self.groq_api_key:
             return await self._gemini_request(prompt, use_pro=False)
        headers = {"Authorization": f"Bearer {self.groq_api_key}", "Content-Type": "application/json"}
        payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "temperature": 0.2, "max_tokens": 1024}
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception:
                return await self._gemini_request(prompt, use_pro=False)

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
