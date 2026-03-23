"""
In-Memory Sliding Window Rate Limiter
Fallback for when Redis is not configured. Uses a per-ip deques of request
timestamps. Thread-safe via asyncio.Lock.
"""
import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict
from fastapi import HTTPException, Request, status


class SlidingWindowLimiter:
    """
    Per-IP, per-endpoint sliding window rate limiter.
    """

    def __init__(self):
        self._windows: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    def _make_key(self, request: Request) -> str:
        client_ip = (
            request.headers.get("x-forwarded-for", "").split(",")[0].strip()
            or (request.client.host if request.client else "unknown")
        )
        return f"{client_ip}:{request.url.path}"

    async def check(self, request: Request, times: int, seconds: int) -> None:
        """
        Raises HTTP 429 if the caller has exceeded `times` requests
        in the last `seconds` seconds for this endpoint.
        """
        key = self._make_key(request)
        now = time.monotonic()
        window_start = now - seconds

        async with self._lock:
            dq = self._windows[key]

            # Evict timestamps outside the window
            while dq and dq[0] < window_start:
                dq.popleft()

            if len(dq) >= times:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please slow down.",
                    headers={"Retry-After": str(seconds)},
                )

            dq.append(now)

    async def reset(self, request: Request) -> None:
        """Clear rate limit state for a specific client+endpoint."""
        key = self._make_key(request)
        async with self._lock:
            self._windows.pop(key, None)


# Singleton
_fallback_limiter = SlidingWindowLimiter()


def get_fallback_limiter() -> SlidingWindowLimiter:
    return _fallback_limiter
