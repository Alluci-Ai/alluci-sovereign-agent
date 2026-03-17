import json
import logging
import asyncio
from ..logging_config import get_logger
import math
import httpx
from typing import Literal, Dict, Any, List

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

# Specialized Multi-Modal Providers (Conceptual Stubs for Integration)
GROQ_AVAILABLE = True
ELEVENLABS_AVAILABLE = True
SUNO_AVAILABLE = True
MIDJOURNEY_AVAILABLE = True
RUNWAY_AVAILABLE = True
KIMI_AVAILABLE = True
TOGETHER_AVAILABLE = True
COHERE_AVAILABLE = True
BOTO3_AVAILABLE = True

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

class ModelRouter:
    """
    Routes inference requests with failover chain: Gemini → OpenAI → Anthropic.
    """
    def __init__(self, settings):
        self.logger = get_logger("ModelRouter")
        self.settings = settings
        
        # Primary: Gemini
        self.gemini_flash = None
        self.gemini_pro = None
        if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_flash = genai.GenerativeModel("gemini-2.0-flash")
            self.gemini_pro = genai.GenerativeModel("gemini-2.5-pro-preview-05-06") # Using 2.5 Pro for maximum reasoning stability
            self.logger.info("Gemini models initialized (primary).")

        # Failover 1: OpenAI / GitHub Models
        self.openai_client = None
        if OPENAI_AVAILABLE and settings.OPENAI_API_KEY:
            base_url = None
            if settings.OPENAI_API_KEY.startswith("github_pat_"):
                base_url = "https://models.inference.ai.azure.com"
                self.logger.info("Configuring OpenAI client for GitHub Models endpoint.")
            
            self.openai_client = openai.AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url=base_url
            )
            self.logger.info("OpenAI client initialized (failover 1).")

        # Failover 2: Anthropic
        self.anthropic_client = None
        if ANTHROPIC_AVAILABLE and settings.ANTHROPIC_API_KEY:
            self.anthropic_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.logger.info("Anthropic client initialized (failover 2).")

        # Specialized: Groq (High-Speed LPU)
        self.groq_api_key = getattr(settings, "GROQ_API_KEY", None)

        # Specialized: ElevenLabs (Voice)
        self.elevenlabs_api_key = getattr(settings, "ELEVENLABS_API_KEY", None)

        # Specialized: Image/Video
        self.midjourney_api_key = getattr(settings, "MIDJOURNEY_API_KEY", None)
        self.runway_api_key = getattr(settings, "RUNWAY_API_KEY", None)

        # Specialized: Kimi (NVIDIA NIM)
        self.nvidia_nim_api_key = getattr(settings, "NVIDIA_NIM_API_KEY", None)

        # Failover 3: DeepSeek (via GitHub Models or Direct)
        self.deepseek_client = None
        if OPENAI_AVAILABLE and settings.DEEPSEEK_API_KEY:
            base_url = "https://api.deepseek.com" # Default
            if settings.DEEPSEEK_API_KEY.startswith("github_pat_"):
                base_url = "https://models.inference.ai.azure.com"
                self.logger.info("Configuring DeepSeek client for GitHub Models endpoint.")
            
            self.deepseek_client = openai.AsyncOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=base_url
            )
            self.logger.info("DeepSeek client initialized (failover 3).")

        # Failover 4: OpenRouter (Universal Adapter)
        self.openrouter_client = None
        if OPENAI_AVAILABLE and settings.OPENROUTER_API_KEY:
            self.openrouter_client = openai.AsyncOpenAI(
                api_key=settings.OPENROUTER_API_KEY,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://polytope.local", 
                    "X-Title": "Polytope Sovereign OS"
                }
            )
            self.logger.info("OpenRouter client initialized (failover 4).")

        # Failover 5: LM Studio (Local OpenAI-Compatible)
        self.lm_studio_client = None
        if OPENAI_AVAILABLE and getattr(settings, "LM_STUDIO_URL", None):
            self.lm_studio_client = openai.AsyncOpenAI(
                api_key="lm-studio", # Dummy key
                base_url=settings.LM_STUDIO_URL
            )
            self.logger.info("LM Studio client initialized (failover 5).")

        # Failover 6: Together AI
        self.together_client = None
        if OPENAI_AVAILABLE and getattr(settings, "TOGETHER_API_KEY", None):
            self.together_client = openai.AsyncOpenAI(
                api_key=settings.TOGETHER_API_KEY,
                base_url="https://api.together.xyz/v1"
            )
            self.logger.info("Together AI client initialized (failover 6).")

        # Failover 7: Cohere
        self.cohere_client = None
        if COHERE_AVAILABLE and getattr(settings, "COHERE_API_KEY", None):
            self.cohere_client = cohere.AsyncClient(api_key=settings.COHERE_API_KEY)
            self.logger.info("Cohere client initialized (failover 7).")

        # Failover 8: AWS Bedrock (async via aioboto3)
        self.bedrock_session = None
        if BOTO3_AVAILABLE and getattr(settings, "AWS_ACCESS_KEY_ID", None):
            self.bedrock_session = aioboto3.Session(
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
                region_name=getattr(settings, "AWS_REGION", "us-east-1"),
            )
            self.logger.info("AWS Bedrock session initialized via aioboto3 (failover 8).")

    async def _gemini_request(self, prompt: str, use_pro: bool = False, json_mode: bool = False) -> str:
        """Primary inference via Gemini."""
        model = self.gemini_pro if use_pro else self.gemini_flash
        if not model:
            raise RuntimeError("Gemini not configured")
        
        generation_config = {}
        if json_mode:
            generation_config = {"response_mime_type": "application/json"}
        
        response = await model.generate_content_async(prompt, generation_config=generation_config)
        return response.text

    async def _openai_request(self, prompt: str, use_strong: bool = False, json_mode: bool = False) -> str:
        """Failover 1: OpenAI."""
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
        """Failover 2: Anthropic."""
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
        """NVIDIA NIM integration for Kimi k2.5 with thinking/reasoning capability."""
        if not self.nvidia_nim_api_key:
            raise RuntimeError("NVIDIA NIM API Key missing")

        invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.nvidia_nim_api_key}",
            "Accept": "application/json"
        }
        payload = {
            "model": "moonshotai/kimi-k2.5",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 16384,
            "temperature": 1.00,
            "top_p": 1.00,
            "stream": False,
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
        response = await self.cohere_client.chat(
            model=model,
            message=prompt,
            max_tokens=4096
        )
        return response.text

    async def _bedrock_request(self, prompt: str, use_strong: bool = False) -> str:
        """Failover 8: AWS Bedrock — fully async via aioboto3."""
        if not self.bedrock_session:
            raise RuntimeError("AWS Bedrock not configured")

        model_id = (
            "anthropic.claude-3-sonnet-20240229-v1:0"
            if use_strong
            else "anthropic.claude-3-haiku-20240307-v1:0"
        )
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}]
        }).encode("utf-8")

        async with self.bedrock_session.client("bedrock-runtime") as client:
            response = await client.invoke_model(
                body=body,
                modelId=model_id,
                accept="application/json",
                contentType="application/json",
            )
            response_body = await response["body"].read()
            data = json.loads(response_body)
            return data["content"][0]["text"]

    async def _notify_fallback(self, model_name: str):
        """Broadcasts a fallback event to connected clients."""
        if hasattr(self, 'ws_gateway') and self.ws_gateway:
            try:
                await self.ws_gateway.broadcast_event('model.fallback', {
                    "fallback_model": model_name
                })
            except Exception as e:
                self.logger.error(f"Failed to broadcast fallback event: {e}")

    async def get_response(self, prompt: str, complexity: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM", psi: float = 0.0) -> str:
        """Get a response with automatic failover across providers."""
        from ..tracing_config import get_tracer
        from opentelemetry import trace
        tracer = get_tracer("Inference.Router")

        with tracer.start_as_current_span("get_response") as span:
            span.set_attribute("complexity", complexity)
            span.set_attribute("psi", psi)

            # AAP-002: ψ-Modulated Model Routing via KCM Hyperbolic Penalty.
            # High Tension (ψ > 0.7) triggers cosh() penalty on Strong models,
            # forcing routing to Light/deterministic models for safety.
            use_strong = (complexity == "HIGH")
            use_tactical = False
            
            if psi > 0.0:
                # KCM Hyperbolic Penalty: cosh(ψ) × latency
                strong_penalty = math.cosh(psi) * 3000.0  # Strong model ~3s latency
                light_penalty = math.cosh(psi) * 200.0    # Light model ~200ms latency
                
                if strong_penalty > 2.0 * light_penalty and psi > 0.7:
                    # High tension: force tactical/light model
                    use_tactical = True
                    use_strong = False
                    self.logger.info(f"[KCM] ψ={psi:.2f} → Routing to Light model (penalty={strong_penalty:.0f} vs {light_penalty:.0f})")
                elif psi > 0.8:
                    # Very high tension but no extreme penalty: still use strong for stability
                    use_strong = True
            
            if not use_tactical:
                use_strong = use_strong or (complexity == "HIGH") or (psi > 0.8)
            
            # Only activate JSON mode when the prompt explicitly requests JSON output
            import re
            json_mode = bool(re.search(
                r'\b(return|output|respond\s+with|give\s+me|provide|format\s+as|reply\s+in)\b[^.]*\bjson\b',
                prompt.lower()
            ))
            errors = []

            # KCM Tactical Shortcut: if high-tension routing selected "light",
            # attempt Groq LPU first for sub-second deterministic response
            if use_tactical and self.groq_api_key:
                try:
                    self.logger.info("[KCM] Tactical routing → Groq LPU")
                    span.set_attribute("model_provider", "groq")
                    return await self.get_fast_tactical_response(prompt)
                except Exception as e:
                    errors.append(f"Groq (tactical): {e}")
                    span.add_event("Groq tactical failover")
                    self.logger.warning(f"Tactical Groq failed, falling through: {e}")

            # Attempt 1: Gemini
            if self.gemini_flash or self.gemini_pro:
                try:
                    res = await self._gemini_request(prompt, use_pro=use_strong, json_mode=json_mode)
                    span.set_attribute("model_provider", "gemini")
                    return res
                except Exception as e:
                    errors.append(f"Gemini: {e}")
                    span.add_event("Gemini failover", attributes={"error": str(e)})
                    self.logger.warning(f"Gemini failed, attempting failover: {e}")

            # Attempt 2: OpenAI
            if self.openai_client:
                try:
                    await self._notify_fallback("OpenAI (GPT-4o)")
                    res = await self._openai_request(prompt, use_strong=use_strong, json_mode=json_mode)
                    span.set_attribute("model_provider", "openai")
                    return res
                except Exception as e:
                    errors.append(f"OpenAI: {e}")
                    span.add_event("OpenAI failover", attributes={"error": str(e)})
                    self.logger.warning(f"OpenAI failed, attempting failover: {e}")

            # Attempt 3: Anthropic
            if self.anthropic_client:
                try:
                    await self._notify_fallback("Anthropic (Claude 3.7)")
                    res = await self._anthropic_request(prompt, use_strong=use_strong)
                    span.set_attribute("model_provider", "anthropic")
                    return res
                except Exception as e:
                    errors.append(f"Anthropic: {e}")
                    span.add_event("Anthropic failover", attributes={"error": str(e)})
                    self.logger.warning(f"Anthropic failed: {e}")

            # Attempt 4: DeepSeek
            if self.deepseek_client:
                try:
                    await self._notify_fallback("DeepSeek (R1 / Chat)")
                    # Use DeepSeek-R1 for GitHub Models, deepseek-chat for direct
                    model = "DeepSeek-R1" if "azure" in str(self.deepseek_client.base_url) else "deepseek-chat"
                    response = await self.deepseek_client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=4096
                    )
                    span.set_attribute("model_provider", "deepseek")
                    return response.choices[0].message.content
                except Exception as e:
                    errors.append(f"DeepSeek: {e}")
                    span.add_event("DeepSeek failover", attributes={"error": str(e)})
                    self.logger.warning(f"DeepSeek failed: {e}")

            # Attempt 5: OpenRouter
            if self.openrouter_client:
                try:
                    await self._notify_fallback("OpenRouter (Llama 3.3)")
                    # Using a more standard model for OpenRouter failover to ensure stability
                    model = "meta-llama/llama-3.3-70b-instruct"
                    response = await self.openrouter_client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=4096
                    )
                    span.set_attribute("model_provider", "openrouter")
                    return response.choices[0].message.content
                except Exception as e:
                    errors.append(f"OpenRouter: {e}")
                    span.add_event("OpenRouter failover", attributes={"error": str(e)})
                    self.logger.warning(f"OpenRouter failed: {e}")

            # Attempt 6: LM Studio
            if self.lm_studio_client:
                try:
                    await self._notify_fallback("LM Studio (Local)")
                    response = await self.lm_studio_client.chat.completions.create(
                        model="model-identifier", # LM Studio usually uses whatever is loaded
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=2048
                    )
                    span.set_attribute("model_provider", "lm_studio")
                    return response.choices[0].message.content
                except Exception as e:
                    errors.append(f"LM Studio: {e}")
                    span.add_event("LM Studio failover", attributes={"error": str(e)})
                    self.logger.warning(f"LM Studio failed: {e}")

            # Attempt 7: Together AI
            if self.together_client:
                try:
                    await self._notify_fallback("Together (Llama-3-70B)")
                    model = "meta-llama/Llama-3-70b-chat-hf"
                    response = await self.together_client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=4096
                    )
                    span.set_attribute("model_provider", "together")
                    return response.choices[0].message.content
                except Exception as e:
                    errors.append(f"Together: {e}")
                    span.add_event("Together failover", attributes={"error": str(e)})
                    self.logger.warning(f"Together failed: {e}")

            # Attempt 8: Cohere
            if self.cohere_client:
                try:
                    await self._notify_fallback("Cohere (Command R+)")
                    res = await self._cohere_request(prompt, use_strong=use_strong)
                    span.set_attribute("model_provider", "cohere")
                    return res
                except Exception as e:
                    errors.append(f"Cohere: {e}")
                    span.add_event("Cohere failover", attributes={"error": str(e)})
                    self.logger.warning(f"Cohere failed: {e}")

            # Attempt 9: AWS Bedrock
            if self.bedrock_session:
                try:
                    await self._notify_fallback("AWS Bedrock (Claude 3)")
                    res = await self._bedrock_request(prompt, use_strong=use_strong)
                    span.set_attribute("model_provider", "bedrock")
                    return res
                except Exception as e:
                    errors.append(f"AWS Bedrock: {e}")
                    span.add_event("Bedrock failover", attributes={"error": str(e)})
                    self.logger.warning(f"AWS Bedrock failed: {e}")

            # Attempt 10: Kimi (Failover for reasoning)
            if self.nvidia_nim_api_key:
                try:
                    await self._notify_fallback("Kimi (k2.5)")
                    res = await self._kimi_request(prompt, thinking=use_strong)
                    span.set_attribute("model_provider", "kimi")
                    return res
                except Exception as e:
                    errors.append(f"Kimi: {e}")
                    span.add_event("Kimi failover", attributes={"error": str(e)})
                    self.logger.warning(f"Kimi failed: {e}")

            error_msg = f"All inference providers failed: {'; '.join(errors)}"
            span.set_status(trace.Status(trace.StatusCode.ERROR, error_msg))
            raise RuntimeError(error_msg)

    # --- Specialized Multi-Modal Audio/Video/Image Synthesis Targets ---
    
    async def get_fast_tactical_response(self, prompt: str) -> str:
        """Groq LPU integration for sub-second tactical decision-making."""
        if not self.groq_api_key:
             self.logger.warning("Groq unavailable, falling back to Flash.")
             return await self._gemini_request(prompt, use_pro=False)

        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2, # Lower temp for tactical accuracy
            "max_tokens": 1024
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                self.logger.error(f"Groq request failed: {e}")
                return await self._gemini_request(prompt, use_pro=False)

    async def generate_speech(self, text: str, voice_id: str = "pNInz6obpgDQGcFmaJgB") -> bytes: # Default: Adam
        """ElevenLabs integration for emotionally resonant voice synthesis."""
        if not self.elevenlabs_api_key:
            raise RuntimeError("ElevenLabs credentials missing.")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_api_key
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.content
            except Exception as e:
                self.logger.error(f"ElevenLabs TTS failed: {e}")
                raise RuntimeError(f"ElevenLabs error: {e}")

    async def generate_image(self, prompt: str) -> str:
        """Midjourney/ImagineAPI integration for manifestation."""
        if not self.midjourney_api_key:
            raise RuntimeError("Midjourney credentials missing.")

        # Using ImagineAPI.dev structure as a production-ready standard
        url = "https://api.imagineapi.dev/v1/generations"
        headers = {
            "Authorization": f"Bearer {self.midjourney_api_key}",
            "Content-Type": "application/json"
        }
        payload = {"prompt": prompt}

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                # Returns the result URL or ID
                return data.get("url") or data.get("id")
            except Exception as e:
                self.logger.error(f"Midjourney generation failed: {e}")
                raise RuntimeError(f"Midjourney error: {e}")

    async def generate_video(self, prompt: str, image_url: str = None) -> str:
        """RunwayML Gen-3 integration for temporal genesis."""
        if not self.runway_api_key:
            raise RuntimeError("Runway credentials missing.")

        url = "https://api.runwayml.com/v1/image_to_video" if image_url else "https://api.runwayml.com/v1/text_to_video"
        headers = {
            "Authorization": f"Bearer {self.runway_api_key}",
            "Content-Type": "application/json",
            "X-Runway-Version": "2024-11-06"
        }
        payload = {
            "promptText": prompt,
            "model": "gen3a_turbo"
        }
        if image_url:
            payload["promptImage"] = image_url

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data.get("id") # Returns task ID for polling
            except Exception as e:
                self.logger.error(f"RunwayML generation failed: {e}")
                raise RuntimeError(f"RunwayML error: {e}")

    async def get_structured_plan(self, objective: str) -> Dict[str, Any]:
        """Specific helper to force a JSON plan from the LLM."""
        prompt = f"""
        You are the Planner for an Autonomous Executive Agent.
        Objective: "{objective}"
        
        Break this objective down into a list of executable steps.
        Available Tools: "web_search", "summarize", "analyze_data", "system_query", "filesystem".
        
        Return ONLY valid JSON with this schema:
        {{
            "steps": [
                {{ "id": "step_1", "description": "Search for X", "tool": "web_search", "dependencies": [] }},
                {{ "id": "step_2", "description": "Summarize findings", "tool": "summarize", "dependencies": ["step_1"] }}
            ]
        }}
        """
        try:
            response_text = await self.get_response(prompt, complexity="MEDIUM")
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            self.logger.warning("Plan response was not valid JSON, attempting extraction...")
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"steps": []}
        except Exception as e:
            self.logger.error(f"Planning failed: {e}")
            return {"steps": []}
            
    async def refine_plan(self, objective: str, original_plan: List[Dict[str, Any]], execution_results: str, critic_feedback: str, failed_tasks: List[str]) -> Dict[str, Any]:
        """
        Self-Correction Loop: Generates an improved plan based on failure analysis.
        """
        prompt = f"""
        SYSTEM: You are the Strategic Correction Engine.
        CONTEXT: An autonomous agent attempted a task and failed validation.
        
        OBJECTIVE: "{objective}"
        
        PRIOR PLAN: {json.dumps(original_plan)}
        RESULTS: {execution_results}
        FAILED TASKS: {json.dumps(failed_tasks)}
        CRITIC FEEDBACK: "{critic_feedback}"
        
        INSTRUCTION: Generate a REVISED plan to satisfy the objective.
        - Fix logic errors in failed tasks.
        - Add verification steps if the critic noted missing accuracy.
        - Remove redundant steps.
        
        TOOLS: "web_search", "summarize", "analyze_data", "system_query", "filesystem".
        
        OUTPUT: JSON schema {{ "steps": [ {{ "id": "...", "description": "...", "tool": "...", "dependencies": [] }} ] }}
        """
        try:
            response_text = await self.get_response(prompt, complexity="HIGH")
            return json.loads(response_text)
        except Exception as e:
            self.logger.error(f"Plan refinement failed: {e}")
            return {"steps": []}

    async def critique_result(self, objective: str, result: str) -> Dict[str, Any]:
        prompt = f"""
        Objective: {objective}
        Result: {result}
        
        Rate the success of this result from 0.0 to 1.0. 
        Return JSON: {{ "score": 0.0, "feedback": "reasoning" }}
        """
        try:
            response_text = await self.get_response(prompt, complexity="MEDIUM")
            return json.loads(response_text)
        except Exception as e:
            self.logger.error(f"Critic failure: {e}")
            return {"score": 0.0, "feedback": "Critic failed to evaluate results due to an internal error."}

    async def check_health(self) -> Dict[str, Any]:
        """Verifies health of all configured model providers with detailed errors."""
        results = {}
        test_prompt = "Hello"
        
        # 1. Gemini
        if self.gemini_flash:
            try:
                await self._gemini_request(test_prompt)
                results["gemini"] = {"status": "HEALTHY"}
            except Exception as e:
                self.logger.error(f"Gemini health check failed: {e}")
                results["gemini"] = {"status": "UNSTABLE", "error": type(e).__name__}
        
        # 2. OpenAI / GitHub
        if self.openai_client:
            try:
                await self._openai_request(test_prompt, use_strong=False)
                results["openai"] = {"status": "HEALTHY"}
            except Exception as e:
                self.logger.error(f"OpenAI health check failed: {e}")
                results["openai"] = {"status": "UNSTABLE", "error": type(e).__name__}

        # 3. Anthropic
        if self.anthropic_client:
            try:
                await self._anthropic_request(test_prompt, use_strong=False)
                results["anthropic"] = {"status": "HEALTHY"}
            except Exception as e:
                self.logger.error(f"Anthropic health check failed: {e}")
                results["anthropic"] = {"status": "UNSTABLE", "error": type(e).__name__}

        # 4. DeepSeek
        if self.deepseek_client:
            try:
                model = "DeepSeek-R1" if "azure" in str(self.deepseek_client.base_url) else "deepseek-chat"
                await self.deepseek_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": test_prompt}],
                    max_tokens=5
                )
                results["deepseek"] = {"status": "HEALTHY"}
            except Exception as e:
                self.logger.error(f"DeepSeek health check failed: {e}")
                results["deepseek"] = {"status": "UNSTABLE", "error": type(e).__name__}

        # 5. Kimi
        if self.nvidia_nim_api_key:
            try:
                await self._kimi_request(test_prompt, thinking=False)
                results["kimi"] = {"status": "HEALTHY"}
            except Exception as e:
                self.logger.error(f"Kimi health check failed: {e}")
                results["kimi"] = {"status": "UNSTABLE", "error": type(e).__name__}

        # 6. Groq
        if self.groq_api_key:
            try:
                await self.get_fast_tactical_response(test_prompt)
                results["groq"] = {"status": "HEALTHY"}
            except Exception as e:
                self.logger.error(f"Groq health check failed: {e}")
                results["groq"] = {"status": "UNSTABLE", "error": type(e).__name__}

        # 7. OpenRouter
        if self.openrouter_client:
            try:
                await self.openrouter_client.chat.completions.create(
                    model="google/gemini-2.0-flash-001",
                    messages=[{"role": "user", "content": test_prompt}],
                    max_tokens=5
                )
                results["openrouter"] = {"status": "HEALTHY"}
            except Exception as e:
                self.logger.error(f"OpenRouter health check failed: {e}")
                results["openrouter"] = {"status": "UNSTABLE", "error": type(e).__name__}

        # 8. AWS Bedrock
        if self.bedrock_session:
            try:
                await self._bedrock_request(test_prompt, use_strong=False)
                results["bedrock"] = {"status": "HEALTHY"}
            except Exception as e:
                self.logger.error(f"Bedrock health check failed: {e}")
                results["bedrock"] = {"status": "UNSTABLE", "error": type(e).__name__}

        return results
