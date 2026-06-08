import re
from typing import Dict, List, Tuple
from .pii_config import PII_SCRUBBER, WHITELIST_TOKENS

class OptimizedSovereignPacket:
    def __init__(self, compressed_abstract_prompt: str, secure_ephemeral_vault: Dict[str, str]):
        self.compressed_abstract_prompt = compressed_abstract_prompt
        self.secure_ephemeral_vault = secure_ephemeral_vault


class AlluciSecureProxy:
    """
    Zero-Trust Bidirectional Topological Anonymization Proxy.
    Extracts PII/secrets into an ephemeral vault, sending only abstract logic to the cloud.
    """

    def __init__(self):
        # No initialization needed; configuration is imported.
        pass

    @property
    def privacy_filter_registry(self) -> List[Tuple[str, re.Pattern]]:
        """Compatibility shim returning the global ``PII_SCRUBBER``.

        Existing code accessing ``self.privacy_filter_registry`` will continue
        to work.
        """
        return PII_SCRUBBER

    @property
    def registry(self) -> List[Tuple[str, re.Pattern]]:
        """Backward‑compatible alias for ``privacy_filter_registry``."""
        return self.privacy_filter_registry
        
    def process_outbound_prompt(self, raw_user_prompt: str) -> OptimizedSovereignPacket:
        """
        Step 1: Extract private data and generate abstract query layouts.
        """
        text_working_buffer = raw_user_prompt
        secure_ephemeral_vault = {}
        token_instance_id = 1001
        
        for placeholder, regex_rule in self.privacy_filter_registry:
            matches = list(regex_rule.finditer(text_working_buffer))
            
            # Find all unique matches to avoid double-replacing same strings with different IDs
            unique_matches = set(m.group(0) for m in matches)
            
            for exact_match in unique_matches:
                # Skip tokens that are in the whitelist (safe to expose)
                if exact_match in WHITELIST_TOKENS:
                    continue
                composite_key = f"{placeholder}_{token_instance_id}"
                # Safe-store private data in volatile memory
                secure_ephemeral_vault[composite_key] = exact_match
                # Swap raw information out for abstract system placeholders
                text_working_buffer = text_working_buffer.replace(exact_match, composite_key)
                token_instance_id += 1

        # Run graph token pruning to optimize message length
        compressed_prompt = self._compress_token_density(text_working_buffer)
        return OptimizedSovereignPacket(compressed_prompt, secure_ephemeral_vault)
        
    def process_inbound_response(self, raw_cloud_response: str, fallback_vault: Dict[str, str], agent_id: str, abstract_prompt: str) -> str:
        """
        Step 2: Merge private context back into incoming API responses.
        Logs the abstract_prompt -> raw_cloud_response to the Agent's dream pool.
        """
        final_output_buffer = raw_cloud_response
        for placeholder_token, private_value in fallback_vault.items():
            final_output_buffer = final_output_buffer.replace(placeholder_token, private_value)
            
        # Log to the sub-agent's dream pool
        self._log_to_dream_pool(agent_id, abstract_prompt, raw_cloud_response)
            
        return final_output_buffer
        
    def _compress_token_density(self, target_text: str) -> str:
        """
        Prune conversational filler to minimize token use and lower API costs.
        """
        noise_words = ["please", "kindly", "could", "you", "help", "me", "optimize", "now"]
        mutated_text = target_text
        
        for word in noise_words:
            # Case insensitive exact word boundary replace
            mutated_text = re.sub(rf"\b{word}\b", "", mutated_text, flags=re.IGNORECASE)
            
        # Strip out excess line breaks and spaces
        mutated_text = re.sub(r"\s+", " ", mutated_text).strip()
        
        return mutated_text

    def _log_to_dream_pool(self, agent_id: str, abstract_prompt: str, cloud_response: str):
        import os
        import json
        from datetime import datetime, timezone
        
        pool_dir = os.path.join(os.getcwd(), "models", "dream_pools")
        os.makedirs(pool_dir, exist_ok=True)
        
        safe_agent_id = re.sub(r'[^a-zA-Z0-9_-]', '_', agent_id)
        pool_path = os.path.join(pool_dir, f"agent_{safe_agent_id}_dream_pool.dat")
        
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": abstract_prompt,
            "response": cloud_response
        }
        
        try:
            with open(pool_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"Failed to write to dream pool for {agent_id}: {e}")
