
import os
import time
import json
import psutil
import logging
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any
from env_config import PLATFORM_PROFILE

class HomeServerGuard:
    """
    Manages background execution stability, thermal safety, and memory governance.
    """
    def __init__(self, ram_threshold_gb: float = 4.0, checkpoint_interval: int = 60):
        self.ram_threshold = ram_threshold_gb * 1024 * 1024 * 1024  # Convert to bytes
        self.checkpoint_interval = checkpoint_interval
        self.last_checkpoint = 0
        self.recovery_file = "recovery.json"
        self.logger = logging.getLogger("PolytopeGuard")
        
        # Start sleep prevention if requested
        if PLATFORM_PROFILE["optimizations"]["sleep_prevention"]:
            self._prevent_sleep()

    def _prevent_sleep(self):
        """Uses macOS caffeinate to keep the home server awake."""
        if PLATFORM_PROFILE["os"] == "Darwin":
            try:
                subprocess.Popen(["caffeinate", "-i", "-s", "-w", str(os.getpid())], 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.logger.info("Sleep prevention (caffeinate) active.")
            except Exception as e:
                self.logger.warning(f"Failed to start caffeinate: {e}")

    def monitor_resources(self, task_graph: Dict[str, Any]):
        """Main loop for resource governance."""
        self._check_thermal_throttling()
        self._enforce_memory_governance()
        self._auto_prune_scratchpad()
        
        # Periodic Checkpointing
        if time.time() - self.last_checkpoint > self.checkpoint_interval:
            self._checkpoint_state(task_graph)

    def _check_thermal_throttling(self):
        """Reduces cycle frequency if hardware temperature is too high."""
        if PLATFORM_PROFILE["platform_type"] == "RASPBERRY_PI_5":
            try:
                with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                    temp = int(f.read()) / 1000.0
                    if temp > 75.0:  # Critical threshold for Pi 5
                        self.logger.warning(f"Thermal threshold reached ({temp}C). Throttling execution.")
                        time.sleep(1.0) # Introduce reasoning delay
            except:
                pass

    def _enforce_memory_governance(self):
        """Clears scratchpads and flushes caches if RAM exceeds threshold."""
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info().rss
        
        if mem_info > self.ram_threshold:
            self.logger.info("RAM threshold exceeded. Pruning volatile manifold caches...")
            # Trigger GC and clear internal buffers
            import gc
            gc.collect()
            # Placeholder for clearing vector embedding caches if applicable
            # self.vector_db.clear_cache()

    def _auto_prune_scratchpad(self):
        """Removes logs and temporary assets older than 24 hours."""
        log_dir = "logs/"
        if not os.path.exists(log_dir):
            return

        now = time.time()
        for f in os.listdir(log_dir):
            f_path = os.path.join(log_dir, f)
            if os.stat(f_path).st_mtime < now - (24 * 3600):
                try:
                    os.remove(f_path)
                    self.logger.debug(f"Pruned stale log: {f}")
                except:
                    pass

    def _checkpoint_state(self, state: Dict[str, Any]):
        """Persists the current task-graph to recovery.json."""
        try:
            with open(self.recovery_file, "w") as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "platform": PLATFORM_PROFILE["platform_type"],
                    "state": state
                }, f)
            self.last_checkpoint = time.time()
            self.logger.debug("System checkpoint created.")
        except Exception as e:
            self.logger.error(f"Checkpoint failure: {e}")

    def load_recovery(self) -> Dict[str, Any]:
        """Loads the last saved state if available."""
        if os.path.exists(self.recovery_file):
            try:
                with open(self.recovery_file, "r") as f:
                    data = json.load(f)
                    return data.get("state", {})
            except:
                pass
        return {}
