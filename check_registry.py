import asyncio
from backend import services

async def main():
    print(f"Registry keys: {list(services.channel_registry.keys())}")

asyncio.run(main())
