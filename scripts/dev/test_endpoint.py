import asyncio
import httpx
from backend.config import load_settings
settings = load_settings()

async def main():
    print("Testing /api/wallet/dashboard endpoint...")
    # First, get a token
    try:
        async with httpx.AsyncClient() as client:
            print("Server is at http://localhost:8000")
            # We don't have a token, but we can see if it responds with 401 immediately or hangs!
            res = await client.get('http://localhost:8000/api/wallet/dashboard', timeout=5.0)
            print(f"Status: {res.status_code}")
            print(f"Response: {res.text}")
    except Exception as e:
        print("Failed:", repr(e))

asyncio.run(main())
