
import asyncio
import google.generativeai as genai
from backend.config import load_settings

async def test_gemini():
    print("[ DIAGNOSTIC ] Testing Gemini...")
    settings = load_settings()
    if not settings.GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY missing from settings")
        return

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content("Say 'Gemini is functional'")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Gemini Exception: {e}")
        if hasattr(e, 'args'):
            print(f"Args: {e.args}")

if __name__ == "__main__":
    asyncio.run(test_gemini())
