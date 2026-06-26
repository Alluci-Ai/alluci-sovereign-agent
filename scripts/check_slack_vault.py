import asyncio
from backend.security.vault import VaultManager
from backend.config import settings

async def main():
    vault = VaultManager(settings.POLYTOPE_MASTER_KEY)
    
    accounts = await vault.list_connections("slack")
    print(f"Slack connection accounts: {accounts}")
    if accounts:
        for acc in accounts:
            creds = await vault.retrieve_connection_secret("slack", acc)
            if creds:
                bot = creds.get("bot_token", "")
                app = creds.get("app_token", "")
                print(f"Account {acc} bot_token exists: {bool(bot)}")
                print(f"Account {acc} app_token exists: {bool(app)}")

if __name__ == "__main__":
    asyncio.run(main())
