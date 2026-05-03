
import asyncio
from fastapi import Request
from backend.routers.auth import get_webauthn_challenge
from backend.config import settings

async def test_webauthn_resolution():
    # 1. Test with default None (Dynamic)
    settings.WEBAUTHN_RP_ID = None
    # Mock Request
    scope = {
        "type": "http",
        "method": "GET",
        "scheme": "https",
        "server": ("alluci.ai", 443),
        "headers": [(b"host", b"alluci.ai")],
    }
    request = Request(scope)
    
    challenge_data = await get_webauthn_challenge(request)
    print(f"Dynamic RP ID: {challenge_data['rp']['id']}")
    assert challenge_data['rp']['id'] == "alluci.ai"

    # 2. Test with explicit override
    settings.WEBAUTHN_RP_ID = "sovereign.local"
    challenge_data = await get_webauthn_challenge(request)
    print(f"Override RP ID: {challenge_data['rp']['id']}")
    assert challenge_data['rp']['id'] == "sovereign.local"

if __name__ == "__main__":
    asyncio.run(test_webauthn_resolution())
