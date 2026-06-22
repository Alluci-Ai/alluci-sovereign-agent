import asyncio
from backend.config import settings
from backend.security.vault import VaultManager

async def run():
    vault = VaultManager(settings.POLYTOPE_MASTER_KEY)
    enabled = await vault.retrieve_secret("channel_slack_enabled")
    print(f"Enabled: {enabled}")
    accounts = await vault.list_connections("slack")
    print(f"Accounts: {accounts}")
    if accounts:
        for acc in accounts:
            creds = await vault.retrieve_connection_secret("slack", acc)
            # hide actual tokens
            if creds:
                safe_creds = {k: "HIDDEN" for k in creds.keys()}
                print(f"Creds for {acc}: {safe_creds}")

asyncio.run(run())
