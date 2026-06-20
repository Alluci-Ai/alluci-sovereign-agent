import json
import statistics
import os
from pathlib import Path
from typing import List

class CalibrationManager:
    """
    Manages the fluid baseline for topological thresholds (Stage 2: PPN/DPK).
    Replaces the rigid 0.15 threshold with Continuous Statistical Normalization.
    """
    def __init__(self):
        self.cache_dir = Path(".alluci_vault")
        self.cache_path = self.cache_dir / "dpk_calibration_cache.json"
        self.rbm_path = self.cache_dir / "rbm_profiles.json"
        self.avl_cache_path = self.cache_dir / "avl_calibration_cache.json"
        self.ace_cache_path = self.cache_dir / "ace_baseline_cache.json"
        self.history: List[float] = []
        self.avl_history: List[dict] = []
        self.ace_history: List[float] = [] # Stress/Tension history
        self.rbm_profiles = {}  # Relational Boundary Manifolds
        self.load_cache()

    def load_cache(self):
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r") as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []
        
        if self.rbm_path.exists():
            try:
                with open(self.rbm_path, "r") as f:
                    self.rbm_profiles = json.load(f)
            except Exception:
                self.rbm_profiles = {}
                
        if self.avl_cache_path.exists():
            try:
                with open(self.avl_cache_path, "r") as f:
                    self.avl_history = json.load(f)
            except Exception:
                self.avl_history = []
                
        if self.ace_cache_path.exists():
            try:
                with open(self.ace_cache_path, "r") as f:
                    self.ace_history = json.load(f)
            except Exception:
                self.ace_history = []

    def save_cache(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self.cache_path, "w") as f:
            json.dump(self.history, f)
        with open(self.rbm_path, "w") as f:
            json.dump(self.rbm_profiles, f)
        with open(self.avl_cache_path, "w") as f:
            json.dump(self.avl_history, f)
        with open(self.ace_cache_path, "w") as f:
            json.dump(self.ace_history, f)

    def get_dynamic_threshold(self, origin: str = "local", soul_preferences: dict = None) -> float:
        """
        Calculates the fluid baseline.
        Local origins use Discovery Mode & Continuous Normalization.
        External origins use their Relational Boundary Manifold (RBM) or Fortress Mode.
        """
        # 1. Zero-Trust Relational Management
        if origin != "local":
            # Fortress Mode or RBM
            if origin in self.rbm_profiles:
                profile = self.rbm_profiles[origin]
                if profile.get("frozen", False):
                    # RBM Freeze Protocol
                    raise Exception("RBM_FROZEN")
                history = profile.get("history", [])
                if len(history) < 3:
                    return 0.10  # Strict Fortress Mode until verified
                mean_shift = statistics.mean(history)
                std_shift = statistics.stdev(history) if len(history) > 1 else 0.02
                return mean_shift + (2 * std_shift) # Tighter boundary for external
            else:
                return 0.05  # Absolute minimum for unknown external origin (Fortress Mode)

        # 2. Local Discovery Mode (Simulated Annealing)
        if len(self.history) < 5:
            base = 0.40 # Highly relaxed
            if soul_preferences:
                creativity = soul_preferences.get('creativity', 0.5)
                base += (creativity - 0.5) * 0.2
            return base
            
        # 3. Continuous Statistical Normalization
        mean_shift = statistics.mean(self.history)
        std_shift = statistics.stdev(self.history) if len(self.history) > 1 else 0.05
        
        # Normalization: Mean + 3 Sigma
        return max(0.15, mean_shift + (3 * std_shift))

    def log_approved_trajectory(self, topology_shift: float, origin: str = "local"):
        """Logs the geometric signature into the calibration cache for self-healing."""
        if origin == "local":
            self.history.append(topology_shift)
            if len(self.history) > 200:
                self.history = self.history[-200:]
        else:
            if origin not in self.rbm_profiles:
                self.rbm_profiles[origin] = {"history": [], "frozen": False}
            self.rbm_profiles[origin]["history"].append(topology_shift)
            if len(self.rbm_profiles[origin]["history"]) > 100:
                self.rbm_profiles[origin]["history"] = self.rbm_profiles[origin]["history"][-100:]
        
        self.save_cache()
        
    def freeze_origin(self, origin: str):
        if origin not in self.rbm_profiles:
            self.rbm_profiles[origin] = {"history": [], "frozen": False}
        self.rbm_profiles[origin]["frozen"] = True
        self.save_cache()
        
    def restore_origin(self, origin: str):
        if origin in self.rbm_profiles:
            self.rbm_profiles[origin]["frozen"] = False
            self.save_cache()
            
    def log_avl_override(self, budget_used: float, origin: str = "local", psi: float = 0.0):
        """Logs the specific execution sequence (DAG budget) and biometric state into the AVL calibration cache for Dual-Signal LoRA."""
        self.avl_history.append({"budget": budget_used, "origin": origin, "psi": psi})
        if len(self.avl_history) > 200:
            self.avl_history = self.avl_history[-200:]
        self.save_cache()

    def log_ace_telemetry(self, stress_score: float):
        """Logs continuous biometric tension (stress score) to form a fluid baseline."""
        self.ace_history.append(stress_score)
        # Keep a moving window of the last 1000 telemetry points for continuous normalization
        if len(self.ace_history) > 1000:
            self.ace_history = self.ace_history[-1000:]
        self.save_cache()

    def get_ace_baseline(self) -> dict:
        """
        Calculates the user's specific normalized biometric baseline.
        Returns the mean and standard deviation.
        """
        if len(self.ace_history) < 10:
            # ACE "Discovery Mode": assume nominal baseline
            return {"mean": 50.0, "std": 10.0}
            
        mean_stress = statistics.mean(self.ace_history)
        std_stress = statistics.stdev(self.ace_history) if len(self.ace_history) > 1 else 10.0
        
        return {"mean": mean_stress, "std": std_stress}
