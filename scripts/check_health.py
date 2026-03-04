
import asyncio
from backend.config import load_settings
from backend.security.vault import VaultManager
from backend.inference.router import ModelRouter

async def main():
    print("[ SENTINEL ] Starting Polytope Health Check...")
    settings = load_settings()
    vault = VaultManager(settings.POLYTOPE_MASTER_KEY)
    router = ModelRouter(settings)
    
    results = await router.check_health()
    
    unstable_found = False
    for provider, status in results.items():
        if isinstance(status, dict):
            stat_val = status.get("status", "UNKNOWN")
            error = status.get("error", "")
            print(f"  - {provider:15}: [{stat_val}] {error}")
            vault.update_vault_status(provider, stat_val)
            if stat_val == "UNSTABLE":
                unstable_found = True
        else:
            print(f"  - {provider:15}: [{status}]")
            vault.update_vault_status(provider, status)
            if status == "UNSTABLE":
                unstable_found = True
            
    if unstable_found:
        print("\n[ WARNING ] Some vaults are [ UNSTABLE ]. Please re-harvest your API keys.")
    else:
        print("\n[ SUCCESS ] All primary model manifolds are [ HEALTHY ].")

if __name__ == "__main__":
    asyncio.run(main())
