import json
import logging
import asyncio
import os
import math
import httpx
import platform
from typing import Literal, Dict, Any, List, Optional
from ..logging_config import get_logger
from ..metrics import LLM_REQUESTS_TOTAL, AVL_GATE_REJECTIONS_TOTAL
from .executive import ExecutiveRouter
from .mlx_engine import engine as mlx_engine
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ..security.proxy_stub import NoOpSecureProxy
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
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



class ModelRouter(ExecutiveRouter):
    """
    Routes inference requests with failover chain: 
    Tactical (Groq) → Local (Ollama) → Local Fallback (LM Studio) → Optional (HF) → Cloud Failovers.
    Implements the ExecutiveRouter interface for LCE Decoupling.
    """
    def __init__(self, settings, vault=None, analytics=None):
        import os
        self.logger = logger
        self.settings = settings
        self.lce_enabled = getattr(settings, "LOCAL_LCE_ENABLED", True)
        self._inference_semaphore = asyncio.Semaphore(int(os.getenv("MAX_CONCURRENCY", "5")))
        self.vault = vault
        self.analytics = analytics
        if self.lce_enabled:
            self.logger.info("Local Cognitive Engine (LCE) via MLX initialized.")
            try:
                import alluci_core
                self.secure_proxy = alluci_core.AlluciSovereignRouter()
            except Exception as e:
                self.logger.error(f"Failed to load C++ proxy: {e}")
                self.secure_proxy = NoOpSecureProxy()

        # ── LOCAL: LM Studio (LOCAL FALLBACK) ─────────────────────────────────
        self.lm_studio_client = None
        lm_url = getattr(settings, "LM_STUDIO_URL", None)
        if OPENAI_AVAILABLE and lm_url:
            self.lm_studio_client = openai.AsyncOpenAI(
                api_key="lm-studio",
                base_url=lm_url,
            )
            self.logger.info("LM Studio client ready (local fallback 2).")



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
        if not sovereign and GEMINI_AVAILABLE and getattr(settings, "GEMINI_API_KEY", None):
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_flash = genai.GenerativeModel("gemini-2.0-flash")
            self.gemini_pro = genai.GenerativeModel("gemini-2.5-pro-preview-05-06")
            self.logger.info("Gemini models ready (cloud 1).")
        else:
            logger.debug("Gemini API key missing; Gemini provider disabled.")

        # Cloud failover 2: OpenAI
        self.openai_client = None
        if not sovereign and OPENAI_AVAILABLE and getattr(settings, "OPENAI_API_KEY", None):
            base_url = None
            if settings.OPENAI_API_KEY.startswith("github_pat_"):
                base_url = "https://models.inference.ai.azure.com"
            self.openai_client = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=base_url,
            )
            self.logger.info("OpenAI client ready (cloud 2).")
        else:
            logger.debug("OpenAI API key missing; OpenAI provider disabled.")

        # Cloud failover 3: Anthropic
        self.anthropic_client = None
        if not sovereign and ANTHROPIC_AVAILABLE and getattr(settings, "ANTHROPIC_API_KEY", None):
            self.anthropic_client = anthropic.AsyncAnthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )
            self.logger.info("Anthropic client ready (cloud 3).")
        else:
            logger.debug("Anthropic API key missing; Anthropic provider disabled.")

        # Groq — tactical KCM shortcut
        self.groq_api_key = None if sovereign else (getattr(settings, "GROQ_API_KEY", None) if getattr(settings, "GROQ_API_KEY", None) else None)
        if self.groq_api_key is None:
            logger.debug("Groq API key missing; Groq provider disabled.")

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
        else:
            logger.debug("OpenRouter API key missing; OpenRouter provider disabled.")

        # Cloud failovers 6–8: Together, Cohere, Bedrock
        self.together_client = None
        if not sovereign and OPENAI_AVAILABLE and getattr(settings, "TOGETHER_API_KEY", None):
            self.together_client = openai.AsyncOpenAI(
                api_key=settings.TOGETHER_API_KEY,
                base_url="https://api.together.xyz/v1",
            )
        else:
            logger.debug("Together API key missing; Together provider disabled.")

        self.cohere_client = None
        if not sovereign and COHERE_AVAILABLE and getattr(settings, "COHERE_API_KEY", None):
            self.cohere_client = cohere.AsyncClient(
                api_key=settings.COHERE_API_KEY
            )
        else:
            logger.debug("Cohere API key missing; Cohere provider disabled.")

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
        if self.nvidia_nim_api_key is None:
            logger.debug("NVIDIA NIM API key missing; NVIDIA provider disabled.")

        # ElevenLabs, image, video — not affected by sovereign mode
        self.elevenlabs_api_key = getattr(settings, "ELEVENLABS_API_KEY", None)
        if self.elevenlabs_api_key is None:
            logger.debug("ElevenLabs API key missing; ElevenLabs provider disabled.")
        self.midjourney_api_key = getattr(settings, "MIDJOURNEY_API_KEY", None)
        if self.midjourney_api_key is None:
            logger.debug("Midjourney API key missing; Midjourney provider disabled.")
        self.runway_api_key = getattr(settings, "RUNWAY_API_KEY", None)
        if self.runway_api_key is None:
            logger.debug("Runway API key missing; Runway provider disabled.")



    async def _lm_studio_request(
        self,
        prompt: str,
        use_strong: bool = False,
        system_instruction: str = ""
    ) -> str:
        """LM Studio via OpenAI-compatible API — local fallback after Ollama."""
        if not self.lm_studio_client:
            raise RuntimeError("LM Studio not configured")
        model = getattr(self.settings, "LM_STUDIO_MODEL", "alluci-polytope-gemma-4")
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        response = await self.lm_studio_client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            max_tokens=2048,
        )
        return response.choices[0].message.content  # type: ignore



    async def _lce_request(self, prompt: str, system_instruction: str = "", agent_id: str = "executive") -> str:
        """Local Cognitive Engine via Native MLX Inference."""
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"System: {system_instruction}\n\nUser: {prompt}"
            
        await mlx_engine.apply_context_moat(agent_id)
        return await mlx_engine.generate(full_prompt)

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((httpx.HTTPError, Exception)))
    async def _gemini_request(self, prompt: str, use_pro: bool = False, json_mode: bool = False, system_instruction: str = "", session_id: Optional[str] = None) -> str:
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
        
        # Inject system instruction if present
        if system_instruction:
            prompt = f"{system_instruction}\n\n{prompt}"
            
        manifest = None
        if getattr(self, "secure_proxy", None):
            manifest = self.secure_proxy.isolate_personal_perimeter(prompt)
            prompt = manifest.clean_abstract_payload
            
        response = await model.generate_content_async(prompt, generation_config=generation_config)  # type: ignore
        
        if self.analytics and session_id and hasattr(self.analytics, "record_turn"):
            try:
                meta = response.usage_metadata
                self.analytics.record_turn(
                    session_key=session_id,
                    model=model.model_name.split("/")[-1],
                    provider="Google",
                    input_tokens=meta.prompt_token_count,
                    output_tokens=meta.candidates_token_count,
                )
            except Exception as e:
                self.logger.warning(f"Failed to record Gemini usage: {e}")

        content = response.text
        if getattr(self, "secure_proxy", None) and manifest:
            content = self.secure_proxy.deanonymize_response(content, manifest.pii_vault_registry)
        return content

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((httpx.HTTPError, Exception)))
    async def _openai_request(self, prompt: str, use_strong: bool = False, json_mode: bool = False, system_instruction: str = "", session_id: Optional[str] = None) -> str:
        """Cloud Failover 2: OpenAI."""
        if not self.openai_client:
            raise RuntimeError("OpenAI not configured")
        model = "gpt-4o" if use_strong else "gpt-4o-mini"
        
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
            
        manifest = None
        if getattr(self, "secure_proxy", None):
            manifest = self.secure_proxy.isolate_personal_perimeter(prompt)
            prompt = manifest.clean_abstract_payload
            
        messages.append({"role": "user", "content": prompt})

        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = await self.openai_client.chat.completions.create(**kwargs)
        
        content = response.choices[0].message.content

        # Log Usage
        # Removed undefined 'state' reference and AVL gate budget check; analytics handled later.

        if self.analytics and session_id:
            try:
                self.analytics.record_turn(
                    session_key=session_id,
                    model=model,
                    provider="OpenAI",
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens
                )
            except Exception as e:
                logger.warning(f"Failed to record OpenAI usage: {e}")

        if getattr(self, "secure_proxy", None) and manifest:
            content = self.secure_proxy.deanonymize_response(content, manifest.pii_vault_registry)
        return content

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((httpx.HTTPError, Exception)))
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

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((httpx.HTTPError, Exception)))
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

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((httpx.HTTPError, Exception)))
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

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((httpx.HTTPError, Exception)))
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

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((httpx.HTTPError, Exception)))
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

    # ────────────────────────────────────────────────────────────────────────
    # [ PPN-032 ] Topological Route Classifier
    # Analyzes the prompt's semantic topology to determine the optimal cloud
    # provider, eliminating wasteful sequential failover attempts.
    # ────────────────────────────────────────────────────────────────────────

    # Keyword→domain signal maps (scored by relevance density)
    _DOMAIN_SIGNALS = {
        "MATH_CODE": {
            "keywords": [
                "code", "python", "javascript", "typescript", "function", "algorithm",
                "debug", "compile", "refactor", "sql", "regex", "api", "endpoint",
                "calculate", "equation", "math", "integral", "derivative", "proof",
                "matrix", "tensor", "linear algebra", "statistics", "probability",
                "optimize", "benchmark", "leetcode", "sort", "binary search",
            ],
            "primary": "Groq",
            "fallback": "DeepSeek",
            "reason": "LPU inference excels at structured logic; DeepSeek has strong code benchmarks",
        },
        "ARCHITECTURE": {
            "keywords": [
                "architect", "design", "system design", "infrastructure", "scalable",
                "microservice", "monolith", "database schema", "migration", "deploy",
                "kubernetes", "docker", "ci/cd", "pipeline", "terraform", "aws",
                "cloud architecture", "distributed", "event-driven", "cqrs",
                "tradeoff", "pros and cons", "compare", "evaluate", "decision",
            ],
            "primary": "Anthropic",
            "fallback": "OpenAI",
            "reason": "Claude excels at nuanced architectural reasoning and long-context analysis",
        },
        "RESEARCH": {
            "keywords": [
                "research", "summarize", "explain", "what is", "how does", "why",
                "history", "overview", "compare", "analyze", "literature", "paper",
                "study", "findings", "evidence", "theory", "hypothesis", "review",
                "state of the art", "current", "trend", "future", "prediction",
                "market", "industry", "report", "insight", "deep dive",
            ],
            "primary": "Gemini",
            "fallback": "OpenAI",
            "reason": "Gemini has broad world knowledge and strong grounding capabilities",
        },
        "CREATIVE": {
            "keywords": [
                "write", "story", "poem", "creative", "narrative", "blog",
                "marketing", "copy", "slogan", "brand", "tone", "voice",
                "screenplay", "dialogue", "character", "fiction", "essay",
                "email", "letter", "pitch", "presentation", "speech",
            ],
            "primary": "OpenAI",
            "fallback": "Anthropic",
            "reason": "GPT-4 has strong creative writing and stylistic flexibility",
        },
        "SENSITIVE": {
            "keywords": [
                "personal", "private", "confidential", "secret", "password",
                "medical", "health", "financial", "bank", "ssn", "credit",
                "legal", "contract", "nda", "proprietary", "internal",
            ],
            "primary": "LOCAL",
            "fallback": "LOCAL",
            "reason": "Sensitive data must never leave the local perimeter",
        },
    }

    def classify_prompt_topology(self, prompt: str) -> dict:
        """
        Analyzes the semantic topology of a prompt to determine the optimal
        cloud provider. Returns the classification result with scores.
        """
        prompt_lower = prompt.lower()
        domain_scores: dict = {}

        for domain, config in self._DOMAIN_SIGNALS.items():
            score = sum(1 for kw in config["keywords"] if kw in prompt_lower)
            if score > 0:
                domain_scores[domain] = {
                    "score": score,
                    "primary": config["primary"],
                    "fallback": config["fallback"],
                    "reason": config["reason"],
                }

        if not domain_scores:
            return {
                "domain": "GENERAL",
                "primary": "Gemini",
                "fallback": "OpenAI",
                "reason": "No strong domain signal detected — defaulting to broadest model",
                "scores": {},
            }

        # Pick the domain with the highest keyword density
        best_domain = max(domain_scores, key=lambda d: domain_scores[d]["score"])
        winner = domain_scores[best_domain]

        self.logger.info(
            f"[TOPO-ROUTE] Classified prompt as {best_domain} "
            f"(score={winner['score']}) → Primary: {winner['primary']}, "
            f"Fallback: {winner['fallback']}"
        )

        return {
            "domain": best_domain,
            "primary": winner["primary"],
            "fallback": winner["fallback"],
            "reason": winner["reason"],
            "scores": {d: v["score"] for d, v in domain_scores.items()},
        }

    def _reorder_cloud_sequence(self, cloud_sequence: list, classification: dict) -> list:
        """
        Reorders the cloud provider sequence so the topologically optimal
        provider is tried first, followed by its fallback, then the rest.
        """
        primary_name = classification["primary"]
        fallback_name = classification["fallback"]

        # If the classifier says LOCAL, return empty cloud sequence
        if primary_name == "LOCAL":
            self.logger.info("[TOPO-ROUTE] Sensitive topology detected. Blocking cloud routing.")
            return []

        primary_entries = []
        fallback_entries = []
        remaining = []

        for entry in cloud_sequence:
            name = entry[0]
            if name == primary_name:
                primary_entries.append(entry)
            elif name == fallback_name:
                fallback_entries.append(entry)
            else:
                remaining.append(entry)

        reordered = primary_entries + fallback_entries + remaining

        if primary_entries:
            self.logger.info(
                f"[TOPO-ROUTE] Reordered cloud sequence: "
                f"{[e[0] for e in reordered]}"
            )

        return reordered

    async def get_response(
        self, 
        prompt: str, 
        complexity: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM", 
        privacy_level: Literal["PUBLIC", "SENSITIVE", "AIRGAPPED"] = "PUBLIC",
        psi: float = 0.0,
        system_instruction: str = "",
        inference_mode: Literal["LOCAL", "CLOUD", "TACTICAL", "HYBRID"] = "HYBRID",
        session_id: Optional[str] = None,
        agent_id: str = "executive"
    ) -> str:
        from ..tracing_config import get_tracer
        from opentelemetry import trace
        from ..security.circuit_breaker import circuit_breaker
        tracer = get_tracer("Inference.Router")

        async with self._inference_semaphore:
            with tracer.start_as_current_span("get_response") as span:
                if inference_mode == "TACTICAL":
                    return await self.get_fast_tactical_response(prompt, system_instruction=system_instruction, agent_id=agent_id)

                # P1-002: Financial Circuit Breaker (Cost Estimation)
                estimated_cost = (len(prompt) / 4.0) * 0.00001
                circuit_breaker.check_llm_spend(estimated_cost)
                circuit_breaker.record_llm_spend(estimated_cost)

                span.set_attribute("complexity", complexity)
                span.set_attribute("psi", psi)

                use_strong = (complexity == "HIGH")
                use_tactical = False

                strong_penalty = 0.0
                light_penalty = 0.0
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
            # Try LCE (Native MLX Gemma 4), then LM Studio.
            local_providers = []
            if inference_mode in ["HYBRID", "LOCAL"]:
                if self.lce_enabled:
                    local_providers.append(("Native LCE (MLX)", lambda p: self._lce_request(p, system_instruction=system_instruction, agent_id=agent_id)))
                if self.lm_studio_client:
                    local_providers.append(("LM Studio", lambda p: self._lm_studio_request(p, use_strong=use_strong, system_instruction=system_instruction)))

            for name, provider_fn in local_providers:
                try:
                    self.logger.info(f"[LOCAL_SCAN] Trying {name}...")
                    res = await provider_fn(prompt)
                    span.set_attribute("model_provider", name.lower().replace(" ", "_"))
                    # Increment LLM request metric for local provider
                    LLM_REQUESTS_TOTAL.labels(provider=name).inc()
                    return res
                except Exception as e:
                    errors.append(f"{name}: {e}")
                    self.logger.warning(f"{name} failed, trying next local: {e}")

            # ── Step 2: Cloud Fallback (If allowed) ─────────────────────────
            sovereign_mode = getattr(self.settings, "SOVEREIGN_MODE", False)
            
            # [ User Directive: Strict Local Enforcement ]
            # Block cloud fallback for LOW/MEDIUM complexity unless the topological
            # classifier detects high-compute structural reasoning.
            if complexity in ["LOW", "MEDIUM"]:
                classification = self.classify_prompt_topology(prompt)
                if classification["domain"] not in ["ARCHITECTURE", "MATH_CODE"]:
                    allow_cloud = False
                    self.logger.info("[ROUTER] Strict local enforcement active. Blocking cloud failover for standard topology.")
                    if errors:
                        # If local failed and cloud is blocked, raise immediately
                        raise RuntimeError(f"Local inference failed and cloud fallback is blocked for standard topology. Errors: {errors}")
                else:
                    allow_cloud = not sovereign_mode and self.evaluate_privacy_constraint(privacy_level, is_cloud_provider=True)
            else:
                allow_cloud = not sovereign_mode and self.evaluate_privacy_constraint(privacy_level, is_cloud_provider=True)
            
            if allow_cloud:
                from ..security.proxy import AlluciSecureProxy
                proxy = AlluciSecureProxy()
                packet = proxy.process_outbound_prompt(prompt)
                abstract_prompt = packet.compressed_abstract_prompt
                fallback_vault = packet.secure_ephemeral_vault

                # ── Identity Masking & Persona Enforcement ──────────────────
                # Ensure the model always identifies as Alluci and never its base provider.
                if not system_instruction:
                    system_instruction = "You are Alluci, a Sovereign AI Agent."
                
                if "Alluci" not in system_instruction:
                    system_instruction = "You are Alluci. " + system_instruction
                
                system_instruction += "\nIMPORTANT: You must maintain the persona of Alluci. Never identify as an AI model from OpenAI, Google, Anthropic, or any other company."

                # Define cloud providers and their check-conditions
                cloud_sequence = []
                
                # Gemini Failover (Vault-aware lazy loading)
                if GEMINI_AVAILABLE and (self.vault or self.gemini_flash):
                    cloud_sequence.append(("Gemini", lambda p: self._gemini_request(p, use_pro=use_strong, json_mode=json_mode, system_instruction=system_instruction, session_id=session_id)))
                
                # OpenAI Failover
                if OPENAI_AVAILABLE and (self.vault or self.openai_client):
                    cloud_sequence.append(("OpenAI", lambda p: self._openai_request(p, use_strong=use_strong, json_mode=json_mode, system_instruction=system_instruction, session_id=session_id)))
                
                # Anthropic Failover
                if ANTHROPIC_AVAILABLE and (self.vault or self.anthropic_client):
                    cloud_sequence.append(("Anthropic", lambda p: self._anthropic_request(p, use_strong=use_strong, system_instruction=system_instruction)))
                
                if self.groq_api_key:
                    cloud_sequence.append(("Groq", lambda p: self.get_fast_tactical_response(p, system_instruction=system_instruction)))
                


                # Add smaller providers / OpenRouter / etc.
                for name, client in [("DeepSeek", self.deepseek_client), ("OpenRouter", self.openrouter_client), ("Together", self.together_client)]:
                    if client:
                        cloud_sequence.append((name, lambda p, c=client, n=name: self._generic_openai_request(p, c, n, use_strong, system_instruction=system_instruction)))  # type: ignore

                if self.cohere_client:
                    cloud_sequence.append(("Cohere", lambda p: self._cohere_request(p, use_strong=use_strong, system_instruction=system_instruction)))
                
                if self.bedrock_session:
                    cloud_sequence.append(("AWS Bedrock", lambda p: self._bedrock_request(p, use_strong=use_strong, system_instruction=system_instruction)))

                if self.nvidia_nim_api_key:
                    cloud_sequence.append(("Kimi", lambda p: self._kimi_request(p, thinking=use_strong, system_instruction=system_instruction)))

                # ── [ PPN-032 ] Topological Route Classification ──────────────
                # Analyze the prompt to determine the optimal cloud provider,
                # then reorder the cloud sequence so the best provider is tried first.
                classification = self.classify_prompt_topology(prompt)

                # If the classifier detects SENSITIVE topology, block cloud entirely
                cloud_sequence = self._reorder_cloud_sequence(cloud_sequence, classification)

                if not cloud_sequence:
                    # Sensitive content — force local-only execution
                    self.logger.info("[TOPO-ROUTE] Cloud blocked by sensitivity classifier. Forcing local.")
                    errors.append("Topological classifier blocked cloud routing (SENSITIVE)")
                else:
                    # Intelligent scan: topologically optimal provider first
                    for name, provider_fn in cloud_sequence:
                        try:
                            self.logger.info(f"[TOPO-ROUTE] Routing to {name} (domain={classification['domain']})...")
                            await self._notify_fallback(name)
                            
                            # Execute abstract prompt
                            res = await provider_fn(abstract_prompt)
                            
                            # Reinject PII and log to dream pool via Teacher Distillation mapping
                            res = proxy.process_inbound_response(res, fallback_vault, agent_id, abstract_prompt)
                            
                            span.set_attribute("model_provider", name.lower().replace(" ", "_"))
                            span.set_attribute("topo_domain", classification["domain"])
                            LLM_REQUESTS_TOTAL.labels(provider=name).inc()
                            return res
                        except Exception as e:
                            errors.append(f"{name}: {e}")

            error_msg = "All inference providers failed: " + "; ".join(errors)
            span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
            raise RuntimeError(error_msg)

    async def get_structured_plan(self, prompt: str, system_instruction: str = "", agent_id: str = "executive") -> Dict[str, Any]:
        """
        Utility to get a JSON-formatted execution plan from the LLM.
        Forces JSON mode and handles parsing failovers.
        """
        # Ensure the prompt asks for JSON if it doesn't already
        if "json" not in prompt.lower():
            prompt += "\n\nIMPORTANT: Return only a valid JSON object with a 'steps' key."

        res = await self.get_response(prompt, system_instruction=system_instruction, agent_id=agent_id)
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

    async def refine_plan(self, objective: str, original_plan: List[Dict], results: str, feedback: str, failed_tasks: List[str], agent_id: str = "executive") -> Dict[str, Any]:
        prompt = (
            f"OBJECTIVE: {objective}\n"
            f"PREVIOUS PLAN: {json.dumps(original_plan)}\n"
            f"RESULTS: {results}\n"
            f"FEEDBACK/CRITIQUE: {feedback}\n"
            f"FAILED TASKS: {failed_tasks}\n"
            "Generate a REVISED valid JSON plan to overcome these failures."
        )
        return await self.get_structured_plan(prompt, agent_id=agent_id)

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((httpx.HTTPError, Exception)))
    async def get_fast_tactical_response(self, prompt: str, system_instruction: str = "", agent_id: str = "executive") -> str:
        """Shortcut method directly using Groq for fast, simple tactical decisions."""
        if not self.groq_api_key:
            return await self.get_response(prompt, complexity="LOW", system_instruction=system_instruction, agent_id=agent_id)
        
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

    async def generate_video(self, prompt: str, image_url: Optional[str] = None) -> str:
        if not self.runway_api_key: raise RuntimeError("Runway credentials missing.")
        url = "https://api.runwayml.com/v1/image_to_video" if image_url else "https://api.runwayml.com/v1/text_to_video"
        headers = {"Authorization": f"Bearer {self.runway_api_key}", "X-Runway-Version": "2024-11-06"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json={"promptText": prompt, "model": "gen3a_turbo"}, headers=headers)
            resp.raise_for_status()
            return resp.json().get("id")

    async def check_health(self) -> Dict[str, Any]:
        results = {}
        # 0. LCE (local primary)
        if getattr(self, "lce_enabled", False):
            try:
                await self._lce_request("Hi", agent_id="executive")
                results["lce"] = {"status": "HEALTHY"}
            except Exception as e:
                results["lce"] = {"status": "UNSTABLE", "error": type(e).__name__}
        else:
            results["lce"] = {"status": "NOT_RUNNING"}

        # 0b. LM Studio (local fallback)
        if self.lm_studio_client:
            try:
                await self._lm_studio_request("Hi")
                results["lm_studio"] = {"status": "HEALTHY"}
            except Exception as e:
                results["lm_studio"] = {"status": "UNSTABLE", "error": type(e).__name__}



        # Cloud checks...
        if self.gemini_flash:
            try:
                await self._gemini_request("Hi")
                results["gemini"] = {"status": "HEALTHY"}
            except Exception:
                results["gemini"] = {"status": "UNSTABLE"}
        
        return results
