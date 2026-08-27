import asyncio
from backend.services import init_services
async def main():
    print("Testing init_services...")
    await init_services(None)
    print("Done init_services")
if __name__ == "__main__":
    asyncio.run(main())
