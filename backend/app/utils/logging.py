"""
Structured logging configuration for ML Speech Emotion Recognition API

Uses structlog for consistent, structured logging with correlation IDs.
Configured for both local development and production monitoring.
"""

import logging
import sys
from typing import Any

import structlog

from .config import get_settings


def setup_logging() -> None:
    """Configure structured logging for the application"""
    settings = get_settings()

    # Configure structlog processors
    processors: list[Any] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Use pretty console output for development, JSON for production
    if settings.debug:
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.debug else logging.INFO,
    )

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> Any:
    """Get a structured logger for the given module"""
    return structlog.get_logger(name)


def log_request_info(
    logger: structlog.stdlib.BoundLogger,
    method: str,
    url: str,
    headers: dict[str, Any],
    correlation_id: str,
) -> None:
    """Log HTTP request information with correlation tracking"""
    logger.info(
        "HTTP request received",
        method=method,
        url=url,
        correlation_id=correlation_id,
        user_agent=headers.get("user-agent"),
    )


def log_response_info(
    logger: structlog.stdlib.BoundLogger,
    status_code: int,
    correlation_id: str,
    duration_ms: float,
) -> None:
    """Log HTTP response information with correlation tracking"""
    logger.info(
        "HTTP response sent",
        status_code=status_code,
        correlation_id=correlation_id,
        duration_ms=duration_ms,
    )
