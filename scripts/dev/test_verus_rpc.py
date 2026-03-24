import asyncio
from backend.security.verus_rpc import verus_rpc

async def main():
    print("Testing Verus RPC get_info...")
    try:
        res = await asyncio.wait_for(verus_rpc.get_info(), timeout=15.0)
        print("Success:", res)
    except Exception as e:
        print("Failed:", repr(e))

asyncio.run(main())
