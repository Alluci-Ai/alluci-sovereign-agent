import asyncio
import httpx

async def main():
    try:
        async with httpx.AsyncClient() as client:
            # The /docs endpoint is usually public and serves the OpenAPI schema
            res = await client.get('http://localhost:8000/docs', timeout=3.0)
            print(f"Docs Status: {res.status_code}")
    except Exception as e:
        print("Docs Failed:", repr(e))

asyncio.run(main())
