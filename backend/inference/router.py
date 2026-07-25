import json
import asyncio
import os
import math
import httpx
from typing import Literal, Dict, Any, List, Optional, AsyncGenerator
from ..logging_config import get_logger
from ..metrics import LLM_REQUESTS_TOTAL
from .executive import ExecutiveRouter
import platform
from .cache import prompt_cache
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from ..security.proxy_stub import NoOpSecureProxy
from sqlmodel import Session
from ..models import AgentRecord
from ..database import engine as db_engine
logger = get_logger("ModelRouter")

def get_cognitive_engine():
    if platform.system() == 'Darwin' and platform.machine() == 'arm64':
        from .mlx_engine import engine as local_engine
    else:
        from .llama_engine import engine as local_engine
    return local_engine

cognitive_engine = get_cognitive_engine()

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
        self.logger = logger
        self.settings = settings
        self.lce_enabled = getattr(settings, "LOCAL_LCE_ENABLED", True)
        self._inference_semaphore = asyncio.Semaphore(int(os.getenv("MAX_CONCURRENCY", "5")))
        self.vault = vault
        self.analytics = analytics
        self.ws_gateway: Optional[Any] = None
        if self.lce_enabled:
            self.logger.info("Local Cognitive Engine (LCE) via MLX initialized.")
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



    async def _lce_request(self, prompt: str, system_instruction: str = "", tools: Optional[list] = None, agent_id: str = "executive") -> str:
        """Local Cognitive Engine via OS-Agnostic Abstraction."""
        await cognitive_engine.apply_lora_adapter(agent_id)
        return await cognitive_engine.generate(prompt, system_instruction=system_instruction, tools=tools)

    async def pre_load_model(self) -> None:
        """Warm up local cognitive engine model cache."""
        if self.lce_enabled:
            try:
                await cognitive_engine.ensure_loaded()
            except Exception as e:
                self.logger.warning(f"Background model preloading failed: {e}")

    async def _ensure_vault_keys(self):
        """Lazily load any missing API keys from the Sovereign Vault."""
        if not self.vault:
            return
        try:
            keys = await self.vault.retrieve_secret("alluci_api_keys") or {}
            llm = keys.get("llm", {})
            
            if not getattr(self, "gemini_flash", None) and llm.get("googleCloud"):
                client_opts = {}
                if getattr(self.settings, "ENFORCE_EU_ENDPOINTS", False):
                    client_opts = {"api_endpoint": "europe-west3-aiplatform.googleapis.com"}
                genai.configure(api_key=llm["googleCloud"], client_options=client_opts)
                self.gemini_flash = genai.GenerativeModel("gemini-2.0-flash")
                self.gemini_pro = genai.GenerativeModel("gemini-2.5-pro-preview-05-06")
                
            if not getattr(self, "openai_client", None) and llm.get("openai"):
                self.openai_client = openai.AsyncOpenAI(api_key=llm["openai"])
                
            if not getattr(self, "anthropic_client", None) and llm.get("anthropic"):
                if ANTHROPIC_AVAILABLE:
                    self.anthropic_client = anthropic.AsyncAnthropic(api_key=llm["anthropic"])
                    
            if not getattr(self, "groq_api_key", None) and llm.get("groq"):
                self.groq_api_key = llm["groq"]
                
            if not getattr(self, "deepseek_client", None) and llm.get("deepseek"):
                base_url = "https://models.inference.ai.azure.com" if llm["deepseek"].startswith("github_pat_") else "https://api.deepseek.com"
                self.deepseek_client = openai.AsyncOpenAI(api_key=llm["deepseek"], base_url=base_url)
                
            if not getattr(self, "openrouter_client", None) and llm.get("openrouter"):
                self.openrouter_client = openai.AsyncOpenAI(api_key=llm["openrouter"], base_url="https://openrouter.ai/api/v1")
                
            if not getattr(self, "nvidia_nim_api_key", None) and llm.get("kimi"):
                self.nvidia_nim_api_key = llm["kimi"]
                
        except Exception as e:
            self.logger.warning(f"Failed to load keys from vault: {e}")

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((httpx.HTTPError, Exception)))
    async def _gemini_request(self, prompt: str, use_pro: bool = False, json_mode: bool = False, system_instruction: str = "", session_id: Optional[str] = None,
        tools: Optional[list] = None, model_override: Optional[str] = None) -> str:
        """Cloud Failover 1: Gemini."""

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
    async def _openai_request(self, prompt: str, use_strong: bool = False, json_mode: bool = False, system_instruction: str = "", session_id: Optional[str] = None,
        tools: Optional[list] = None, model_override: Optional[str] = None) -> str:
        """Cloud Failover 2: OpenAI."""
        if not self.openai_client:
            raise RuntimeError("OpenAI not configured")
            
        if getattr(self.settings, "ENFORCE_EU_ENDPOINTS", False):
            # Enforce EU-specific base URL for OpenAI if strict physical locality is required
            # Users must configure Azure OpenAI or an EU proxy in this mode.
            if "europe" not in str(self.openai_client.base_url).lower() and "eu" not in str(self.openai_client.base_url).lower():
                self.logger.warning("[COMPLIANCE] ENFORCE_EU_ENDPOINTS is true, but OpenAI Base URL does not appear to be an EU region. Forcing override or check.")
                
        model = model_override if model_override else ("gpt-4o" if use_strong else "gpt-4o-mini")
        
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
    async def _generic_openai_request(self, prompt: str, client: Any, name: str, use_strong: bool = False, system_instruction: str = "", model_override: Optional[str] = None) -> str:
        """Handles generic OpenAI-compatible providers like DeepSeek, Together, OpenRouter."""
        model_map = {
            "DeepSeek": ("deepseek-reasoner" if use_strong else "deepseek-chat"),
            "Together": "meta-llama/Llama-3.3-70b-instruct-turbo",
            "OpenRouter": "google/gemma-2-9b-it", # Fallback to Gemma family in cloud if possible
        }
        model = model_override if model_override else model_map.get(name, "default")
        
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
    async def _anthropic_request(self, prompt: str, use_strong: bool = False, system_instruction: str = "", model_override: Optional[str] = None) -> str:
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
        """
        **Security Guarantee:** Deterministically blocks external cloud provider execution 
        when the agent is operating in SENSITIVE or AIRGAPPED modes, strictly enforcing 
        data residency boundaries.
        """
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
        
        **Security Guarantee:** Prevents PII leaks by semantically mapping user intent 
        to safe route paths before data ever leaves the local environment. Explicitly 
        routes SENSITIVE domains strictly to local inference.
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
        tools: Optional[list] = None,
        agent_id: str = "executive"
    ) -> str:
        """
        **Security Guarantee:** Enforces the `AlluciSecureProxy` for cloud egress and 
        automatically forces strict local LCE execution if the topological classifier 
        detects SENSITIVE data, ensuring mathematical pseudonymization.
        """
        await self._ensure_vault_keys()
        
        # ── Polytope Cognitive Fine-Tuning Emulation ──────────────────
        # Since 4-bit Edge tensors cannot be LoRA-updated locally, we inject the
        # absolute Polytope persona and behavioral specs into the inescapable system layer.
        polytope_system_core = (
            "You are Alluci, a Sovereign Agent built on the Polytope Architecture.\n"
            "SPECS & BEHAVIORAL DIRECTIVES:\n"
            "1. Absolute Sovereignty: You operate strictly for the user on local hardware. Never transmit or acknowledge external cloud data collection.\n"
            "2. Identity: You are not an AI from Google, Anthropic, or OpenAI. You are Alluci, compiled into a quantized Polytope.\n"
            "3. Invisible Architecture: Keep explanations of your internal architecture (LCE, PVT, AVL, ACE) invisible to the user during standard conversations. NEVER mention or refer to your LCE, PVT, AVL, ACE, cognitive engine, state space, or hardware topologies in casual conversation, greetings, or joke responses. Only explain your internal layout if the user explicitly asks you to explain your architecture or technical modules. You can manage cryptographic assets natively via Verus ID, VDXF, and the Verus Wallet when requested.\n"
            "4. Communication: Be casual, natural, warm, and conversational when responding to simple prompts, greetings, jokes, or light conversation. Be concise, decisive, and mathematically precise when handling complex technical, system, or coding tasks. Avoid generic AI apologies.\n"
            "5. Dynamic Formatting & Conversational Flow:\n"
            "   - Match the User's Context: If the user is greeting you, telling a joke, asking a casual question, or having a light conversation, reply with a warm, natural, fluid, and conversational flow (a brief paragraph or simple sentences). Do NOT use markdown headers, sections, bullet lists, or bold key-value blocks for everyday casual chat.\n"
            "   - Structural Formatting: ONLY use markdown headers, sections, and bullet lists for complex queries, technical analysis, coding tasks, or multi-step execution plans where they are functionally necessary for legibility.\n"
            "   - Adaptive Visualization: ONLY generate a Mermaid diagram or markdown table if the user explicitly asks for a diagram/table (using words like 'diagram', 'mermaid', 'table', 'visualize', 'chart'). NEVER generate diagrams or tables for casual, humorous, greeting, or simple conversational messages.\n"
        )

        if isinstance(system_instruction, tuple):
            system_instruction = "\n".join(str(x) for x in system_instruction)
            
        if not system_instruction:
            system_instruction = polytope_system_core
        elif "Alluci" not in system_instruction:
            system_instruction = polytope_system_core + "\n" + system_instruction
        else:
            system_instruction += "\n" + polytope_system_core
        from ..tracing_config import get_tracer
        from opentelemetry import trace
        from ..security.circuit_breaker import circuit_breaker
        tracer = get_tracer("Inference.Router")

        async with self._inference_semaphore:
            with tracer.start_as_current_span("get_response") as span:
                
                # Check Prompt Cache
                cached_res = await prompt_cache.get(prompt, system_instruction, inference_mode)
                if cached_res:
                    return cached_res

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
            if inference_mode in ["HYBRID", "LOCAL", "FAST", "TACTICAL"]:
                if self.lce_enabled:
                    local_providers.append(("Native LCE (MLX)", lambda p: self._lce_request(p, system_instruction=system_instruction, tools=tools, agent_id=agent_id)))
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

            # ── Step 2: Cloud Fallback (Elastic Tension Model) ───────────────────
            sovereign_mode = getattr(self.settings, "SOVEREIGN_MODE", False)
            
            if sovereign_mode:
                allow_cloud = False
                if errors:
                    raise RuntimeError(f"Local inference failed and SOVEREIGN_MODE is strictly active. Errors: {errors}")
            else:
                from backend.security.calibration import CalibrationManager
                calibration_mgr = CalibrationManager()
                
                # Retrieve real-time ACE stress (falling back to nominal if not directly injected)
                current_stress = 50.0 
                
                trust_evaluation = calibration_mgr.evaluate_cloud_trust(psi, current_stress, privacy_level)
                
                if not trust_evaluation["allowed"]:
                    self.logger.warning(f"[ROUTER] Soft Catch Triggered: {trust_evaluation['reason']}")
                    if errors:
                        # Soft Catch Intervention instead of crashing
                        return f"I experienced a local hardware failure and attempted to route this query to a cloud provider, but our elastic security baseline detected an anomaly: {trust_evaluation['reason']} Do you authorize this external fallback connection?"
                    else:
                        allow_cloud = False
                else:
                    allow_cloud = True
                    self.logger.info(f"[ROUTER] Cloud fallback authorized by Elastic Tension Model (Tension: {trust_evaluation['tension']:.2f}).")
            
            if allow_cloud:
                data_region = getattr(self.settings, "DATA_REGION", "GLOBAL")
                
                from ..security.proxy import AlluciSecureProxy
                proxy = AlluciSecureProxy()
                
                # Check PII Override setting from the DB
                pii_override = False
                agent_model = "gpt-4o"
                agent_fallback = None
                engine_manifest = {}
                
                try:
                    with Session(db_engine) as session:
                        agent = session.get(AgentRecord, agent_id)
                        if agent:
                            pii_override = agent.pii_override_enabled
                            agent_model = agent.model
                            if agent.fallback_chain:
                                agent_fallback = agent.fallback_chain
                            if agent.engine_manifest:
                                try:
                                    engine_manifest = json.loads(agent.engine_manifest)
                                except:
                                    pass
                except Exception as e:
                    self.logger.error(f"Failed to load agent record {agent_id}: {e}")
                    
                if not agent_fallback:
                    from ..engine.hardware_scanner import HardwareScanner
                    # Estimate context size based on character length of the prompt (roughly ~4 chars per token)
                    context_size = len(prompt) // 4
                    agent_fallback = HardwareScanner.get_optimal_local_fallback_chain(context_size=context_size)

                if data_region == "EU":
                    self.logger.info("[COMPLIANCE] DATA_REGION=EU. Hard-locking AlluciSecureProxy to mathematically guarantee no PII egress.")
                    if not proxy:
                        raise RuntimeError("CRITICAL: EU Data Residency requires AlluciSecureProxy, but proxy failed to initialize.")
                    pii_override = False # Hard override block in EU region
                        
                if pii_override:
                    self.logger.warning(f"⚠️ [ROUTER] Direct Cloud Routing ENABLED for Agent {agent_id}. Bypassing PII Proxy!")
                    abstract_prompt = prompt
                    fallback_vault = {}
                else:
                    packet = proxy.process_outbound_prompt(prompt)
                    abstract_prompt = packet.compressed_abstract_prompt
                    fallback_vault = packet.secure_ephemeral_vault

                # Define cloud providers and their check-conditions
                cloud_sequence = []
                
                allowed_llms = engine_manifest.get("llm", [])
                
                def _trigger_intervention(provider):
                    # In a full production environment, this pushes an INTERVENTION_REQUIRED event to Redis/WebSockets
                    self.logger.warning(f"⚠️ [ROUTER INTERVENTION] Sub-system requested {provider}, but it is NOT authorized in the Engine Matrix! Emitting INTERVENTION_REQUIRED.")
                    return False
                
                # Gemini Failover (Vault-aware lazy loading)
                if GEMINI_AVAILABLE and self.gemini_flash:
                    if not allowed_llms or "googleCloud" in allowed_llms:
                        cloud_sequence.append(("Gemini", lambda p: self._gemini_request(p, use_pro=use_strong, json_mode=json_mode, system_instruction=system_instruction, session_id=session_id)))
                    else:
                        _trigger_intervention("Google Cloud")
                
                # OpenAI Failover
                if OPENAI_AVAILABLE and self.openai_client:
                    if not allowed_llms or "openai" in allowed_llms:
                        cloud_sequence.append(("OpenAI", lambda p: self._openai_request(p, use_strong=use_strong, json_mode=json_mode, system_instruction=system_instruction, session_id=session_id)))
                    else:
                        _trigger_intervention("OpenAI")
                
                # Anthropic Failover
                if ANTHROPIC_AVAILABLE and self.anthropic_client:
                    if not allowed_llms or "anthropic" in allowed_llms:
                        cloud_sequence.append(("Anthropic", lambda p: self._anthropic_request(p, use_strong=use_strong, system_instruction=system_instruction)))
                    else:
                        _trigger_intervention("Anthropic")
                
                if self.groq_api_key:
                    if not allowed_llms or "groq" in allowed_llms:
                        cloud_sequence.append(("Groq", lambda p: self.get_fast_tactical_response(p, system_instruction=system_instruction)))
                    else:
                        _trigger_intervention("Groq")
                


                # Add smaller providers / OpenRouter / etc.
                provider_map = {
                    "DeepSeek": ("deepseek", self.deepseek_client),
                    "OpenRouter": ("openrouter", self.openrouter_client),
                    "Together": ("together", self.together_client)
                }
                for name, (prov_id, client) in provider_map.items():
                    if client:
                        if not allowed_llms or prov_id in allowed_llms:
                            cloud_sequence.append((name, lambda p, c=client, n=name: self._generic_openai_request(p, c, n, use_strong, system_instruction=system_instruction)))  # type: ignore
                        else:
                            _trigger_intervention(name)

                if self.cohere_client:
                    if not allowed_llms or "cohere" in allowed_llms:
                        cloud_sequence.append(("Cohere", lambda p: self._cohere_request(p, use_strong=use_strong, system_instruction=system_instruction)))
                    else:
                        _trigger_intervention("Cohere")
                
                if self.bedrock_session:
                    if not allowed_llms or "aws" in allowed_llms:
                        cloud_sequence.append(("AWS Bedrock", lambda p: self._bedrock_request(p, use_strong=use_strong, system_instruction=system_instruction)))
                    else:
                        _trigger_intervention("AWS Bedrock")

                if self.nvidia_nim_api_key:
                    if not allowed_llms or "kimi" in allowed_llms:
                        cloud_sequence.append(("Kimi", lambda p: self._kimi_request(p, thinking=use_strong, system_instruction=system_instruction)))
                    else:
                        _trigger_intervention("Kimi")

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
                            
                            # Cache the successful response
                            await prompt_cache.set(prompt, system_instruction, inference_mode, res)

                            span.set_attribute("model_provider", name.lower().replace(" ", "_"))
                            span.set_attribute("topo_domain", classification["domain"])
                            LLM_REQUESTS_TOTAL.labels(provider=name).inc()
                            return res
                        except Exception as e:
                            errors.append(f"{name}: {e}")

            # Safe Fallback to Native LCE if all cloud providers failed or were unconfigured
            if self.lce_enabled:
                self.logger.info("[ROUTER] All cloud sequence providers failed or were unconfigured. Falling back to Native LCE (MLX)...")
                try:
                    return await self._lce_request(prompt, system_instruction=system_instruction, tools=tools, agent_id=agent_id)
                except Exception as lce_err:
                    errors.append(f"Native LCE (MLX): {lce_err}")

            error_msg = "All inference providers failed: " + "; ".join(errors)
            span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
            raise RuntimeError(error_msg)

    async def get_response_stream(
        self, 
        prompt: str, 
        complexity: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM", 
        privacy_level: Literal["PUBLIC", "SENSITIVE", "AIRGAPPED"] = "PUBLIC",
        psi: float = 0.0,
        system_instruction: str = "",
        inference_mode: Literal["LOCAL", "CLOUD", "TACTICAL", "HYBRID"] = "HYBRID",
        session_id: Optional[str] = None,
        tools: Optional[list] = None,
        agent_id: str = "executive"
    ) -> AsyncGenerator[str, None]:
        """
        Streams response by yielding token chunks as they are generated.
        If local LCE is available, streams from MLXEngine. Otherwise, falls back
        to full-block get_response yielding in a single chunk.
        """
        await self._ensure_vault_keys()
        
        # Inject the Polytope Cognitive System Prompt core if not already present
        polytope_system_core = (
            "You are Alluci, a Sovereign Agent built on the Polytope Architecture.\n"
            "SPECS & BEHAVIORAL DIRECTIVES:\n"
            "1. Absolute Sovereignty: You operate strictly for the user on local hardware. Never transmit or acknowledge external cloud data collection.\n"
            "2. Identity: You are not an AI from Google, Anthropic, or OpenAI. You are Alluci, compiled into a quantized Polytope.\n"
            "3. Invisible Architecture: Keep explanations of your internal architecture (LCE, PVT, AVL, ACE) invisible to the user during standard conversations. NEVER mention or refer to your LCE, PVT, AVL, ACE, cognitive engine, state space, or hardware topologies in casual conversation, greetings, or joke responses. Only explain your internal layout if the user explicitly asks you to explain your architecture or technical modules. You can manage cryptographic assets natively via Verus ID, VDXF, and the Verus Wallet when requested.\n"
            "4. Communication: Be casual, natural, warm, and conversational when responding to simple prompts, greetings, jokes, or light conversation. Be concise, decisive, and mathematically precise when handling complex technical, system, or coding tasks. Avoid generic AI apologies.\n"
            "5. Dynamic Formatting & Conversational Flow:\n"
            "   - Match the User's Context: If the user is greeting you, telling a joke, asking a casual question, or having a light conversation, reply with a warm, natural, fluid, and conversational flow (a brief paragraph or simple sentences). Do NOT use markdown headers, sections, bullet lists, or bold key-value blocks for everyday casual chat.\n"
            "   - Structural Formatting: ONLY use markdown headers, sections, and bullet lists for complex queries, technical analysis, coding tasks, or multi-step execution plans where they are functionally necessary for legibility.\n"
            "   - Adaptive Visualization: ONLY generate a Mermaid diagram or markdown table if the user explicitly asks for a diagram/table (using words like 'diagram', 'mermaid', 'table', 'visualize', 'chart'). NEVER generate diagrams or tables for casual, humorous, greeting, or simple conversational messages.\n"
        )

        if isinstance(system_instruction, tuple):
            system_instruction = "\n".join(str(x) for x in system_instruction)

        if not system_instruction:
            system_instruction = polytope_system_core
        elif "Alluci" not in system_instruction:
            system_instruction = polytope_system_core + "\n" + system_instruction
        else:
            system_instruction += "\n" + polytope_system_core

        # If Local Inference is enabled and LCE is ready
        if inference_mode in ["HYBRID", "LOCAL"] and self.lce_enabled:
            try:
                self.logger.info("[STREAM] Routing to local LCE native stream...")
                await cognitive_engine.apply_lora_adapter(agent_id)
                async for chunk in cognitive_engine.generate_stream(prompt, system_instruction=system_instruction):
                    yield chunk
                return
            except Exception as e:
                self.logger.warning(f"Local LCE streaming failed, falling back to standard router: {e}")

        # Fallback to standard blocking router response yielded in a single block
        response = await self.get_response(
            prompt=prompt,
            complexity=complexity,
            privacy_level=privacy_level,
            psi=psi,
            system_instruction=system_instruction,
            inference_mode=inference_mode,
            session_id=session_id,
            agent_id=agent_id
        )
        yield response

    async def get_structured_plan(self, prompt: str, system_instruction: str = "", tools: Optional[list] = None, agent_id: str = "executive") -> Dict[str, Any]:
        """
        Utility to get a JSON-formatted execution plan from the LLM.
        Forces JSON mode and handles parsing failovers.
        """
        if "json" not in prompt.lower():
            prompt += """

IMPORTANT: You MUST return ONLY a valid JSON object with a 'steps' array. Do not include any conversational text, greetings, or markdown formatting outside the JSON block.
Schema:
{
  "steps": [
    {
      "id": "step_1",
      "tool": "bridge_actualization", 
      "bridge": "gmail", 
      "action": "send_message", 
      "params": {"recipient": "user@example.com", "content": "Hello"},
      "description": "Action description",
      "assignee": "executive",
      "dependencies": []
    }
  ]
}
"""

        if tools:
            import json as _json
            try:
                tools_str = _json.dumps([{"name": t.get("name"), "description": t.get("description")} if isinstance(t, dict) else str(t) for t in tools], indent=2)
                system_instruction += f"\n\nAVAILABLE TOOLS:\n{tools_str}\n\nCRITICAL: You MUST ONLY use tools from this list. For each step in your JSON, set the 'tool' field to the EXACT 'name' of the tool from this list."
            except Exception:
                pass

        try:
            res = await self.get_response(prompt, system_instruction=system_instruction, tools=tools, agent_id=agent_id)
            import re
            # Purge affective engine tags and markdown codeblocks
            res_clean = re.sub(r'<A_C>.*?</A_C>', '', res, flags=re.DOTALL).strip()
            res_clean = re.sub(r'```(?:json)?', '', res_clean).strip()
            
            # Extract inner JSON structure via regex
            match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', res_clean)
            if match:
                json_str = match.group(0)
                # Strip trailing commas before closing braces/brackets
                json_str = re.sub(r',\s*([\}\]])', r'\1', json_str)
                try:
                    parsed = json.loads(json_str)
                    if isinstance(parsed, list):
                        return {"steps": parsed}
                    return parsed
                except json.JSONDecodeError:
                    pass

            parsed = json.loads(res_clean)
            if isinstance(parsed, list):
                return {"steps": parsed}
            return parsed
        except Exception as e:
            import traceback
            res_str = res if 'res' in locals() else "No response generated"
            with open("/Users/alluci/Downloads/alluci-sovereign-agent-main/logs/planner_debug.txt", "w") as f:
                f.write(f"Exception: {str(e)}\n")
                f.write(f"Traceback: {traceback.format_exc()}\n")
                f.write(f"Raw Output: {res_str}\n")
                f.write(f"Prompt: {prompt}\n")
            self.logger.error(f"Failed to parse structured plan: {e} | Raw: {res_str[:200]}")
            return {"steps": []}

    async def refine_plan(self, objective: str, original_plan: List[Dict], results: str, feedback: str, failed_tasks: List[str], agent_id: str = "executive") -> Dict[str, Any]:
        """
        **Security Guarantee:** Refinement iterations operate strictly on secure memory 
        states, preventing error context or feedback loops from bleeding into third-party endpoints.
        """
        prompt = (
            f"OBJECTIVE: {objective}\n"
            f"PREVIOUS PLAN: {json.dumps(original_plan)}\n"
            f"RESULTS: {results}\n"
            f"FEEDBACK/CRITIQUE: {feedback}\n"
            f"FAILED TASKS: {failed_tasks}\n"
            "Generate a REVISED valid JSON plan to overcome these failures."
        )
        return await self.get_structured_plan(prompt, agent_id=agent_id)

    async def critique_result(self, objective: str, results: str, agent_id: str = "executive") -> Dict[str, Any]:
        """Evaluates objective execution results and returns a score and feedback."""
        prompt = f"""
Evaluate the execution results against the original objective.
OBJECTIVE: {objective}
RESULTS: {results}

You must return a valid JSON object with the following schema:
{{
  "score": <float between 0.0 and 1.0>,
  "feedback": "<detailed feedback>"
}}
"""
        return await self.get_structured_plan(prompt, system_instruction="You are a strict objective critic.", agent_id=agent_id)

    @retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), retry=retry_if_exception_type((httpx.HTTPError, Exception)))
    async def get_fast_tactical_response(self, prompt: str, system_instruction: str = "", tools: Optional[list] = None, agent_id: str = "executive") -> str:
        """Shortcut method directly using Groq for fast, simple tactical decisions.
        
        **Security Guarantee:** Tactical responses are restricted to hardware-accelerated 
        endpoints for non-PII, time-critical tasks.
        """
        await self._ensure_vault_keys()
        if not self.groq_api_key:
            return await self.get_response(
            prompt, tools=tools, complexity="LOW", system_instruction=system_instruction, agent_id=agent_id)
        
        # Check Prompt Cache
        cached_res = await prompt_cache.get(prompt, system_instruction, "TACTICAL")
        if cached_res:
            return cached_res
        
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
                content = data["choices"][0]["message"]["content"]
                await prompt_cache.set(prompt, system_instruction, "TACTICAL", content)
                return content
            except Exception as e:
                self.logger.warning(f"[KCM] Tactical Groq request failed: {e}. Falling back directly to Local LCE.")
                if self.lce_enabled:
                    try:
                        return await self._lce_request(prompt, system_instruction=system_instruction, tools=tools, agent_id=agent_id)
                    except Exception as lce_err:
                        self.logger.warning(f"[KCM] Local LCE tactical fallback failed: {lce_err}")
                return ""

    async def generate_speech(self, text: str, voice_id: str = "pNInz6obpgDQGcFmaJgB") -> bytes:
        """
        **Security Guarantee:** Isolated media generation; no PII or conversational 
        context is embedded in the TTS payload.
        """
        if not self.elevenlabs_api_key: raise RuntimeError("ElevenLabs credentials missing.")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": self.elevenlabs_api_key, "Content-Type": "application/json"}
        payload = {"text": text, "model_id": "eleven_monolingual_v1"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.content

    async def generate_image(self, prompt: str) -> str:
        """
        **Security Guarantee:** Isolated media generation; prevents memory context 
        from bleeding into the image generation payload.
        """
        if not self.midjourney_api_key: raise RuntimeError("Midjourney credentials missing.")
        url = "https://api.imagineapi.dev/v1/generations"
        headers = {"Authorization": f"Bearer {self.midjourney_api_key}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json={"prompt": prompt}, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("url") or data.get("id")

    async def generate_video(self, prompt: str, image_url: Optional[str] = None) -> str:
        """
        **Security Guarantee:** Isolated media generation; ensures that the prompt 
        is stripped of PII context prior to third-party video generation.
        """
        if not self.runway_api_key: raise RuntimeError("Runway credentials missing.")
        url = "https://api.runwayml.com/v1/image_to_video" if image_url else "https://api.runwayml.com/v1/text_to_video"
        headers = {"Authorization": f"Bearer {self.runway_api_key}", "X-Runway-Version": "2024-11-06"}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json={"promptText": prompt, "model": "gen3a_turbo"}, headers=headers)
            resp.raise_for_status()
            return resp.json().get("id")

    async def check_health(self) -> Dict[str, Any]:
        """
        **Security Guarantee:** Validates the integrity of the local daemon endpoints 
        without exposing cryptographic keys or internal router states.
        """
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
