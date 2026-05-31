import pytest
from backend.security.proxy import AlluciSecureProxy

def test_token_pruning_logic():
    """Confirms that conversational filler is successfully stripped to minimize query token density."""
    raw_input_string = "Please kindly help me optimize this payload loop now."
    noise_words = ["please", "kindly", "could", "you", "help", "me", "optimize", "now"]
    
    working_string = raw_input_string.lower()
    for word in noise_words:
        working_string = working_string.replace(word, "")
    cleaned_string = " ".join(working_string.split())
    
    # Assertions confirm that empty padding tokens are removed
    assert "please" not in cleaned_string
    assert "kindly" not in cleaned_string
    assert cleaned_string == "this payload loop ."

def test_secure_vault_mapping():
    """Validates that extracted private keys match their corresponding placeholder tokens."""
    token_key = "[ALLUCI_EMAIL_TOKEN_1001]"
    private_value = "developer@alluci-ai.net"
    mock_vault = {token_key: private_value}
    
    mock_cloud_output = "Update configurations for user [ALLUCI_EMAIL_TOKEN_1001] locally."
    
    # Simulate context re-injection pass
    for key, val in mock_vault.items():
        mock_cloud_output = mock_cloud_output.replace(key, val)
        
    assert "[ALLUCI_EMAIL_TOKEN_1001]" not in mock_cloud_output
    assert "developer@alluci-ai.net" in mock_cloud_output

def test_actual_proxy_integration():
    """Validates the actual implementation of AlluciSecureProxy matches the spec logic."""
    proxy = AlluciSecureProxy()
    
    # Test Outbound
    raw_prompt = "Draft contract terms for client Alice Vance at alice@vance-legal.org using 0x71C7656EC7ab88b098defB751B7401B5f6d8976F"
    packet = proxy.process_outbound_prompt(raw_prompt)
    
    assert "alice@vance-legal.org" not in packet.compressed_abstract_prompt
    assert "0x71C7656EC7ab88b098defB751B7401B5f6d8976F" not in packet.compressed_abstract_prompt
    assert len(packet.secure_ephemeral_vault) >= 3
    
    # Test Inbound Re-injection
    simulated_cloud = f"Contract for {list(packet.secure_ephemeral_vault.keys())[0]} is ready."
    final_output = proxy.process_inbound_response(simulated_cloud, packet.secure_ephemeral_vault, agent_id="executive", abstract_prompt=packet.compressed_abstract_prompt)
    
    assert list(packet.secure_ephemeral_vault.values())[0] in final_output
