
import os
import logging
from ..logging_config import get_logger
from typing import Dict, Any
from mss import mss
from .base import Adapter

class ScreenCaptureAdapter(Adapter):
    """
    Screen Capture Adapter.
    Captures the current screen and saves it as an image file.
    """
    name = "screen_capture"
    description = "Capture a screenshot of the current display."

    def __init__(self, output_dir: str = "/tmp/alluci/screenshots"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger = get_logger("ScreenCaptureAdapter")

    async def execute(self, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Takes a screenshot of the specified monitor.

        args:
            monitor (int): 1-based monitor index. Default: 1 (primary display).
            output_path (str): Optional custom output path. Auto-generated if not set.
        """
        _args = args or {}
        monitor_idx = int(_args.get("monitor", 1))
        custom_path = _args.get("output_path")

        try:
            with mss() as sct:
                monitors = sct.monitors
                # monitors[0] is the combined virtual display — use monitors[1] as the primary
                if monitor_idx >= len(monitors):
                    monitor_idx = 1  # silently fall back to primary

                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                out_path = custom_path or os.path.join(
                    self.output_dir, f"screenshot_{timestamp}.png"
                )

                sct.shot(mon=monitor_idx, output=out_path)

                return {
                    "status": "success",
                    "path": out_path,
                    "monitor": monitor_idx,
                    "message": f"Screenshot saved to {out_path}",
                }
        except Exception as e:
            self.logger.error(f"Screen capture failed: {e}")
            return {"status": "error", "message": str(e)}
