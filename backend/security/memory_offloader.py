import time
import asyncio
import logging
from ..voice.kokoro_bridge import kokoro_bridge

logger = logging.getLogger("MemoryOffloader")

# Track the time of the last active voice transaction (transcription or synthesis)
_last_activity_time = time.time()
_offloader_running = False

def record_activity():
    """Call this on any voice operation to refresh the active window."""
    global _last_activity_time
    _last_activity_time = time.time()

async def start_memory_offloader_loop(idle_timeout_seconds: float = 300.0):
    """
    Spawns a lightweight background task that periodically checks for voice idle time.
    Offloads Kokoro TTS from unified memory (VRAM) after 5 minutes of inactivity.
    """
    global _offloader_running
    if _offloader_running:
        return
    _offloader_running = True
    
    logger.info(f"[MEMORY OFFLOADER] Idle monitor loop started (timeout={idle_timeout_seconds}s).")
    
    try:
        while True:
            await asyncio.sleep(30)
            elapsed = time.time() - _last_activity_time
            
            if elapsed >= idle_timeout_seconds:
                # If Kokoro has weights loaded, offload them
                if kokoro_bridge.tts is not None:
                    logger.info(f"[MEMORY OFFLOADER] Idle threshold reached ({elapsed:.0f}s >= {idle_timeout_seconds}s). Releasing VRAM.")
                    kokoro_bridge.unload_model()
                    
                    # Force Python and MLX GC
                    import gc
                    gc.collect()
                    try:
                        import mlx.core as mx
                        mx.metal.clear_cache()
                    except ImportError:
                        pass
    except asyncio.CancelledError:
        logger.info("[MEMORY OFFLOADER] Loop cancelled.")
    finally:
        _offloader_running = False
