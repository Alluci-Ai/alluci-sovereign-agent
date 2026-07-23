import asyncio
from backend.inference.mlx_engine import MLXEngine

async def main():
    print("Initializing MLXEngine...")
    engine = MLXEngine()
    await engine.ensure_loaded()
    
    prompt = "Explain the theory of relativity in two short sentences."
    print(f"\nPrompt: {prompt}\n")
    print("Response: ")
    
    response_text = ""
    async for chunk in engine.generate_stream(prompt, max_tokens=150, temperature=0.3):
        print(chunk, end="", flush=True)
        response_text += chunk
        
    print("\n\n--- Semantic Verification ---")
    if len(response_text.strip()) > 0:
        print("PASS: Response is not empty.")
    else:
        print("FAIL: Response is empty.")
        
    if "é" in response_text or "ই" in response_text or "LCLCL" in response_text:
        print("FAIL: Detected signs of previous gibberish patterns.")
    else:
        print("PASS: No known gibberish patterns detected.")
        
    # Check if the output stopped properly (is shorter than max_tokens assuming the answer is brief)
    # A brief answer should be under ~500 characters.
    if len(response_text) > 400:
        print("WARNING: Response might be unusually long or failing to stop.")
    else:
        print("PASS: Response length is reasonable, indicating proper EOS token stopping.")

asyncio.run(main())
