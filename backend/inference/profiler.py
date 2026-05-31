import psutil
import platform
import logging
from typing import Dict, Any

logger = logging.getLogger("HardwareProfiler")

class HardwareProfiler:
    """
    [ PPN-020 ] Hardware Tiering Matrix.
    Dynamically profiles Apple Silicon memory to select the optimal Gemma 4 variant.
    """
    
    # Gemma 4 variants mapped to their required memory footprints
    MODELS = {
        "DENSE_31B": "google/gemma-4-31b-dense",
        "MOE_26B_4BIT": "google/gemma-4-26b-moe-4bit",
        "DENSE_8B_4BIT": "google/gemma-4-8b-4bit",
        "EDGE_2B": "google/gemma-4-e2b"
    }

    @staticmethod
    def get_system_profile() -> Dict[str, Any]:
        """Returns the hardware profile and the recommended model tier."""
        try:
            # psutil.virtual_memory().total returns bytes
            ram_bytes = psutil.virtual_memory().total
            ram_gb = ram_bytes / (1024 ** 3)
        except Exception as e:
            logger.warning(f"Failed to read system RAM: {e}. Defaulting to 16GB.")
            ram_gb = 16.0

        is_apple_silicon = platform.system() == 'Darwin' and platform.machine() == 'arm64'
        
        # Determine optimal model based on the Sovereign Architecture matrix
        if ram_gb >= 60.0:
            # 64GB+ Mac Studio / Max
            recommended_model = HardwareProfiler.MODELS["DENSE_31B"]
            tier = "TIER_1_MAX"
        elif ram_gb >= 30.0:
            # 32GB - 63GB MacBook Pro
            recommended_model = HardwareProfiler.MODELS["MOE_26B_4BIT"]
            tier = "TIER_2_PRO"
        elif ram_gb >= 15.0:
            # 16GB - 31GB MacBook Air / Base Pro
            recommended_model = HardwareProfiler.MODELS["DENSE_8B_4BIT"]
            tier = "TIER_3_BASE"
        else:
            # <16GB Legacy / Edge Allocation
            recommended_model = HardwareProfiler.MODELS["EDGE_2B"]
            tier = "TIER_4_EDGE"

        return {
            "ram_gb": round(ram_gb, 2),
            "is_apple_silicon": is_apple_silicon,
            "tier": tier,
            "recommended_model": recommended_model
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    profile = HardwareProfiler.get_system_profile()
    logger.info(f"Hardware Profile: {profile}")
