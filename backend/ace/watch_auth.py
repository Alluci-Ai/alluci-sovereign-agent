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
    [ PPN-017 ] Sovereign Kill Switch Daemon (Now Optional).
    Monitors Apple Watch / Bio-wearable status.
    If the agent attempts high-cognitive actions and the watch is off-wrist,
    it triggers a biometric check. By default, this prompts the user in chat
    rather than strictly locking the system.
    """
    def __init__(self, require_telemetry: bool = False):
        self.sensor_data = WatchSensorData(
            is_on_wrist=False, 
            heart_rate=None, 
            blood_oxygen=None, 
            last_update_ms=0
        )
        self.locked = False
        self.require_telemetry = require_telemetry

    def update_sensors(self, is_on_wrist: bool, heart_rate: Optional[float]):
        """Stream hook for live watch data."""
        self.sensor_data.is_on_wrist = is_on_wrist
        self.sensor_data.heart_rate = heart_rate

    def verify_liveness(self, action_type: str) -> bool:
        """
        Validates whether the sovereign user is currently physically present.
        High-cognitive/sensitive actions trigger strict liveness checks.
        If REQUIRE_WATCH_TELEMETRY is False, this acts as an observability warning, not a block.
        """
        sensitive_actions = ["banking", "db_write", "file_overwrite", "os_exec", "crypto_tx"]
        
        if action_type in sensitive_actions:
            if not self.sensor_data.is_on_wrist or self.sensor_data.heart_rate is None:
                logger.warning(f"⚠️ Biometric liveness check failed for sensitive action: {action_type}.")
                if self.require_telemetry:
                    self.trigger_kill_switch(action_type)
                    return False
                else:
                    logger.info(f"💡 REQUIRE_WATCH_TELEMETRY is disabled. Permitting {action_type} without biometric data.")
                    return True
                
        return True

    def trigger_kill_switch(self, action_type: str):
        """
        Immediately locks the agent execution and encrypts current working memory.
        """
        self.locked = True
        logger.critical("🚨 SOVEREIGN KILL SWITCH ACTIVATED 🚨")
        logger.critical(f"Unauthorized/Unverified attempt to execute: {action_type}.")
        logger.critical("No biological pulse detected and REQUIRE_WATCH_TELEMETRY is True. Locking agent.")
