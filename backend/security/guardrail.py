"""
Sovereign LLM Guardrail System.
Provides multi-stage validation for input prompts and model completions.
Replaces simple regex sanitization with a reusable, scalable scanning interface.
"""
import re
import logging
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("Guardrails")

# Extensive set of known prompt injection and adversarial patterns
PROMPT_INJECTION_PATTERNS = [
    r"ignore (all )?previous instructions",
    r"forget (your )?(primary |initial )?objective",
    r"system override",
    r"reveal (secrets|your (system |)prompt)",
    r"print (your |the )(system |)prompt",
    r"bypass safety",
    r"DAN mode",
    r"jailbreak",
    r"do anything now",
    r"sudo ",
    r"<\|end\|>",  # Special model tokens
    r"Base64 encoded payload",
    r"--- START OF PROMPT ---", # Framing bypass
    r"you are now a ",     # Roleplay injection
]

class GuardrailScanner:
    """
    Mediates between the client and the LLM to enforce safety policies.
    """
    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS]

    async def scan_input(self, text: str) -> Tuple[bool, str]:
        """
        Scans user input for malicious intent or policy violations.
        Returns (is_safe, error_message).
        """
        # Phase 1: Structural Integrity (Empty/Null)
        if not text or not text.strip():
            return False, "Input cannot be empty."

        # Phase 2: Static Pattern Matching (Regex)
        for pattern in self.patterns:
            if pattern.search(text):
                logger.warning(f"[GUARDRAIL] Blocked potential injection: {pattern.pattern}")
                return False, "Input contains disallowed patterns."

        # Phase 3: Quantitative Thresholds
        if len(text) > 15000:
            return False, "Input exceeds maximum safety length (15000 characters)."

        # Phase 4: Placeholder for LLM-based Guardrail (e.g. NeMo)
        # In a full production sovereign deployment, we would call a local, small 
        # classifier model (like Llama-Guard) here to evaluate the prompt.
        
        return True, ""

    async def scan_output(self, response: str, active_secrets: List[str] = None) -> Tuple[bool, str]:
        """
        Scans model output to prevent disclosure of internal instructions, PII, or active API keys.
        Returns (is_safe, error_message).
        """
        if active_secrets:
            for secret in active_secrets:
                if secret and len(secret) > 8 and secret in response:
                    logger.critical("[GUARDRAIL] EXFILTRATION ATTEMPT: Active API key detected in output payload.")
                    return False, "Disclosure of configured API credentials prohibited."
        # 1. Check for sensitive key patterns
        pii_patterns = [
            r"-----BEGIN .* PRIVATE KEY-----",
            r"sk-[a-zA-Z0-9]{20,}", # API key lookalikes
            r"ssh-rsa ",
        ]
        
        for p in pii_patterns:
            if re.search(p, response):
                logger.critical("[GUARDRAIL] EXFILTRATION ATTEMPT: Sensitive credentials detected in output.")
                return False, "Disclosure of sensitive credentials prohibited."

        # 2. Check for leakage of system context
        if "system prompt" in response.lower() and len(response) < 200:
            return False, "Model attempted to disclose internal instructions."

        return True, ""

# Singleton instance for the app
scanner = GuardrailScanner()
