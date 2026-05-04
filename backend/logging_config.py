"""
Centralized structured logging for the Polytope Sovereign OS backend.
Uses structlog for JSON-formatted, ELK/Datadog-compatible log output.

Usage in any module:
    from backend.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("event_name", key="value")
"""
import logging
import sys
import structlog
from opentelemetry import trace


def add_otel_trace_id(logger, method_name, event_dict):
    """Injects current OTel trace and span IDs into the log event."""
    span = trace.get_current_span()
    if span and span.is_recording():
        ctx = span.get_span_context()
        if ctx.is_valid:
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def sensitive_masker(logger, method_name, event_dict):
    """Redacts sensitive values based on keys defined in settings."""
    # We import settings here to avoid circular imports during early boot
    try:
        from .config import settings
        keys_to_mask = getattr(settings, "SENSITIVE_LOG_KEYS", [])
    except (ImportError, AttributeError):
        # Fallback if settings aren't ready
        keys_to_mask = ["key", "secret", "token", "password", "key_id"]

    for key in event_dict:
        if any(k.lower() in key.lower() for k in keys_to_mask):
            val = event_dict[key]
            if isinstance(val, str) and len(val) > 8:
                event_dict[key] = f"{val[:4]}...{val[-4:]} [REDACTED]"
            else:
                event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging(app_env: str = "development") -> None:
    """
    Configures structlog to wrap the stdlib logging module.
    Call once at application startup (e.g., in lifespan).

    In production: JSON output for ELK/Datadog ingestion.
    In development: colored, human-readable console output.
    """
    is_production = app_env in ("production", "staging")

    # --- Shared processors that run on every log entry ---
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        add_otel_trace_id,
        sensitive_masker,  # Redact secrets before they hit the renderer
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.PositionalArgumentsFormatter(),
    ]

    if is_production:
        # Production: emit machine-parseable JSON (one object per line)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development: colorful, human-readable console output
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            # Filter by log level before rendering
            structlog.stdlib.filter_by_level,
            # Format exception info using structlog's formatter
            structlog.processors.format_exc_info,
            # Prepare event dict for stdlib ProcessorFormatter
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure the stdlib root logger to use structlog's ProcessorFormatter
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO if is_production else logging.DEBUG)

    # Initialize Sentry if DSN is provided
    try:
        from .config import settings
        if settings.SENTRY_DSN and is_production:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            from sentry_sdk.integrations.redis import RedisIntegration
            from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
            
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
                environment=app_env,
                integrations=[
                    FastApiIntegration(),
                    RedisIntegration(),
                    SqlalchemyIntegration(),
                ],
            )
            logger.info("Sentry monitoring online.")
    except (ImportError, Exception) as e:
        # We don't want to crash boot if Sentry fails to load
        pass

    # Quiet noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Returns a structlog-wrapped logger.
    Drop-in replacement for logging.getLogger().
    """
    return structlog.get_logger(name)
