
import time
import psutil
from typing import Dict, Any

class MetricsTracker:
    def __init__(self):
        self.request_count = 0
        self.latency_sum = 0
        self.error_count = 0
        self.start_time = time.time()

    def record_request(self, latency: float, status_code: int):
        self.request_count += 1
        self.latency_sum += latency
        if status_code >= 400:
            self.error_count += 1

    def get_metrics_text(self) -> str:
        uptime = time.time() - self.start_time
        avg_latency = self.latency_sum / self.request_count if self.request_count > 0 else 0
        
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        
        lines = [
            "# HELP alluci_uptime_seconds_total Total uptime in seconds",
            "# TYPE alluci_uptime_seconds_total counter",
            f"alluci_uptime_seconds_total {uptime}",
            
            "# HELP alluci_requests_total Total number of HTTP requests processed",
            "# TYPE alluci_requests_total counter",
            f"alluci_requests_total {self.request_count}",
            
            "# HELP alluci_errors_total Total number of HTTP 4xx/5xx responses",
            "# TYPE alluci_errors_total counter",
            f"alluci_errors_total {self.error_count}",
            
            "# HELP alluci_avg_latency_seconds Average request latency in seconds",
            "# TYPE alluci_avg_latency_seconds gauge",
            f"alluci_avg_latency_seconds {avg_latency}",
            
            "# HELP alluci_cpu_percent Current CPU usage percentage",
            "# TYPE alluci_cpu_percent gauge",
            f"alluci_cpu_percent {cpu}",
            
            "# HELP alluci_ram_percent Current RAM usage percentage",
            "# TYPE alluci_ram_percent gauge",
            f"alluci_ram_percent {ram}",
        ]
        return "\n".join(lines) + "\n"

metrics = MetricsTracker()
