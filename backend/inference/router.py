
import json
import logging
import httpx
from typing import Literal, Dict, Any, List

logger = logging.getLogger("ModelRouter")

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


class ModelRouter:
    """
    Routes inference requests with failover chain: Gemini → OpenAI → Anthropic.
    """
    def __init__(self, settings):
        self.logger = logging.getLogger("ModelRouter")
        self.settings = settings
        
        # Primary: Gemini
        self.gemini_flash = None
        self.gemini_pro = None
        if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.gemini_flash = genai.GenerativeModel("gemini-1.5-flash-latest")
            self.gemini_pro = genai.GenerativeModel("gemini-1.5-pro-latest")
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
        
        model = "claude-3-5-sonnet-20241022" if use_strong else "claude-3-5-haiku-20241022"
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

    async def _notify_fallback(self, model_name: str):
        """Broadcasts a fallback event to connected clients."""
        if hasattr(self, 'ws_gateway') and self.ws_gateway:
            try:
                await self.ws_gateway.broadcast_event('model.fallback', {
                    "fallback_model": model_name
                })
            except Exception as e:
                self.logger.error(f"Failed to broadcast fallback event: {e}")

    async def get_response(self, prompt: str, complexity: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM") -> str:
        """Get a response with automatic failover across providers."""
        use_strong = complexity == "HIGH"
        # Only activate JSON mode when the prompt explicitly requests JSON output,
        # not just any mention of the word "json" in the content.
        import re
        json_mode = bool(re.search(
            r'\b(return|output|respond\s+with|give\s+me|provide|format\s+as|reply\s+in)\b[^.]*\bjson\b',
            prompt.lower()
        ))
        errors = []

        # Attempt 1: Gemini
        if self.gemini_flash or self.gemini_pro:
            try:
                return await self._gemini_request(prompt, use_pro=use_strong, json_mode=json_mode)
            except Exception as e:
                errors.append(f"Gemini: {e}")
                self.logger.warning(f"Gemini failed, attempting failover: {e}")

        # Attempt 2: OpenAI
        if self.openai_client:
            try:
                await self._notify_fallback("OpenAI (GPT-4o)")
                return await self._openai_request(prompt, use_strong=use_strong, json_mode=json_mode)
            except Exception as e:
                errors.append(f"OpenAI: {e}")
                self.logger.warning(f"OpenAI failed, attempting failover: {e}")

        # Attempt 3: Anthropic
        if self.anthropic_client:
            try:
                await self._notify_fallback("Anthropic (Claude 3.5)")
                return await self._anthropic_request(prompt, use_strong=use_strong)
            except Exception as e:
                errors.append(f"Anthropic: {e}")
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
                return response.choices[0].message.content
            except Exception as e:
                errors.append(f"DeepSeek: {e}")
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
                return response.choices[0].message.content
            except Exception as e:
                errors.append(f"OpenRouter: {e}")
                self.logger.warning(f"OpenRouter failed: {e}")

        # Attempt 6: Kimi (Failover for reasoning)
        if self.nvidia_nim_api_key:
            try:
                await self._notify_fallback("Kimi (k2.5)")
                return await self._kimi_request(prompt, thinking=use_strong)
            except Exception as e:
                errors.append(f"Kimi: {e}")
                self.logger.warning(f"Kimi failed: {e}")

        raise RuntimeError(f"All inference providers failed: {'; '.join(errors)}")

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

    async def generate_speech(self, text: str, voice_id: str = "default") -> bytes:
        """ElevenLabs integration for emotionally resonant voice synthesis."""
        if not self.elevenlabs_api_key:
            raise RuntimeError("ElevenLabs credentials missing.")
        # TODO: Implement actual HTTP request to ElevenLabs API
        raise NotImplementedError(
            "Speech synthesis is not yet implemented. "
            "Set ELEVENLABS_API_KEY and implement the ElevenLabs API integration."
        )

    async def generate_image(self, prompt: str) -> str:
        """Midjourney Alpha API integration for manifestation."""
        if not self.midjourney_api_key:
            raise RuntimeError("Midjourney credentials missing.")
        # TODO: Implement actual HTTP request to Midjourney API
        raise NotImplementedError(
            "Image generation is not yet implemented. "
            "Set MIDJOURNEY_API_KEY and implement the Midjourney API integration."
        )

    async def generate_video(self, prompt: str, image_url: str = None) -> str:
        """Runway Gen-4.5 / Luma integration for temporal genesis."""
        if not self.runway_api_key:
            raise RuntimeError("Runway credentials missing.")
        # TODO: Implement actual HTTP request to RunwayML API
        raise NotImplementedError(
            "Video generation is not yet implemented. "
            "Set RUNWAY_API_KEY and implement the RunwayML API integration."
        )

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

        return results
