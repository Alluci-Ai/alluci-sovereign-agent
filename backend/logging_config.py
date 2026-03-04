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
