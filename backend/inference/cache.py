import hashlib
import time
import asyncio
from typing import Optional, Dict, Tuple
from ..logging_config import get_logger

logger = get_logger("PromptCache")

class AsyncPromptCache:
    """
    A Zero-Dependency TTL In-Memory Cache for LLM Prompts.
    Maintains Data Sovereignty by keeping cache strictly in local RAM.
    TTL is 5 minutes by default to handle rapid bursts of duplicate queries.
    """
    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        # dict maps hash_key -> (timestamp, response_string)
        self._cache: Dict[str, Tuple[float, str]] = {}
        self._lock = asyncio.Lock()

    def _generate_key(self, prompt: str, system_instruction: str, inference_mode: str) -> str:
        """Creates a deterministic hash of the request."""
        raw = f"{prompt}|{system_instruction}|{inference_mode}".encode('utf-8')
        return hashlib.sha256(raw).hexdigest()

    async def get(self, prompt: str, system_instruction: str, inference_mode: str) -> Optional[str]:
        """Retrieves a prompt response if it exists and is not expired."""
        key = self._generate_key(prompt, system_instruction, inference_mode)
        
        async with self._lock:
            if key in self._cache:
                timestamp, response = self._cache[key]
                if time.time() - timestamp <= self.ttl_seconds:
                    logger.debug(f"[ CACHE HIT ] Reusing response for hash {key[:8]}...")
                    return response
                else:
                    # Expired
                    del self._cache[key]
                    
        return None

    async def set(self, prompt: str, system_instruction: str, inference_mode: str, response: str):
        """Stores a prompt response with the current timestamp."""
        key = self._generate_key(prompt, system_instruction, inference_mode)
        
        async with self._lock:
            self._cache[key] = (time.time(), response)
            logger.debug(f"[ CACHE SET ] Stored response for hash {key[:8]} (TTL: {self.ttl_seconds}s)")

    async def clear(self):
        """Manually clear the cache (useful for memory purges)."""
        async with self._lock:
            self._cache.clear()
            logger.info("[ CACHE CLEARED ] All LLM cached responses purged.")

# Global singleton
prompt_cache = AsyncPromptCache()
