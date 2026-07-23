import asyncio
from backend.inference.mlx_engine import engine

async def main():
    print("Testing MLX Engine initialization and generation...")
    # Generate response
    prompt = "Hello! Please tell me a short joke."
    print(f"\nUser: {prompt}\nModel: ", end="", flush=True)
    
    async for chunk in engine.generate_stream(prompt, max_tokens=100, temperature=0.7):
        print(chunk, end="", flush=True)
    print("\n\nTest completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
