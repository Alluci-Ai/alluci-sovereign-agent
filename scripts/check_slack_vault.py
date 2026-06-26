import asyncio
from backend.security.vault import VaultManager
from backend.config import settings

async def main():
    vault = VaultManager(settings.POLYTOPE_MASTER_KEY)
    state = await vault.retrieve_secret("channel_slack_enabled")
    print(f"Vault 'channel_slack_enabled': {state}")
    
    # Try enabling it!
    if state and not state.get("enabled", True):
        print("Enabling it now!")
        await vault.store_secret("channel_slack_enabled", {"enabled": True})
        print("Enabled!")
        
if __name__ == "__main__":
    asyncio.run(main())
