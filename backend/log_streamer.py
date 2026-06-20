"""
JSONL Log Streamer for the Polytope Sovereign OS.

Provides WebSocket-based real-time log streaming with level filtering,
auto-follow mode, and log file export.

Reference: Sovereign Spec Sections 9.1–9.4
"""

import asyncio
import json
import logging
from .logging_config import get_logger
from datetime import datetime, timezone
from typing import Optional, Set, Dict, Any
from collections import deque
import structlog.contextvars
from fastapi import WebSocket, WebSocketDisconnect

logger = get_logger("LogStreamer")


class LogBuffer:
    """
    Ring buffer that captures log records and makes them available
    for WebSocket streaming and historical queries.
    """

    def __init__(self, max_entries: int = 5000):
        self._buffer: deque = deque(maxlen=max_entries)
        self._subscribers: Set[asyncio.Queue] = set()
        self._handler: Optional[logging.Handler] = None

    def install_handler(self):
        """Install a logging handler that captures records into the buffer."""
        if self._handler:
            return
        self._handler = _BufferHandler(self)
        root = logging.getLogger()
        root.addHandler(self._handler)
        logger.info("[LogStreamer] Handler installed on root logger")

    def append(self, record: dict):
        """Add a record and notify all subscribers."""
        self._buffer.append(record)
        for q in list(self._subscribers):
            try:
                # We put a tuple (record, session_key_filter) or just record? 
                # Better to just push the record and let the subscriber filter.
                q.put_nowait(record)
            except asyncio.QueueFull:
                pass  # subscriber is slow, skip

    def subscribe(self) -> asyncio.Queue:
        """Create a new subscriber queue."""
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """Remove a subscriber queue."""
        self._subscribers.discard(q)

    def get_history(self, limit: int = 200, level: Optional[str] = None, session_key: Optional[str] = None) -> list:
        """Return recent log entries, filtered by level and/or session_key."""
        entries = list(self._buffer)
        if level:
            level_upper = level.upper()
            entries = [e for e in entries if e.get("level", "").upper() == level_upper]
        if session_key:
            entries = [e for e in entries if e.get("session_key") == session_key]
        return entries[-limit:]

    def export_jsonl(self, level: Optional[str] = None, session_key: Optional[str] = None) -> str:
        """Export buffered entries as JSONL text."""
        entries = list(self._buffer)
        if level:
            level_upper = level.upper()
            entries = [e for e in entries if e.get("level", "").upper() == level_upper]
        if session_key:
            entries = [e for e in entries if e.get("session_key") == session_key]
        return "\n".join(json.dumps(e) for e in entries)


class _BufferHandler(logging.Handler):
    """Stdlib logging handler that pushes records into a LogBuffer."""

    def __init__(self, buffer: LogBuffer):
        super().__init__()
        self.buffer = buffer

    def emit(self, record: logging.LogRecord):
        try:
            # Try to grab session_key from structlog contextvars
            ctx = structlog.contextvars.get_contextvars()
            session_key = ctx.get("session_key")

            entry = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record) if self.formatter else record.getMessage(),
                "session_key": session_key
            }
            if record.exc_info and record.exc_info[1]:
                entry["exception"] = str(record.exc_info[1])
            self.buffer.append(entry)
        except Exception:
            pass  # never let logging crash the app


# ── WebSocket Streaming Handler ──────────────────────────────────────────────

class LogStreamHandler:
    """
    Manages a WebSocket connection that streams log entries in real time.
    Supports level filtering and auto-follow mode.
    """

    def __init__(self, log_buffer: LogBuffer):
        self.log_buffer = log_buffer

    async def handle(self, websocket: WebSocket, already_accepted: bool = False):
        """Full lifecycle for a single log stream WebSocket connection."""
        if not already_accepted:
            await websocket.accept()

        config = {"level": None, "session_key": None, "auto_follow": True}
        queue = self.log_buffer.subscribe()

        async def receiver():
            """Loop to handle inbound configuration updates from the client."""
            nonlocal config
            try:
                async for raw in websocket.iter_text():
                    try:
                        data = json.loads(raw)
                        if "level" in data:
                            config["level"] = data.get("level")
                        if "session_key" in data:
                            config["session_key"] = data.get("session_key")
                        if "auto_follow" in data:
                            config["auto_follow"] = bool(data["auto_follow"])
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass

        recv_task = asyncio.create_task(receiver())

        try:
            # Send initial history based on starting filters
            history = self.log_buffer.get_history(limit=200, level=config["level"], session_key=config["session_key"])  # type: ignore
            for entry in history:
                await websocket.send_text(json.dumps(entry))

            while True:
                entry = await queue.get()
                
                # Dynamic Filtering
                if config["level"] and entry.get("level", "").upper() != config["level"].upper():  # type: ignore
                    continue
                if config["session_key"] and entry.get("session_key") != config["session_key"]:
                    continue
                
                if not config["auto_follow"]:
                    continue

                await websocket.send_text(json.dumps(entry))

        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug(f"[LogStreamer] Stream ended: {e}")
        finally:
            self.log_buffer.unsubscribe(queue)
            recv_task.cancel()


# ── Module-level singleton ───────────────────────────────────────────────────

log_buffer = LogBuffer()
log_stream_handler = LogStreamHandler(log_buffer)
