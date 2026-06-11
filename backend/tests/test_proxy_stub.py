import pytest
pytestmark = pytest.mark.unit

from backend.security.proxy_stub import NoOpSecureProxy

def test_noop_secure_proxy_isolate_personal_perimeter():
    proxy = NoOpSecureProxy()
    prompt = "Hello John Doe"
    manifest = proxy.isolate_personal_perimeter(prompt)
    assert manifest.clean_abstract_payload == prompt
    assert manifest.pii_vault_registry == {}

def test_noop_secure_proxy_deanonymize_response():
    proxy = NoOpSecureProxy()
    content = "Hello John Doe"
    result = proxy.deanonymize_response(content, {})
    assert result == content

def test_noop_secure_proxy_process_outbound_prompt():
    proxy = NoOpSecureProxy()
    prompt = "Hello John Doe"
    packet = proxy.process_outbound_prompt(prompt)
    assert packet.compressed_abstract_prompt == prompt
    assert packet.secure_ephemeral_vault == {}

def test_noop_secure_proxy_process_inbound_response():
    proxy = NoOpSecureProxy()
    content = "Hello John Doe"
    result = proxy.process_inbound_response(content, {}, "agent_1", "abstract")
    assert result == content
