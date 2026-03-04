"""
JSONL Log Streamer for the Polytope Sovereign OS.

Provides WebSocket-based real-time log streaming with level filtering,
auto-follow mode, and log file export.

Reference: OpenClaw Sections 9.1–9.4
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Set
from collections import deque
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("LogStreamer")


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

    def get_history(self, limit: int = 200, level: Optional[str] = None) -> list:
        """Return recent log entries, optionally filtered by level."""
        entries = list(self._buffer)
        if level:
            level_upper = level.upper()
            entries = [e for e in entries if e.get("level", "").upper() == level_upper]
        return entries[-limit:]

    def export_jsonl(self, level: Optional[str] = None) -> str:
        """Export all buffered entries as JSONL text."""
        entries = list(self._buffer)
        if level:
            level_upper = level.upper()
            entries = [e for e in entries if e.get("level", "").upper() == level_upper]
        return "\n".join(json.dumps(e) for e in entries)


class _BufferHandler(logging.Handler):
    """Stdlib logging handler that pushes records into a LogBuffer."""

    def __init__(self, buffer: LogBuffer):
        super().__init__()
        self.buffer = buffer

    def emit(self, record: logging.LogRecord):
        try:
            entry = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record) if self.formatter else record.getMessage(),
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

    async def handle(self, websocket: WebSocket):
        """Full lifecycle for a single log stream WebSocket connection."""
        await websocket.accept()

        # Read initial config message
        level_filter: Optional[str] = None
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=2.0)
            config = json.loads(raw)
            level_filter = config.get("level")
        except (asyncio.TimeoutError, json.JSONDecodeError):
            pass  # no config, stream everything

        # Send recent history first
        history = self.log_buffer.get_history(limit=100, level=level_filter)
        for entry in history:
            await websocket.send_text(json.dumps(entry))

        # Subscribe to live entries
        queue = self.log_buffer.subscribe()
        try:
            while True:
                entry = await queue.get()
                if level_filter and entry.get("level", "").upper() != level_filter.upper():
                    continue
                await websocket.send_text(json.dumps(entry))
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug(f"[LogStreamer] Stream ended: {e}")
        finally:
            self.log_buffer.unsubscribe(queue)


# ── Module-level singleton ───────────────────────────────────────────────────

log_buffer = LogBuffer()
log_stream_handler = LogStreamHandler(log_buffer)
