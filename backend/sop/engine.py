
import logging
from typing import List, Dict, Any, Optional

class SOPEngine:
    """
    ZeroClaw SOP (Standard Operating Procedure) Engine.
    Executes predefined sequences of tool calls/actions for complex tasks.
    """
    def __init__(self):
        self.sops: Dict[str, Dict[str, Any]] = {}

    def register_sop(self, sop_id: str, title: str, steps: List[Dict[str, Any]]):
        self.sops[sop_id] = {
            "id": sop_id,
            "title": title,
            "steps": steps # List of { "action": "...", "args": {...} }
        }

    def get_sop(self, sop_id: str) -> Optional[Dict[str, Any]]:
        return self.sops.get(sop_id)

    def list_sops(self) -> List[Dict[str, Any]]:
        return list(self.sops.values())

sop_engine = SOPEngine()
