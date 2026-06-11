import pytest
pytestmark = pytest.mark.unit

import base64
import hashlib
import sys
from unittest.mock import MagicMock, patch

mock_mnemo = MagicMock()
mock_mnemo.to_mnemonic.return_value = " ".join(["apple"] * 24)
mock_mnemo.check.return_value = True
mock_mnemo.to_entropy.return_value = hashlib.sha256(b"my_secret_master_key").digest()

mock_mnemonic_module = MagicMock()
mock_mnemonic_module.Mnemonic.return_value = mock_mnemo
sys.modules['mnemonic'] = mock_mnemonic_module

from backend.security.recovery import MasterKeyRecovery, initiate_recovery_workflow

@pytest.fixture
def recovery():
    rec = MasterKeyRecovery()
    # Reset some mocks per test just in case
    rec.mnemo.to_entropy.return_value = hashlib.sha256(b"my_secret_master_key").digest()
    rec.mnemo.check.return_value = True
    rec.mnemo.check.side_effect = None
    return rec

def test_generate_recovery_phrase(recovery):
    master_key = "my_secret_master_key"
    phrase = recovery.generate_recovery_phrase(master_key)
    assert len(phrase.split()) == 24

def test_derive_key_from_phrase(recovery):
    master_key = "my_secret_master_key"
    phrase = recovery.generate_recovery_phrase(master_key)
    
    derived = recovery.derive_key_from_phrase(phrase)
    
    expected_entropy = hashlib.sha256(master_key.encode()).digest()
    expected_key = base64.b64encode(expected_entropy).decode()
    
    assert derived == expected_key

def test_derive_key_invalid_phrase(recovery):
    recovery.mnemo.check.return_value = False
    with pytest.raises(ValueError, match="Invalid recovery phrase checksum."):
        recovery.derive_key_from_phrase("apple apple apple")

def test_verify_phrase_true(recovery):
    master_key = "test_key"
    recovery.mnemo.to_entropy.return_value = hashlib.sha256(master_key.encode()).digest()
    phrase = recovery.generate_recovery_phrase(master_key)
    expected_key = base64.b64encode(hashlib.sha256(master_key.encode()).digest()).decode()
    
    assert recovery.verify_phrase(phrase, expected_key) is True

def test_verify_phrase_false(recovery):
    master_key = "test_key"
    recovery.mnemo.to_entropy.return_value = hashlib.sha256(master_key.encode()).digest()
    phrase = recovery.generate_recovery_phrase(master_key)
    assert recovery.verify_phrase(phrase, "wrong_key") is False

def test_verify_phrase_exception(recovery):
    recovery.mnemo.check.side_effect = Exception("error")
    assert recovery.verify_phrase("bad phrase", "expected") is False

def test_initiate_recovery_workflow_success(recovery):
    master_key = "test_key"
    recovery.mnemo.to_entropy.return_value = hashlib.sha256(master_key.encode()).digest()
    phrase = recovery.generate_recovery_phrase(master_key)
    expected_key = base64.b64encode(hashlib.sha256(master_key.encode()).digest()).decode()
    
    with patch("backend.security.recovery.MasterKeyRecovery") as MockClass:
        MockClass.return_value = recovery
        new_key = initiate_recovery_workflow(phrase)
    assert new_key == expected_key

def test_initiate_recovery_workflow_failure(recovery):
    recovery.mnemo.check.return_value = False
    with patch("backend.security.recovery.MasterKeyRecovery", return_value=recovery):
        new_key = initiate_recovery_workflow("bad phrase")
    assert new_key is None
