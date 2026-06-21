import asyncio
import os
from backend.security.vault import VaultManager

async def main():
    vault_root = os.path.expanduser("~/.polytope/vaults")
    # Fetch from OS Keychain automatically
    vault = VaultManager(os.environ.get("POLYTOPE_MASTER_KEY", "dummy"), vault_root)

    creds = await vault.retrieve_connection_secret("slack", "default")
    app_token = creds.get('app_token', '')
    bot_token = creds.get('bot_token', '')
    print(f"app_token: '{app_token}' (len: {len(app_token)})")
    print(f"bot_token: '{bot_token}' (len: {len(bot_token)})")

if __name__ == "__main__":
    asyncio.run(main())
