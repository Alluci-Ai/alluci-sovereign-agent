
import asyncio
import os
import json
from backend.security.vault import VaultManager
from backend.config import settings

async def check_manifest():
    vault = VaultManager(settings.POLYTOPE_MASTER_KEY)
    manifest = await vault.retrieve_secret("soul_manifest")
    print(json.dumps(manifest, indent=2))

if __name__ == "__main__":
    asyncio.run(check_manifest())
