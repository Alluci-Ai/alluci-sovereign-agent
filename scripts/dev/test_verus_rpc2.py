import asyncio
from backend.security.verus_rpc import verus_rpc

async def main():
    print("Testing Verus RPC...")
    print(f"URL: {verus_rpc.public_url}")
    print(f"Lite Mode: {verus_rpc.client}")
    try:
        res = await asyncio.wait_for(verus_rpc.get_info(), timeout=5.0)
        print("Success:", res)
    except Exception as e:
        print("Failed:", repr(e))

asyncio.run(main())
