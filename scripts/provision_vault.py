#!/usr/bin/env python3
"""
First-boot provisioning: moves critical keys from .env into the OS keychain
so they never need to sit in a plaintext file again.

Run once after initial setup:
    python3 scripts/provision_vault.py
"""
import os
import sys
import secrets
import getpass

try:
    import keyring
except ImportError:
    sys.exit("ERROR: Install keyring first:  pip install keyring")

# Simple .env loader to avoid requiring python-dotenv in the script environment
def load_env_manual(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                if k not in os.environ:
                    os.environ[k] = v

load_env_manual()

SERVICE = "alluci-sovereign"

KEYS_TO_PROVISION = [
    ("POLYTOPE_MASTER_KEY",  "Vault master key",         lambda: secrets.token_hex(32)),
    ("JWT_SECRET_KEY",       "JWT signing key",          lambda: secrets.token_urlsafe(64)),
    ("CSRF_SECRET_KEY",      "CSRF signing key",         lambda: secrets.token_urlsafe(64)),
]

def provision():
    print("Alluci Sovereign Agent — Keychain Provisioner")
    print("=" * 50)
    print(f"Service name: {SERVICE!r}\n")

    for env_key, label, generate in KEYS_TO_PROVISION:
        existing = keyring.get_password(SERVICE, env_key)
        env_val  = os.getenv(env_key, "")

        if existing:
            print(f"  {label}: already in keychain — skipping")
            continue

        if env_val and "PLACEHOLDER" not in env_val:
            print(f"  {label}: migrating from environment variable")
            keyring.set_password(SERVICE, env_key, env_val)
            print(f"    stored in keychain: {env_key[:8]}...{env_key[-4:]}")
        else:
            val = generate()
            keyring.set_password(SERVICE, env_key, val)
            print(f"  {label}: generated and stored ({val[:8]}...)")

    print("\nProvisioning complete.")
    print("You can now remove POLYTOPE_MASTER_KEY, JWT_SECRET_KEY, and")
    print("CSRF_SECRET_KEY from your .env file — they will be loaded from")
    print("the OS keychain automatically on every boot.")

if __name__ == "__main__":
    provision()
