import asyncio
from backend.services import init_services
from backend import services
async def main():
    print("Testing init_services...")
    await init_services(None)
    print("Done init_services")
    print("Testing get_or_create_jwt_keypair...")
    private_key, public_key = await services.vault.get_or_create_jwt_keypair()
    print("Done get_or_create_jwt_keypair")
if __name__ == "__main__":
    asyncio.run(main())
