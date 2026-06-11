from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, REGISTRY
from ..metrics import metrics_router  # ensure metrics are registered
from ..security.auth import verify_authenticated

router = APIRouter()

@router.get("/json", response_class=JSONResponse, dependencies=[Depends(verify_authenticated)])
async def get_metrics_json():
    """Expose Prometheus metrics as JSON for HTMX polling.
    The output is a dict where each metric name maps to its current value(s).
    """
    # generate_latest returns the text exposition format. We'll parse it simply.
    raw = generate_latest(REGISTRY)
    # Simple parsing: each line like: metric_name value
    result = {}
    for line in raw.decode().splitlines():
        if line.startswith('#'):
            continue
        parts = line.split()
        if len(parts) >= 2:
            # metric may have labels, take first part as full metric identifier
            raw_name = parts[0]
            # Extract base metric name before any labels for JSON keys
            name = raw_name.split('{')[0]
            value = parts[-1]
            try:
                # Attempt to parse numeric values (int or float)
                num = float(value)
                if num.is_integer():
                    result[name] = int(num)
                else:
                    result[name] = num
            except ValueError:
                # Keep the raw string if parsing fails (e.g., histograms)
                result[name] = value
    return JSONResponse(content=result)
