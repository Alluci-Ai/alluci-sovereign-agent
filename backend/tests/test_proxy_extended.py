import pytest
pytestmark = pytest.mark.unit

# backend/tests/test_proxy_extended.py
"""Tests for AlluciSecureProxy privacy filtering behavior.
These tests cover:
- basic placeholder replacement and vault storage,
- preservation of whitelist tokens,
- handling of large Base64 strings,
- nested JSON payloads,
- robustness against malformed JSON.
"""

import os
import json
import base64

from backend.security.proxy import AlluciSecureProxy
from backend.security.pii_config import WHITELIST_TOKENS, PII_SCRUBBER


def _run_proxy(prompt: str):
    proxy = AlluciSecureProxy()
    packet = proxy.process_outbound_prompt(prompt)
    return packet


def test_privacy_filter_registry_exists():
    proxy = AlluciSecureProxy()
    # Ensure the property exists and returns the expected list
    assert hasattr(proxy, "privacy_filter_registry")
    registry = proxy.privacy_filter_registry
    assert isinstance(registry, list)
    assert registry == PII_SCRUBBER


def test_basic_replacement_and_vault():
    prompt = "I am John Doe and my email is test@example.com."
    packet = _run_proxy(prompt)
    # The actual data should be scrubbed and replaced with placeholders
    assert "John Doe" not in packet.compressed_abstract_prompt
    assert "test@example.com" not in packet.compressed_abstract_prompt
    # Vault should contain the original values keyed by the generated tokens
    vault = packet.secure_ephemeral_vault
    assert any("ALLUCI_NAME_TOKEN" in k for k in vault)
    assert any("ALLUCI_EMAIL_TOKEN" in k for k in vault)
    # Ensure the values match the original data
    assert any(v == "John Doe" for v in vault.values())
    assert any(v == "test@example.com" for v in vault.values())


def test_whitelist_preservation():
    # Use a token that is in the default whitelist
    whitelist_token = next(iter(WHITELIST_TOKENS))
    prompt = f"This is a safe token: {whitelist_token} and a private name John Doe."
    packet = _run_proxy(prompt)
    # Whitelist token must remain in the compressed prompt unchanged
    assert whitelist_token in packet.compressed_abstract_prompt
    # It must not appear in the vault
    assert whitelist_token not in packet.secure_ephemeral_vault.values()


def test_large_base64_string():
    # Create a 20KB random Base64 string (not matched by any regex, but should not crash)
    raw_bytes = os.urandom(15_000)  # 15KB raw => ~20KB base64
    b64_str = base64.b64encode(raw_bytes).decode()
    prompt = f"Here is some data: {b64_str} and a name token John Doe."
    packet = _run_proxy(prompt)
    # Ensure processing completes and name token is still handled
    assert "John Doe" not in packet.compressed_abstract_prompt
    assert any("ALLUCI_NAME_TOKEN" in k for k in packet.secure_ephemeral_vault)
    # The large base64 string should stay untouched (no regex matches)
    assert b64_str in packet.compressed_abstract_prompt


def test_nested_json_payload():
    payload = {
        "user": {
            "name": "Jane Smith",
            "contact": {"email": "jane.smith@example.com"},
            "metadata": {"token": "deadbeef"},  # whitelist example
        }
    }
    prompt = json.dumps(payload)
    packet = _run_proxy(prompt)
    # Ensure both name and email tokens are replaced
    assert "Jane Smith" not in packet.compressed_abstract_prompt
    assert "jane.smith@example.com" not in packet.compressed_abstract_prompt
    # Whitelist token should remain
    assert "deadbeef" in packet.compressed_abstract_prompt
    # Vault should contain both original placeholders
    vault_values = set(packet.secure_ephemeral_vault.values())
    assert "Jane Smith" in vault_values
    assert "jane.smith@example.com" in vault_values


def test_malformed_json_handling():
    # Intentionally broken JSON (missing closing brace)
    prompt = "{\"user\": {\"name\": \"John Doe\""
    # The proxy works on raw strings, so it should still replace the token
    packet = _run_proxy(prompt)
    assert "John Doe" not in packet.compressed_abstract_prompt
    # No exception should be raised
    assert isinstance(packet, AlluciSecureProxy.process_outbound_prompt.__annotations__["return"])

