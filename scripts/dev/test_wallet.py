import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get('http://localhost:8000/api/wallet/dashboard')
            print(f"Status: {r.status_code}")
            print(f"Response: {r.text}")
        except Exception as e:
            print(f"Failed: {e}")

asyncio.run(test())
