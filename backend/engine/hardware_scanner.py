import platform
from typing import Literal

BackendType = Literal["mlx", "torch_cuda", "numpy_cpu"]

class HardwareScanner:
    """
    Sovereign Hardware Scanner
    Detects local hardware topology to dynamically route inference requests to the
    optimal mathematical backend, ensuring zero-compilation frictionless deployment.
    """
    
    @staticmethod
    def check_cuda_available() -> bool:
        """Safely checks for CUDA without crashing if torch isn't installed."""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    @staticmethod
    def get_optimal_backend() -> BackendType:
        """
        Determines the optimal tensor projection backend.
        Primary: Apple MLX (arm64 Mac)
        Secondary: PyTorch CUDA (Windows/Linux)
        Fallback: NumPy CPU
        """
        os_name = platform.system()
        arch = platform.machine().lower()
        
        if os_name == "Darwin" and arch == "arm64":
            try:
                import mlx.core
                return "mlx"
            except ImportError:
                pass
        elif os_name in ["Windows", "Linux"]:
            if HardwareScanner.check_cuda_available():
                return "torch_cuda"
        
        return "numpy_cpu"
