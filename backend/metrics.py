from prometheus_client import (
    Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST, REGISTRY
)
from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
import time

# ── Metric Definitions ────────────────────────────────────────────────────────

REQUEST_COUNT = Counter(
    "alluci_http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status_code"]
)

REQUEST_LATENCY = Histogram(
    "alluci_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

ACTIVE_CONNECTIONS = Gauge(
    "alluci_websocket_connections_active",
    "Number of active WebSocket connections"
)

INFERENCE_FAILOVER = Counter(
    "alluci_inference_failover_total",
    "Total number of inference routing failover events",
    ["source_tier", "target_tier"]
)

DREAM_CYCLE_LOSS = Gauge(
    "alluci_dream_cycle_loss",
    "Latest DPO training loss from the Dream Cycle Forge"
)

MEMORY_CONSOLIDATION_TOTAL = Counter(
    "alluci_memory_consolidation_total",
    "Total number of H-LSM memory consolidation sweeps",
    ["tier"]
)

# New Prometheus metrics
LLM_REQUESTS_TOTAL = Counter(
    "alluci_llm_requests_total",
    "Total LLM requests with provider label",
    ["provider"]
)

AVL_GATE_REJECTIONS_TOTAL = Counter(
    "alluci_avl_gate_rejections_total",
    "Total AVL gate rejections",
    []
)

HLSM_HEALTH_SCORE = Gauge(
    "alluci_hlsm_health_score",
    "Current H-LSM memory health score (0.0 - 1.0)"
)

HLSM_DUPLICATE_CLUSTERS = Gauge(
    "alluci_hlsm_duplicate_clusters_total",
    "Current number of duplicate clusters across all H-LSM memory tiers"
)

HLSM_SELF_HEALING_TOTAL = Counter(
    "alluci_hlsm_self_healing_total",
    "Total autonomous memory self-healing deduplication sweeps executed"
)

# ── Middleware ────────────────────────────────────────────────────────────────

async def metrics_middleware(request: Request, call_next):
    """Records per-request latency and status code metrics."""
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start

    path = request.url.path
    # Normalize path
    for segment in path.split("/"):
        if segment.isdigit() or (len(segment) > 20 and "-" in segment):
            path = path.replace(segment, "{id}")

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=path,
        status_code=str(response.status_code)
    ).inc()

    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=path
    ).observe(duration)

    return response

# ── Router ────────────────────────────────────────────────────────────────────

metrics_router = APIRouter(tags=["Observability"])

@metrics_router.get("/metrics", include_in_schema=False)
async def get_metrics():
    """Prometheus scrape endpoint."""
    return PlainTextResponse(
        content=generate_latest(REGISTRY).decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST
    )

class MetricsFacade:
    def __init__(self):
        self.start_time = time.time()

    def increment_counter(self, name: str, labels: dict = None):  # type: ignore
        """Dynamic counter increment (standard facade pattern)."""
        # Mapping for common counters used in the codebase
        mapping = {
            "redis_init_failures_total": REQUEST_COUNT.labels(method="INTERNAL", endpoint="REDIS", status_code="500"),
            "redis_not_configured_total": REQUEST_COUNT.labels(method="INTERNAL", endpoint="REDIS", status_code="400"),
        }
        if name in mapping:
            mapping[name].inc()

metrics = MetricsFacade()
