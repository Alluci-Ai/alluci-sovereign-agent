class NoOpSecureProxy:
    """Fallback proxy that performs no sanitisation.

    All methods return the input unchanged – preserving the contract
    of the real proxy while guaranteeing safe execution.
    """

    def isolate_personal_perimeter(self, prompt: str):
        """Return a minimal manifest that carries the original prompt unchanged."""
        class Manifest:
            clean_abstract_payload = prompt
            pii_vault_registry = {}
        return Manifest()

    def deanonymize_response(self, content: str, _registry: dict):
        """Identity transformation – return content as‑is."""
        return content

    def process_outbound_prompt(self, prompt: str):
        """Mimic the real proxy's packet interface for outbound prompts."""
        class Packet:
            compressed_abstract_prompt = prompt
            secure_ephemeral_vault = {}
        return Packet()

    def process_inbound_response(self, resp, vault, agent_id, abstract):
        """Identity transformation for inbound responses."""
        return resp
