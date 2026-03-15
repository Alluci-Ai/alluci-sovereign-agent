
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

    async def execute(self) -> Dict[str, Any]:
        """
        Takes a screenshot.
        """
        try:
            with mss() as sct:
                filename = sct.shot(output=os.path.join(self.output_dir, "screenshot.png"))
                return {
                    "status": "success",
                    "path": filename,
                    "message": f"Screenshot saved to {filename}"
                }
        except Exception as e:
            self.logger.error(f"Screen capture failed: {e}")
            return {"status": "error", "message": str(e)}
