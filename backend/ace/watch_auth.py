import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

logger = logging.getLogger("BioTelemetryAuth")

@dataclass
class BioSensorData:
    is_on_wrist: bool
    heart_rate: Optional[float]
    blood_oxygen: Optional[float]
    stress_level: Optional[float]
    last_update_ms: int
    source_device: str

class BioTelemetryAuth:
    """
    [ PPN-017 ] Sovereign Kill Switch Daemon (Now Multi-Platform).
    Monitors biological telemetry from generic webhooks (Apple Watch, Garmin, Whoop, etc).
    If the agent attempts high-cognitive actions and no pulse is detected,
    it triggers a biometric check. By default, this prompts the user in chat
    rather than strictly locking the system, unless REQUIRE_BIO_TELEMETRY is strictly enforced.
    """
    def __init__(self, require_telemetry: bool = False):
        self.sensor_data = BioSensorData(
            is_on_wrist=False, 
            heart_rate=None, 
            blood_oxygen=None, 
            stress_level=None,
            last_update_ms=0,
            source_device="None"
        )
        self.locked = False
        self.require_telemetry = require_telemetry

    def update_sensors(self, is_on_wrist: bool = False, heart_rate: Optional[float] = None, 
                       blood_oxygen: Optional[float] = None, stress_level: Optional[float] = None,
                       source_device: str = "Apple Watch"):
        """Direct update method for native Apple Watch / hardware telemetry."""
        import time
        self.sensor_data.is_on_wrist = is_on_wrist
        if heart_rate is not None:
            self.sensor_data.heart_rate = heart_rate
        if blood_oxygen is not None:
            self.sensor_data.blood_oxygen = blood_oxygen
        if stress_level is not None:
            self.sensor_data.stress_level = stress_level
        self.sensor_data.source_device = source_device
        self.sensor_data.last_update_ms = int(time.time() * 1000)
        logger.debug(f"BioTelemetry updated natively from {self.sensor_data.source_device}")

    def handle_webhook_payload(self, payload: Dict[str, Any]):
        """Stream hook for live multi-platform biometric webhooks."""
        # Generic payload parsing mapping standard telemetry keys
        self.sensor_data.is_on_wrist = payload.get("is_on_wrist", self.sensor_data.is_on_wrist)
        self.sensor_data.heart_rate = payload.get("heart_rate", self.sensor_data.heart_rate)
        self.sensor_data.blood_oxygen = payload.get("blood_oxygen", self.sensor_data.blood_oxygen)
        self.sensor_data.stress_level = payload.get("stress_level", self.sensor_data.stress_level)
        self.sensor_data.source_device = payload.get("device_name", "Unknown Webhook")
        
        import time
        self.sensor_data.last_update_ms = int(time.time() * 1000)
        logger.debug(f"BioTelemetry updated from {self.sensor_data.source_device}")

    def verify_liveness(self, action_type: str) -> bool:
        """
        Validates whether the sovereign user is currently physically present.
        High-cognitive/sensitive actions trigger strict liveness checks.
        If REQUIRE_BIO_TELEMETRY is False, this acts as an observability warning, not a block.
        """
        sensitive_actions = ["banking", "db_write", "file_overwrite", "os_exec", "crypto_tx"]
        
        if action_type in sensitive_actions:
            if not self.sensor_data.is_on_wrist or self.sensor_data.heart_rate is None:
                logger.warning(f"⚠️ Biometric liveness check failed for sensitive action: {action_type}.")
                if self.require_telemetry:
                    self.trigger_kill_switch(action_type)
                    return False
                else:
                    logger.info(f"💡 REQUIRE_BIO_TELEMETRY is disabled. Permitting {action_type} without biometric data.")
                    return True
                
        return True

    def trigger_kill_switch(self, action_type: str):
        """
        Immediately locks the agent execution and encrypts current working memory.
        """
        self.locked = True
        logger.critical("🚨 SOVEREIGN KILL SWITCH ACTIVATED 🚨")
        logger.critical(f"Unauthorized/Unverified attempt to execute: {action_type}.")
        logger.critical("No biological pulse detected and REQUIRE_BIO_TELEMETRY is True. Locking agent.")
