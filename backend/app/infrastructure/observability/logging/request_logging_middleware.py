"""
Structured logging configuration for ML Speech Emotion Recognition API.

Uses structlog for consistent, structured logging with:
- OpenTelemetry trace context injection (trace_id, span_id)
- Request/response logging middleware
- Error capture with full context
- Class/function name extraction
- JSON output for production, pretty console for development
"""

import inspect
import logging
import sys
import time
import uuid
from collections.abc import Callable
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from app.utils.config import get_settings


def add_trace_context(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Structlog processor to add OpenTelemetry trace context to log entries.

    Injects trace_id and span_id from the current active span.

    Args:
        logger: Structlog logger instance (Any type for compatibility with structlog processors)
        method_name: Method name being called
        event_dict: Event dictionary to be logged
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        ctx = span.get_span_context()
        event_dict["trace_id"] = format(ctx.trace_id, "032x")
        event_dict["span_id"] = format(ctx.span_id, "016x")
    return event_dict


def add_caller_info(
    logger: Any,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Structlog processor to add caller information (module, function, line).

    Walks up the call stack to find the actual caller outside structlog.

    Args:
        logger: Structlog logger instance (Any type for compatibility with structlog processors)
        method_name: Method name being called
        event_dict: Event dictionary to be logged
    """
    # Skip frames from structlog and logging internals
    frame = inspect.currentframe()
    if frame is None:
        return event_dict

    try:
        # Walk up the stack to find the actual caller
        for _ in range(10):  # Limit iterations to prevent infinite loop
            frame = frame.f_back
            if frame is None:
                break
            module = frame.f_globals.get("__name__", "")
            # Skip structlog, logging, and this module's internals
            if not any(
                skip in module
                for skip in [
                    "structlog",
                    "logging",
                    "_logging",
                    "app.utils.logging",
                    "app.infrastructure.observability.logging",
                ]
            ):
                event_dict["caller_module"] = module
                event_dict["caller_function"] = frame.f_code.co_name
                event_dict["caller_line"] = frame.f_lineno

                # Try to get class name if method is part of a class
                local_vars = frame.f_locals
                if "self" in local_vars:
                    event_dict["caller_class"] = type(local_vars["self"]).__name__
                elif "cls" in local_vars:
                    event_dict["caller_class"] = local_vars["cls"].__name__

                break
    finally:
        del frame

    return event_dict


def setup_logging() -> None:
    """Configure structured logging for the application with trace correlation."""
    settings = get_settings()

    # Configure structlog processors
    processors: list[Any] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        add_trace_context,  # Add OpenTelemetry trace context
        add_caller_info,  # Add caller information
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Use pretty console output for development, JSON for production
    if settings.debug:
        processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        )
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
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("opentelemetry").setLevel(logging.WARNING)


def get_logger(name: str) -> Any:
    """Get a structured logger for the given module."""
    return structlog.get_logger(name)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured request/response logging with trace correlation.

    Logs every incoming request and outgoing response with:
    - Request: method, path, headers, client IP, request_id
    - Response: status code, duration, content length
    - Errors: exception type, message, traceback
    """

    def __init__(self, app: FastAPI, app_name: str = "fastapi-app") -> None:
        super().__init__(app)
        self.app_name = app_name
        self.logger = get_logger("request_logger")

    @staticmethod
    def get_path_template(request: Request) -> str:
        """Get the route template path (e.g., /api/v1/users/{id})."""
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return route.path
        return request.url.path

    @staticmethod
    def get_client_ip(request: Request) -> str:
        """Extract client IP from request, handling X-Forwarded-For header."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    @staticmethod
    def generate_request_id() -> str:
        """Generate a unique request ID."""
        return str(uuid.uuid4())

    def _should_skip_logging(self, path: str) -> bool:
        """Determine if logging should be skipped for this path."""
        skip_paths = {"/health", "/metrics", "/ready", "/live"}
        return path in skip_paths

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process request and log request/response details."""
        path_template = self.get_path_template(request)

        # Skip logging for health/metrics endpoints
        if self._should_skip_logging(path_template):
            return await call_next(request)

        # Generate request ID and bind to logger context
        request_id = request.headers.get("x-request-id") or self.generate_request_id()
        client_ip = self.get_client_ip(request)

        # Get trace context for logging
        trace_id: str | None = None
        span_id: str | None = None
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            ctx = span.get_span_context()
            trace_id = format(ctx.trace_id, "032x")
            span_id = format(ctx.span_id, "016x")

        # Log incoming request
        self.logger.info(
            "HTTP request received",
            request_id=request_id,
            method=request.method,
            path=path_template,
            url=str(request.url),
            client_ip=client_ip,
            user_agent=request.headers.get("user-agent"),
            content_type=request.headers.get("content-type"),
            content_length=request.headers.get("content-length"),
            app_name=self.app_name,
            trace_id=trace_id,
            span_id=span_id,
        )

        # Track request duration
        start_time = time.perf_counter()
        status_code = 500  # Default to 500 in case of unhandled exception

        try:
            response = await call_next(request)
            status_code = response.status_code

            # Add request ID to response headers
            response.headers["x-request-id"] = request_id
            if trace_id:
                response.headers["x-trace-id"] = trace_id

            return response

        except Exception as exc:
            # Log exception details
            self.logger.exception(
                "HTTP request failed with exception",
                request_id=request_id,
                method=request.method,
                path=path_template,
                exception_type=type(exc).__name__,
                exception_message=str(exc),
                app_name=self.app_name,
                trace_id=trace_id,
                span_id=span_id,
            )
            raise

        finally:
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log response details
            log_level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"
            getattr(self.logger, log_level)(
                "HTTP response sent",
                request_id=request_id,
                method=request.method,
                path=path_template,
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
                app_name=self.app_name,
                trace_id=trace_id,
                span_id=span_id,
            )


def log_request_info(
    logger: structlog.stdlib.BoundLogger,
    method: str,
    url: str,
    headers: dict[str, Any],
    correlation_id: str,
) -> None:
    """Log HTTP request information with correlation tracking."""
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
    """Log HTTP response information with correlation tracking."""
    logger.info(
        "HTTP response sent",
        status_code=status_code,
        correlation_id=correlation_id,
        duration_ms=duration_ms,
    )


def log_error(
    logger: structlog.stdlib.BoundLogger,
    error: Exception,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Log error with full context and traceback.

    Args:
        logger: The structured logger instance
        error: The exception to log
        context: Additional context to include in the log
    """
    error_context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    if context:
        error_context.update(context)

    logger.exception("Error occurred", **error_context)
