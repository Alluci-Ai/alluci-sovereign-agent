import sys
import asyncio
import os
from fastapi import FastAPI
from backend.app import lifespan

app = FastAPI()

async def main():
    print("STARTING TEST", flush=True)
    try:
        async with lifespan(app):
            print("LIFESPAN SUCCESS", flush=True)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
