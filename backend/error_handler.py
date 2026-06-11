import sentry_sdk
from .config import settings
from functools import wraps

# Initialize Sentry SDK if DSN is provided
if getattr(settings, "SENTRY_DSN", None):
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=getattr(settings, "SENTRY_TRACES_SAMPLE_RATE", 0.1),
        environment=getattr(settings, "APP_ENV", "development"),
    )

def error_report(func):
    """Decorator for async functions to report exceptions to Sentry.

    Usage:
        @error_report
        async def my_endpoint(...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Capture the exception in Sentry before re-raising
            sentry_sdk.capture_exception(e)
            raise
    return wrapper

def error_report_sync(func):
    """Decorator for synchronous functions to report exceptions to Sentry."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise
    return wrapper
