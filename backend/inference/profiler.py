import psutil
import platform
import logging
from typing import Dict, Any

logger = logging.getLogger("HardwareProfiler")

class HardwareProfiler:
    """
    [ PPN-020 ] Hardware Tiering Matrix.
    Dynamically profiles Unified Memory (Mac) or VRAM (PC) to select the optimal Gemma 4 variant.
    """
    
    # Gemma 4 variants mapped to their required memory footprints
    MODELS = {
        "DENSE_31B_BF16": "Alluci/alluci-polytope-gemma-4-31b-bf16",
        "DENSE_31B_4BIT": "Alluci/alluci-polytope-gemma-4-31b-4bit",
        "MOE_26B_4BIT": "Alluci/alluci-polytope-gemma-4-26b-a4b-4bit",
        "DENSE_12B_4BIT": "Alluci/alluci-polytope-gemma-4-12B-it-4bit",
        "EDGE_2B_4BIT": "Alluci/alluci-polytope-gemma-4-e2b-it-4bit"
    }

    @staticmethod
    def get_system_profile() -> Dict[str, Any]:
        """Returns the hardware profile and the recommended model tier."""
        system = platform.system()
        is_apple_silicon = system == 'Darwin' and platform.machine() == 'arm64'
        
        total_memory_gb = 16.0  # Safe fallback
        vram_gb = 0.0
        
        try:
            # Base System RAM
            ram_bytes = psutil.virtual_memory().total
            system_ram_gb = ram_bytes / (1024 ** 3)
            
            if is_apple_silicon:
                # Apple uses Unified Memory, so System RAM = VRAM
                total_memory_gb = system_ram_gb
            else:
                # PC (Windows/Linux) - Check for dedicated GPU VRAM using pynvml
                total_memory_gb = system_ram_gb
                try:
                    import pynvml
                    pynvml.nvmlInit()
                    device_count = pynvml.nvmlDeviceGetCount()
                    if device_count > 0:
                        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                        vram_gb = info.total / (1024 ** 3)
                        total_memory_gb = system_ram_gb + vram_gb
                    pynvml.nvmlShutdown()
                except Exception as e:
                    logger.debug(f"pynvml scan skipped or failed: {e}")
                    
        except Exception as e:
            logger.warning(f"Failed to read system memory: {e}. Defaulting to 16GB.")

        # Determine optimal model based on the Sovereign Architecture matrix (5 Tiers)
        if total_memory_gb >= 96.0:
            recommended_model = HardwareProfiler.MODELS["DENSE_31B_BF16"]
            tier = "TIER_0_ULTRA"
        elif total_memory_gb >= 60.0:
            recommended_model = HardwareProfiler.MODELS["DENSE_31B_4BIT"]
            tier = "TIER_1_MAX"
        elif total_memory_gb >= 30.0:
            recommended_model = HardwareProfiler.MODELS["MOE_26B_4BIT"]
            tier = "TIER_2_PRO"
        elif total_memory_gb >= 15.0:
            recommended_model = HardwareProfiler.MODELS["DENSE_12B_4BIT"]
            tier = "TIER_3_BASE"
        else:
            recommended_model = HardwareProfiler.MODELS["EDGE_2B_4BIT"]
            tier = "TIER_4_EDGE"

        return {
            "total_memory_gb": round(total_memory_gb, 2),
            "vram_gb": round(vram_gb, 2),
            "is_apple_silicon": is_apple_silicon,
            "os": system,
            "tier": tier,
            "recommended_model": recommended_model
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    profile = HardwareProfiler.get_system_profile()
    logger.info(f"Hardware Profile: {profile}")
