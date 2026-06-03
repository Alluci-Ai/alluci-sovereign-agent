from typing import Optional, Dict, Any

class SecurityException(Exception):
    """
    Unified Security Exception.
    Raised by the Core Firewall, Circuit Breakers, or Sovereign Security Manager.
    Includes metadata to trigger Interactive User Resolutions on the frontend.
    """
    def __init__(self, message: str, exception_type: str, metadata: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.exception_type = exception_type
        self.metadata = metadata or {}
