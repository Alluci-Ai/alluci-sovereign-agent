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

    @staticmethod
    def get_optimal_polytope_variant(available_ram_gb: float, backend: BackendType) -> str:
        """
        Dynamically routes the agent to the optimal Sovereign Polytope model
        based on the host's total system memory and backend execution context.
        """
        is_mlx = backend == "mlx"
        prefix = "alluci-polytope-gemma-4"
        suffix = "mlx-4bit" if is_mlx else "Q4_K_M.gguf"

        if available_ram_gb >= 64:
            variant = "31b-it-4bit" if is_mlx else "31B-it-GGUF"
        elif available_ram_gb >= 32:
            variant = "26B-A4B-it-OptiQ-4bit" if is_mlx else "26B-A4B-it-GGUF"
        elif available_ram_gb >= 16:
            variant = "12B-it-OptiQ-4bit" if is_mlx else "12B-it-GGUF"
        elif available_ram_gb >= 8:
            variant = "e4b-it-OptiQ-4bit" if is_mlx else "E4B-it-GGUF"
        else:
            variant = "e2b-it-4bit" if is_mlx else "E2B-it-GGUF"

        return f"{prefix}-{variant}"

    @staticmethod
    def get_optimal_local_fallback_chain(context_size: int = 0) -> str:
        """
        Returns a progressive chain of local models formatted for the fallback router (e.g., 'local/xxx,local/yyy').
        Considers available RAM and context size to prevent OOM.
        """
        try:
            import psutil
            available_ram_gb = psutil.virtual_memory().available / (1024**3)
        except ImportError:
            available_ram_gb = 16.0 # Safe default if psutil is missing
            
        from ..config import settings
        
        # High context demands more KV cache, reducing model size capacity
        effective_ram = available_ram_gb
        if context_size > 32000:
            effective_ram *= 0.5
        elif context_size > 8000:
            effective_ram *= 0.75
            
        chain = []
        if effective_ram >= 32:
            chain.append(f"local/{settings.LOCAL_MODEL_MAX}")
        if effective_ram >= 24:
            chain.append(f"local/{settings.LOCAL_MODEL_STRONG}")
        if effective_ram >= 16:
            chain.append(f"local/{settings.LOCAL_MODEL_MEDIUM}")
        if effective_ram >= 8:
            chain.append(f"local/{settings.LOCAL_MODEL_LIGHT}")
            
        chain.append(f"local/{settings.LOCAL_MODEL_LITE}")
        
        # Remove duplicates while preserving order
        seen = set()
        deduped = [x for x in chain if not (x in seen or seen.add(x))]
        
        return ",".join(deduped)

    @staticmethod
    def get_optimal_max_tokens(context_size: int = 0) -> int:
        """
        Dynamically calculates the safe maximum output token budget for the LLM
        based on available system RAM/VRAM to prevent OOM errors.
        """
        try:
            import psutil
            available_ram_gb = psutil.virtual_memory().available / (1024**3)
        except ImportError:
            available_ram_gb = 16.0  # Safe default if psutil is missing
            
        if available_ram_gb > 64:
            return 16384
        elif available_ram_gb > 32:
            return 8192
        else:
            return 4096
