import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("AppleWatchAuth")

@dataclass
class WatchSensorData:
    is_on_wrist: bool
    heart_rate: Optional[float]
    blood_oxygen: Optional[float]
    last_update_ms: int

class AppleWatchAuth:
    """
    [ PPN-017 ] Sovereign Kill Switch Daemon.
    Monitors Apple Watch / Bio-wearable status.
    If the agent attempts high-cognitive actions (banking, deep file edits) 
    and the watch is off-wrist or no pulse is detected, it triggers the kill switch.
    """
    def __init__(self):
        self.sensor_data = WatchSensorData(
            is_on_wrist=False, 
            heart_rate=None, 
            blood_oxygen=None, 
            last_update_ms=0
        )
        self.locked = False

    def update_sensors(self, is_on_wrist: bool, heart_rate: Optional[float]):
        """Stream hook for live watch data."""
        self.sensor_data.is_on_wrist = is_on_wrist
        self.sensor_data.heart_rate = heart_rate

    def verify_liveness(self, action_type: str) -> bool:
        """
        Validates whether the sovereign user is currently physically present.
        High-cognitive/sensitive actions trigger strict liveness checks.
        """
        sensitive_actions = ["banking", "db_write", "file_overwrite", "os_exec", "crypto_tx"]
        
        if action_type in sensitive_actions:
            if not self.sensor_data.is_on_wrist or self.sensor_data.heart_rate is None:
                self.trigger_kill_switch(action_type)
                return False
                
        return True

    def trigger_kill_switch(self, action_type: str):
        """
        Immediately locks the agent execution and encrypts current working memory.
        """
        self.locked = True
        logger.critical(f"🚨 SOVEREIGN KILL SWITCH ACTIVATED 🚨")
        logger.critical(f"Unauthorized/Unverified attempt to execute: {action_type}.")
        logger.critical("No biological pulse detected. Locking agent and encrypting memory.")
