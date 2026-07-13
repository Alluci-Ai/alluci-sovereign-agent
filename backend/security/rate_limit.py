from fastapi import Request, Response, HTTPException
from pyrate_limiter import Limiter, Rate
from fastapi_limiter.depends import RateLimiter as FastAPIRateLimiter
from .rate_limiter import get_fallback_limiter
import logging

logger = logging.getLogger("RateLimitAdapter")

class RateLimiter:
    """
    Adapter for FastAPI Limiter that provides graceful fallback to 
    an in-memory sliding window limiter if Redis is unavailable.
    
    This avoids monkey-patching the third-party library globally.
    """
    def __init__(self, times: int = 60, milliseconds: int = 0, seconds: int = 0, minutes: int = 0, hours: int = 0):
        self.times = times
        self.milliseconds = milliseconds
        self.seconds = seconds
        self.minutes = minutes
        self.hours = hours
        
        # Calculate total milliseconds for pyrate_limiter
        duration_ms = int(milliseconds + seconds * 1000 + minutes * 60 * 1000 + hours * 3600 * 1000)
        if duration_ms == 0:
            duration_ms = 60000
            
        rate = Rate(times, duration_ms)
        self._limiter = FastAPIRateLimiter(limiter=Limiter(rate))

    async def __call__(self, request: Request, response: Response):
        try:
            return await self._limiter(request, response)
        except HTTPException as e:
            if e.status_code == 429:
                logger.warning(f"Provider rate limit hit (429): {e.detail}")
                # Continue to fallback logic below
            else:
                raise
        except Exception as e:
            logger.warning(f"Redis rate limiter unavailable, falling back: {e}")
        
        # Fallback to in-memory limiter
        total_seconds = int(
            self.milliseconds / 1000 + 
            self.seconds + 
            self.minutes * 60 + 
            self.hours * 3600
        )
        if total_seconds == 0:
            total_seconds = 60 # Default
            
        await get_fallback_limiter().check(request, times=self.times, seconds=total_seconds)
