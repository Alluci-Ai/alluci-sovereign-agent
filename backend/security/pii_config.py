'''backend/security/pii_config.py'''
"""Configuration for PII scrubbing used by :class:`AlluciSecureProxy`.

All regex patterns and the default whitelist are defined as module‑level
constants so that they are version‑controlled and easily importable.
A small helper loads an optional runtime whitelist from the environment
variable ``ALLUCI_PII_WHITELIST`` and merges it with the static list.
"""

import os
import re
from typing import List, Tuple, Set, Pattern

# ---------------------------------------------------------------------------
# Core scrubbing patterns – each entry is ``(placeholder_token, compiled_regex)``
# ---------------------------------------------------------------------------
PII_SCRUBBER: List[Tuple[str, Pattern]] = [
    (
        "[ALLUCI_NAME_TOKEN]",
        re.compile(r"\b([A-Z][a-z]+)\s+([A-Z][a-z]+)\b"),
    ),
    (
        "[ALLUCI_EMAIL_TOKEN]",
        re.compile(r"[\w\.-]+@[\w\.-]+\.\w+"),
    ),
    (
        "[ALLUCI_CRYPTO_TOKEN]",
        re.compile(r"\b(0x)[a-fA-F0-9]{40}\b"),
    ),
    (
        "[ALLUCI_FINANCE_TOKEN]",
        re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
    ),
]

# ---------------------------------------------------------------------------
# Default whitelist – tokens that are considered safe to appear in the
# outbound prompt and therefore should **not** be scrubbed.
# ---------------------------------------------------------------------------
DEFAULT_WHITELIST: Set[str] = {
    "a1b2c3d4",
    "deadbeef",
    "cafebabe",
    "PUBLIC_API_KEY",
}


def _load_runtime_whitelist() -> Set[str]:
    """Load optional whitelist entries from the environment.

    The environment variable ``ALLUCI_PII_WHITELIST`` may contain a comma‑
    separated list of additional tokens.  If the variable is absent or
    empty, the function simply returns a copy of ``DEFAULT_WHITELIST``.
    This logic runs once at import time, so there is no per‑request I/O.
    """
    raw = os.getenv("ALLUCI_PII_WHITELIST", "")
    if not raw:
        return set(DEFAULT_WHITELIST)
    extra = {token.strip() for token in raw.split(",") if token.strip()}
    # Union with the static list – duplicates are discarded automatically.
    return set(DEFAULT_WHITELIST).union(extra)

# Public constant used by the proxy implementation.
WHITELIST_TOKENS: Set[str] = _load_runtime_whitelist()

# End of file
