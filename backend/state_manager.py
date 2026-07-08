import os
import json
import fcntl
from typing import Dict, Any
from .logging_config import get_logger

logger = get_logger("StateManager")

TOGGLES_FILE = os.path.expanduser("~/.polytope/toggles.json")

class StateManager:
    @staticmethod
    def _read_toggles() -> Dict[str, Any]:
        if not os.path.exists(TOGGLES_FILE):
            return {"tools": {}, "skills": {}}
        try:
            with open(TOGGLES_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read toggles: {e}")
            return {"tools": {}, "skills": {}}

    @staticmethod
    def _write_toggles(data: Dict[str, Any]):
        os.makedirs(os.path.dirname(TOGGLES_FILE), exist_ok=True)
        try:
            with open(TOGGLES_FILE, "w") as f:
                # Use fcntl for simple file locking if needed, but dump is usually fast enough
                fcntl.flock(f, fcntl.LOCK_EX)
                json.dump(data, f, indent=2)
                fcntl.flock(f, fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Failed to write toggles: {e}")

    @classmethod
    def get_tool_toggles(cls) -> Dict[str, bool]:
        return cls._read_toggles().get("tools", {})

    @classmethod
    def get_skill_toggles(cls) -> Dict[str, bool]:
        return cls._read_toggles().get("skills", {})

    @classmethod
    def set_tool_toggle(cls, tool_id: str, enabled: bool):
        data = cls._read_toggles()
        if "tools" not in data:
            data["tools"] = {}
        data["tools"][tool_id] = enabled
        cls._write_toggles(data)

    @classmethod
    def set_skill_toggle(cls, skill_id: str, enabled: bool):
        data = cls._read_toggles()
        if "skills" not in data:
            data["skills"] = {}
        data["skills"][skill_id] = enabled
        cls._write_toggles(data)
