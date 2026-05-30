"""
Structured Logging — JSON-formatted log output with correlation IDs.

Configures the root logger to emit structured JSON lines in production,
making logs parseable by log aggregation systems (ELK, CloudWatch, Datadog).
Each log record automatically includes the current request's correlation ID
when available via the CorrelationIdMiddleware.
"""

import logging
import sys
from contextvars import ContextVar

from pythonjsonlogger.json import JsonFormatter

# ── Context variable for request correlation ID ─────────────────────────
request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


class CorrelationIdFilter(logging.Filter):
    """Injects the current request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "-"  # type: ignore[attr-defined]
        return True


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure structured JSON logging for the application.

    Should be called once at application startup (in main.py).
    """
    root_logger = logging.getLogger()

    # Prevent duplicate handlers on reload
    if any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    formatter = JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
        rename_fields={
            "asctime": "timestamp",
            "levelname": "level",
            "name": "logger",
        },
    )
    handler.setFormatter(formatter)
    handler.addFilter(CorrelationIdFilter())

    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Silence noisy third-party loggers
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("opentelemetry").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
