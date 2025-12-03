"""
Custom Prometheus middleware for FastAPI with metrics compatible with
Grafana FastAPI Observability Dashboard (ID: 16110).

This middleware provides:
- fastapi_requests_total: Counter for total requests
- fastapi_requests_duration_seconds: Histogram for request duration
- fastapi_responses_total: Counter for responses by status code
- fastapi_requests_in_progress: Gauge for concurrent requests
- fastapi_exceptions_total: Counter for exceptions
- fastapi_app_info: Info gauge for app metadata
"""

import time
from typing import Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match

from opentelemetry import trace


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to collect Prometheus metrics compatible with FastAPI Observability Dashboard.

    Exposes metrics with 'fastapi_' prefix and 'app_name' label for dashboard compatibility.
    """

    # Class-level metric definitions (shared across instances)
    _metrics_initialized = False
    _app_info: Gauge
    _requests_total: Counter
    _responses_total: Counter
    _requests_duration: Histogram
    _requests_in_progress: Gauge
    _exceptions_total: Counter

    def __init__(self, app: FastAPI, app_name: str = "fastapi-app") -> None:
        super().__init__(app)
        self.app_name = app_name
        self._initialize_metrics()
        # Set app info gauge to 1 for this app_name (for label_values query)
        self._app_info.labels(app_name=self.app_name).set(1)

    @classmethod
    def _initialize_metrics(cls) -> None:
        """Initialize Prometheus metrics (once per process)."""
        if cls._metrics_initialized:
            return

        # App info gauge (using Gauge instead of Info to avoid _info suffix)
        cls._app_info = Gauge(
            name="fastapi_app_info",
            documentation="FastAPI application information",
            labelnames=["app_name"],
        )

        # Request counter
        cls._requests_total = Counter(
            name="fastapi_requests_total",
            documentation="Total count of requests by method, path, and app name",
            labelnames=["method", "path", "app_name"],
        )

        # Response counter with status code
        cls._responses_total = Counter(
            name="fastapi_responses_total",
            documentation="Total count of responses by method, path, status code, and app name",
            labelnames=["method", "path", "status_code", "app_name"],
        )

        # Request duration histogram with buckets optimized for web requests
        cls._requests_duration = Histogram(
            name="fastapi_requests_duration_seconds",
            documentation="Histogram of request duration by method, path, and app name",
            labelnames=["method", "path", "app_name"],
            buckets=(
                0.005,
                0.01,
                0.025,
                0.05,
                0.075,
                0.1,
                0.25,
                0.5,
                0.75,
                1.0,
                2.5,
                5.0,
                7.5,
                10.0,
                float("inf"),
            ),
        )

        # In-progress requests gauge
        cls._requests_in_progress = Gauge(
            name="fastapi_requests_in_progress",
            documentation="Gauge of requests currently being processed",
            labelnames=["method", "path", "app_name"],
        )

        # Exception counter
        cls._exceptions_total = Counter(
            name="fastapi_exceptions_total",
            documentation="Total count of exceptions raised by path and exception type",
            labelnames=["method", "path", "exception_type", "app_name"],
        )

        cls._metrics_initialized = True

    @staticmethod
    def get_path(request: Request) -> tuple[str, bool]:
        """
        Get the path template from the request, matching against defined routes.

        Returns:
            Tuple of (path_template, is_handled)
            - path_template: The route template (e.g., "/api/v1/users/{id}")
            - is_handled: True if the path matches a defined route
        """
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return route.path, True
        return request.url.path, False

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        """Process request and collect metrics."""
        method = request.method
        path, is_handled = self.get_path(request)

        # Skip metrics collection for unhandled paths and /metrics endpoint
        if not is_handled or path == "/metrics":
            return await call_next(request)

        # Track in-progress requests
        self._requests_in_progress.labels(
            method=method, path=path, app_name=self.app_name
        ).inc()

        # Increment request counter
        self._requests_total.labels(
            method=method, path=path, app_name=self.app_name
        ).inc()

        # Track request duration
        start_time = time.perf_counter()
        status_code = "500"  # Default to 500 in case of unhandled exception

        try:
            response = await call_next(request)
            status_code = str(response.status_code)
            return response

        except Exception as exc:
            # Track exception
            exception_type = type(exc).__name__
            self._exceptions_total.labels(
                method=method,
                path=path,
                exception_type=exception_type,
                app_name=self.app_name,
            ).inc()
            raise

        finally:
            # Record duration
            duration = time.perf_counter() - start_time

            # Try to get trace ID for exemplar correlation
            try:
                span = trace.get_current_span()
                if span and span.get_span_context().is_valid:
                    trace_id = format(span.get_span_context().trace_id, "032x")
                    # Record with exemplar (if supported)
                    self._requests_duration.labels(
                        method=method, path=path, app_name=self.app_name
                    ).observe(duration, {"trace_id": trace_id})
                else:
                    self._requests_duration.labels(
                        method=method, path=path, app_name=self.app_name
                    ).observe(duration)
            except Exception:
                # Fallback without exemplar
                self._requests_duration.labels(
                    method=method, path=path, app_name=self.app_name
                ).observe(duration)

            # Record response
            self._responses_total.labels(
                method=method,
                path=path,
                status_code=status_code,
                app_name=self.app_name,
            ).inc()

            # Decrement in-progress
            self._requests_in_progress.labels(
                method=method, path=path, app_name=self.app_name
            ).dec()


async def metrics_endpoint(request: Request) -> Response:
    """Prometheus metrics endpoint handler."""
    return Response(
        content=generate_latest(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
