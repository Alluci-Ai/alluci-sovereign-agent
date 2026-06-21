import asyncio
import os
from backend.security.vault import VaultManager

async def main():
    vault_root = os.path.expanduser("~/.polytope/vaults")
    vault = VaultManager(os.environ.get("POLYTOPE_MASTER_KEY", "dummy"), vault_root)

    enabled = await vault.retrieve_secret("channel_slack_enabled")
    print(f"slack enabled: {enabled}")

if __name__ == "__main__":
    asyncio.run(main())
