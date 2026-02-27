
import platform
import os
import subprocess
import sys
from typing import Dict, Any

class HardwareAbstraction:
    """
    Detects the host environment and applies platform-specific optimization flags.
    Targeting: Raspberry Pi 5 (ARM64 Linux), Intel Mac, and Apple Silicon.
    """
    
    @staticmethod
    def get_hardware_profile() -> Dict[str, Any]:
        system = platform.system()
        machine = platform.machine()
        processor = platform.processor()
        
        profile = {
            "os": system,
            "arch": machine,
            "platform_type": "UNKNOWN",
            "optimizations": {
                "enable_mps": False,
                "quantization": "FP32",
                "swap_backed": False,
                "sleep_prevention": False
            },
            "python_path": sys.executable
        }

        # 1. Apple Silicon Optimization
        if system == "Darwin" and machine == "arm64":
            profile["platform_type"] = "APPLE_SILICON"
            profile["optimizations"].update({
                "enable_mps": True,  # Metal Performance Shaders
                "quantization": "FP16",
                "sleep_prevention": True
            })
            # Shared memory awareness: M-series chips benefit from aggressive GC
            import gc
            gc.set_threshold(500, 5, 5)

        # 2. Intel Mac Optimization
        elif system == "Darwin" and machine == "x86_64":
            profile["platform_type"] = "INTEL_MAC"
            profile["optimizations"].update({
                "enable_mps": False,
                "quantization": "FP32",
                "sleep_prevention": True
            })

        # 3. Raspberry Pi 5 / Linux ARM64 Optimization
        elif system == "Linux" and (machine == "aarch64" or machine == "armv7l"):
            # Verify if it's a Pi by checking device-tree or cpuinfo
            is_pi = False
            try:
                if os.path.exists("/proc/device-tree/model"):
                    with open("/proc/device-tree/model", "r") as f:
                        if "Raspberry Pi" in f.read():
                            is_pi = True
            except:
                pass

            if is_pi:
                profile["platform_type"] = "RASPBERRY_PI_5"
                profile["optimizations"].update({
                    "enable_mps": False,
                    "quantization": "INT8",  # Prioritize speed on CPU
                    "swap_backed": True     # Save RAM for reasoning
                })
            else:
                profile["platform_type"] = "GENERIC_LINUX_ARM"

        return profile

    @staticmethod
    def get_service_path_logic() -> str:
        """Determines the correct binary path for service templates."""
        system = platform.system()
        machine = platform.machine()
        
        if system == "Darwin":
            if machine == "arm64":
                return "/opt/homebrew/bin/python3"
            return "/usr/local/bin/python3"
        return "/usr/bin/python3"

# Global Hardware Profile
PLATFORM_PROFILE = HardwareAbstraction.get_hardware_profile()
