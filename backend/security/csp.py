"""
CSP Nonce Generator
Generates a cryptographically random per-request nonce for CSP script/style allowlisting.
The nonce is stored in request.state so middleware and templates can read it.
"""
import base64
import os
from fastapi import Request


def generate_nonce() -> str:
    """Returns a 128-bit (16-byte) URL-safe base64-encoded nonce string."""
    return base64.b64encode(os.urandom(16)).decode("ascii")


def get_nonce(request: Request) -> str:
    """Dependency: retrieves the per-request nonce set by the CSP middleware."""
    return getattr(request.state, "csp_nonce", "")
