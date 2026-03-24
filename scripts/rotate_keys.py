import asyncio
import sys
import os

# Add project root to sys.path to allow importing from backend
sys.path.append(os.getcwd())

from backend.config import settings
from backend.security.vault import VaultManager

async def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/rotate_keys.py <new_master_key>")
        sys.exit(1)
    
    new_key = sys.argv[1]
    
    # Optional: check if new key is secure enough (handled by vault later but good to check here)
    if len(new_key) < 16:
        print("Error: New master key must be at least 16 characters long.")
        sys.exit(1)

    print(f"[*] Initializing Vault with current master key...")
    try:
        vm = VaultManager(settings.POLYTOPE_MASTER_KEY)
    except Exception as e:
        print(f"[!] Failed to initialize Vault: {e}")
        sys.exit(1)

    print(f"[*] Starting deep key rotation...")
    success = await vm.rotate_keys(new_key)
    
    if success:
        print("[+] Key rotation successful.")
        print("[!] IMPORTANT: Update your .env or OS Keychain with the new POLYTOPE_MASTER_KEY.")
        print(f"    New Key: {new_key}")
    else:
        print("[!] Key rotation FAILED. Check logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
