from fastapi import Request, Response, HTTPException
try:
    from fastapi_limiter.depends import RateLimiter as FastAPIRateLimiter
except ImportError:
    # Define a minimal stub that simply passes through the response
    class FastAPIRateLimiter:
        def __init__(self, *args, **kwargs):
            pass
        async def __call__(self, request: Request, response: Response):
            return response
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
        
        # Initialize the underlying FastAPIRateLimiter
        # Note: 'days' is not supported by FastAPIRateLimiter
        self._limiter = FastAPIRateLimiter(
            times=times, 
            milliseconds=milliseconds, 
            seconds=seconds, 
            minutes=minutes, 
            hours=hours
        )

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
