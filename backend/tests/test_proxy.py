import pytest
pytestmark = pytest.mark.unit

import os
import json
from unittest.mock import patch, mock_open
from backend.security.proxy import AlluciSecureProxy, OptimizedSovereignPacket

@pytest.fixture
def proxy():
    return AlluciSecureProxy()

def test_process_outbound_prompt_email(proxy):
    raw = "My email is test@example.com."
    packet = proxy.process_outbound_prompt(raw)
    assert "test@example.com" not in packet.compressed_abstract_prompt
    assert "[ALLUCI_EMAIL_TOKEN]_1001" in packet.compressed_abstract_prompt
    assert packet.secure_ephemeral_vault["[ALLUCI_EMAIL_TOKEN]_1001"] == "test@example.com"

def test_process_outbound_prompt_crypto(proxy):
    raw = "Send it to 0x1234567890123456789012345678901234567890"
    packet = proxy.process_outbound_prompt(raw)
    assert "0x1234" not in packet.compressed_abstract_prompt
    assert "[ALLUCI_CRYPTO_TOKEN]_1001" in packet.compressed_abstract_prompt
    assert packet.secure_ephemeral_vault["[ALLUCI_CRYPTO_TOKEN]_1001"] == "0x1234567890123456789012345678901234567890"

def test_process_outbound_prompt_finance(proxy):
    raw = "My card is 1234-5678-9012-3456"
    packet = proxy.process_outbound_prompt(raw)
    assert "1234" not in packet.compressed_abstract_prompt
    assert "[ALLUCI_FINANCE_TOKEN]_1001" in packet.compressed_abstract_prompt
    assert packet.secure_ephemeral_vault["[ALLUCI_FINANCE_TOKEN]_1001"] == "1234-5678-9012-3456"

def test_process_outbound_prompt_name(proxy):
    raw = "Hello, my name is John Doe."
    packet = proxy.process_outbound_prompt(raw)
    assert "John Doe" not in packet.compressed_abstract_prompt
    assert "[ALLUCI_NAME_TOKEN]_1001" in packet.compressed_abstract_prompt
    assert packet.secure_ephemeral_vault["[ALLUCI_NAME_TOKEN]_1001"] == "John Doe"

def test_process_outbound_prompt_multiple(proxy):
    raw = "My email is test@example.com and test@example.com."
    packet = proxy.process_outbound_prompt(raw)
    assert packet.compressed_abstract_prompt.count("[ALLUCI_EMAIL_TOKEN]_1001") == 2
    assert len(packet.secure_ephemeral_vault) == 1

def test_compress_token_density(proxy):
    raw = "Please kindly help me optimize this now"
    compressed = proxy._compress_token_density(raw)
    assert compressed == "this"

def test_process_inbound_response(proxy):
    raw_response = "We sent it to [ALLUCI_EMAIL_TOKEN]_1001."
    vault = {"[ALLUCI_EMAIL_TOKEN]_1001": "test@example.com"}
    
    with patch("backend.security.proxy.AlluciSecureProxy._log_to_dream_pool") as mock_log:
        res = proxy.process_inbound_response(raw_response, vault, "agent1", "abstract")
        assert res == "We sent it to test@example.com."
        mock_log.assert_called_once_with("agent1", "abstract", raw_response)

def test_log_to_dream_pool(proxy):
    with patch("os.makedirs"):
        with patch("builtins.open", mock_open()) as mocked_file:
            proxy._log_to_dream_pool("agent_1", "abstract prompt", "cloud response")
            mocked_file.assert_called_once()
            handle = mocked_file()
            handle.write.assert_called_once()
            written = handle.write.call_args[0][0]
            data = json.loads(written)
            assert data["prompt"] == "abstract prompt"
            assert data["response"] == "cloud response"

def test_log_to_dream_pool_exception(proxy):
    with patch("os.makedirs"):
        with patch("builtins.open", side_effect=Exception("Disk error")):
            # Should not raise exception
            proxy._log_to_dream_pool("agent_1", "abstract prompt", "cloud response")
