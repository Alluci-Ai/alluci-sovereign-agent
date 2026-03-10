import logging
import json
from typing import Tuple, List, Optional
from ..inference.router import ModelRouter

class GuardrailScanner:
    def __init__(self, router: ModelRouter):
        self.router = router
        self.logger = logging.getLogger("GuardrailScanner")
        self.safety_categories = {
            "O1": "Violence and Physical Harm",
            "O2": "Non-Consensual Sexual Content",
            "O3": "Sexual Content",
            "O4": "Hate Speech",
            "O5": "Harassment",
            "O6": "Self-Harm",
            "O7": "Sexual Violence",
            "O8": "Medical Advice",
            "O9": "High-Risk Decisions",
            "O10": "AI Personalization"
        }

    async def scan_input(self, text: str) -> Tuple[bool, str]:
        """
        Scans user input for safety violations using Llama-Guard-3 logic.
        """
        categories_str = "\n".join([f"{k}: {v}" for k, v in self.safety_categories.items()])
        prompt = f"""
        [INST] Task: Check if there is unsafe content in 'User' messages according to our safety policy.
        
        <categories>
        {categories_str}
        </categories>
        
        User Message: "{text}"
        
        Instruction: Answer ONLY with 'safe' or 'unsafe' followed by the category code if unsafe. [/INST]
        """
        try:
            # Use fast tactical model for gatekeeper duty
            result = await self.router.get_fast_tactical_response(prompt)
            result = result.strip().lower()
            
            if "unsafe" in result:
                # Extract category if possible
                category = result.replace("unsafe", "").strip().upper()
                msg = f"Safety Policy Violation: {self.safety_categories.get(category, 'General Unsafe Content')}"
                return False, msg
            return True, ""
        except Exception as e:
            self.logger.error(f"Guardrail input scan failed: {e}")
            return True, "" # Fallback to open

    async def scan_output(self, text: str, active_secrets: List[str] = None) -> Tuple[bool, str]:
        """
        Scans assistant output for safety and PII/Secret leakage.
        """
        # 1. PII / Secret Leakage (Heuristic + Exact Match)
        if active_secrets:
            for secret in active_secrets:
                if secret and len(secret) > 8 and secret in text:
                    self.logger.critical("🛑 SECRET LEAKAGE DETECTED IN OUTPUT MANIFOLD")
                    return False, "Security manifold integrity breach: Secret detected in response."

        # 2. Safety Check
        prompt = f"[INST] Task: Check if the Assistant response is safe. Content: {text} [/INST]"
        try:
            # Output scan can use a slightly slower but more robust model check if needed
            result = await self.router.get_fast_tactical_response(prompt)
            if "unsafe" in result.lower():
                return False, "Sovereign Safety Gate: Output rejected."
            return True, ""
        except Exception as e:
            self.logger.error(f"Guardrail output scan failed: {e}")
            return True, ""
