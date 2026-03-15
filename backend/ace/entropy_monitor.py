import numpy as np
import logging
from ..logging_config import get_logger
from collections import deque
from typing import List

logger = get_logger("EntropyMonitor")

class EntropySpikeDetector:
    """
    Entropy Spike Detector.
    Source: PPN §Monitoring — entropy_sensor.cpp::detect_spike()

    Monitors graph entropy (H_G) over time. Sudden spikes indicate 
    topological ruptures or "hallucination cascades".
    """
    def __init__(self, window_size: int = 15):
        self.history = deque(maxlen=window_size)
        self.SPIKE_THRESHOLD = 2.0  # Z-score threshold for alert

    def push(self, h_norm: float) -> bool:
        """
        Pushes a new entropy measurement and returns True if a spike is detected.
        """
        if len(self.history) < 5:
            self.history.append(h_norm)
            return False

        mean = np.mean(self.history)
        std = max(float(np.std(self.history)), 0.1)
        z_score = abs(h_norm - mean) / std

        self.history.append(h_norm)

        if z_score > self.SPIKE_THRESHOLD:
            logger.warning(f"[MONITOR] Entropy Spike Detected! Z={z_score:.2f}")
            return True
        return False
