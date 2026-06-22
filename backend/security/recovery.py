import hashlib
import base64
from typing import Optional
from mnemonic import Mnemonic
from ..logging_config import get_logger

logger = get_logger("KeyRecovery")

class MasterKeyRecovery:
    """
    Implements a BIP-39 based recovery workflow for the POLYTOPE_MASTER_KEY.
    Allows re-generating the master key from a 24-word seed phrase.
    """
    def __init__(self, language: str = "english"):
        self.mnemo = Mnemonic(language)

    def generate_recovery_phrase(self, master_key: str) -> str:
        """
        Generates a 24-word mnemonic from a provided master key.
        The master key is hashed to create a stable entropy source.
        """
        # We need 256 bits of entropy for a 24-word phrase
        entropy = hashlib.sha256(master_key.encode()).digest()
        phrase = self.mnemo.to_mnemonic(entropy)
        return phrase

    def derive_key_from_phrase(self, phrase: str) -> str:
        """
        Derives a base64 master key from a 24-word mnemonic.
        """
        if not self.mnemo.check(phrase):
            raise ValueError("Invalid recovery phrase checksum.")
        
        entropy = self.mnemo.to_entropy(phrase)
        # Convert 32-byte entropy back to the expected base64 format
        return base64.b64encode(entropy).decode()

    def verify_phrase(self, phrase: str, expected_key: str) -> bool:
        """Checks if a phrase correctly recovers the current key."""
        try:
            recovered = self.derive_key_from_phrase(phrase)
            return recovered == expected_key
        except Exception:
            return False

def initiate_recovery_workflow(phrase: str) -> Optional[str]:
    """
    Helper to attempt master key recovery.
    In a real scenario, this would be used during a manual bootstrap process.
    """
    recovery = MasterKeyRecovery()
    try:
        new_key = recovery.derive_key_from_phrase(phrase)
        logger.info("[ RECOVERY ] Master key successfully derived from recovery phrase.")
        return new_key
    except Exception as e:
        logger.error(f"[ RECOVERY ] Failed to derive key: {e}")
        return None
