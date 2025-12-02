"""
Unit tests for Prometheus middleware.

These tests verify that the PrometheusMiddleware exposes metrics with the correct
names and labels required by the Grafana FastAPI Observability Dashboard (ID: 16110).
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.routing import Route

from app.middleware.prometheus import PrometheusMiddleware, metrics_endpoint


class TestPrometheusMiddlewareMetricNames:
    """Test that metric names are correct for dashboard compatibility."""

    def setup_method(self) -> None:
        """Reset metrics state before each test."""
        # Reset the class-level metrics initialized flag to allow re-initialization
        PrometheusMiddleware._metrics_initialized = False

    def test_app_info_metric_name_no_suffix(self) -> None:
        """
        Test that fastapi_app_info metric does NOT have _info suffix.

        The dashboard expects 'fastapi_app_info' but prometheus_client.Info()
        automatically adds '_info' suffix, resulting in 'fastapi_app_info_info'.
        We use Gauge instead to avoid this issue.
        """
        from prometheus_client import REGISTRY

        # Clear any existing collectors for clean test
        collectors_to_remove = []
        for collector in list(REGISTRY._names_to_collectors.values()):
            if hasattr(collector, "_name") and "fastapi" in getattr(
                collector, "_name", ""
            ):
                collectors_to_remove.append(collector)

        for collector in collectors_to_remove:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass

        PrometheusMiddleware._metrics_initialized = False

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint() -> dict:
            return {"status": "ok"}

        # Add middleware
        with patch("app.middleware.prometheus.trace"):
            middleware = PrometheusMiddleware(app, app_name="test-app")

        # Check that the metric name is correct (no double _info suffix)
        assert middleware._app_info._name == "fastapi_app_info"
        # Verify it's NOT fastapi_app_info_info
        assert middleware._app_info._name != "fastapi_app_info_info"

    def test_all_required_metrics_present(self) -> None:
        """Test that all metrics required by the dashboard are initialized."""
        from prometheus_client import REGISTRY

        # Clear any existing collectors
        collectors_to_remove = []
        for collector in list(REGISTRY._names_to_collectors.values()):
            if hasattr(collector, "_name") and "fastapi" in getattr(
                collector, "_name", ""
            ):
                collectors_to_remove.append(collector)

        for collector in collectors_to_remove:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass

        PrometheusMiddleware._metrics_initialized = False

        app = FastAPI()

        with patch("app.middleware.prometheus.trace"):
            middleware = PrometheusMiddleware(app, app_name="test-app")

        # Verify all required metrics are present with correct base names
        # Note: prometheus_client Counter/Histogram store the base name internally,
        # but add _total/_bucket suffixes in output. Gauge keeps the name as-is.
        expected_metrics = {
            # Counters store base name without _total suffix
            "fastapi_requests": middleware._requests_total,
            "fastapi_responses": middleware._responses_total,
            "fastapi_exceptions": middleware._exceptions_total,
            # Histograms store base name (output gets _bucket, _count, _sum)
            "fastapi_requests_duration_seconds": middleware._requests_duration,
            # Gauges store exact name
            "fastapi_requests_in_progress": middleware._requests_in_progress,
            "fastapi_app_info": middleware._app_info,
        }

        for expected_name, metric in expected_metrics.items():
            assert metric._name == expected_name, (
                f"Metric name mismatch: expected {expected_name}, got {metric._name}"
            )

    def test_app_info_has_app_name_label(self) -> None:
        """Test that fastapi_app_info metric has app_name label for dashboard query."""
        from prometheus_client import REGISTRY

        # Clear any existing collectors
        collectors_to_remove = []
        for collector in list(REGISTRY._names_to_collectors.values()):
            if hasattr(collector, "_name") and "fastapi" in getattr(
                collector, "_name", ""
            ):
                collectors_to_remove.append(collector)

        for collector in collectors_to_remove:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass

        PrometheusMiddleware._metrics_initialized = False

        app = FastAPI()

        with patch("app.middleware.prometheus.trace"):
            middleware = PrometheusMiddleware(app, app_name="ml-emotion-api")

        # Verify the app_info gauge has app_name label
        assert "app_name" in middleware._app_info._labelnames

    def test_metrics_have_correct_labels(self) -> None:
        """Test that all metrics have the required labels for dashboard queries."""
        from prometheus_client import REGISTRY

        # Clear any existing collectors
        collectors_to_remove = []
        for collector in list(REGISTRY._names_to_collectors.values()):
            if hasattr(collector, "_name") and "fastapi" in getattr(
                collector, "_name", ""
            ):
                collectors_to_remove.append(collector)

        for collector in collectors_to_remove:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass

        PrometheusMiddleware._metrics_initialized = False

        app = FastAPI()

        with patch("app.middleware.prometheus.trace"):
            middleware = PrometheusMiddleware(app, app_name="test-app")

        # fastapi_requests_total should have method, path, app_name
        assert set(middleware._requests_total._labelnames) == {
            "method",
            "path",
            "app_name",
        }

        # fastapi_responses_total should have method, path, status_code, app_name
        assert set(middleware._responses_total._labelnames) == {
            "method",
            "path",
            "status_code",
            "app_name",
        }

        # fastapi_requests_duration_seconds should have method, path, app_name
        assert set(middleware._requests_duration._labelnames) == {
            "method",
            "path",
            "app_name",
        }

        # fastapi_requests_in_progress should have method, path, app_name
        assert set(middleware._requests_in_progress._labelnames) == {
            "method",
            "path",
            "app_name",
        }

        # fastapi_exceptions_total should have method, path, exception_type, app_name
        assert set(middleware._exceptions_total._labelnames) == {
            "method",
            "path",
            "exception_type",
            "app_name",
        }


class TestPrometheusMetricsOutput:
    """Test the actual metrics output format."""

    def setup_method(self) -> None:
        """Reset metrics state before each test."""
        PrometheusMiddleware._metrics_initialized = False

    def test_metrics_endpoint_output_contains_app_info(self) -> None:
        """Test that /metrics endpoint outputs fastapi_app_info (not _info_info)."""
        from prometheus_client import REGISTRY, generate_latest

        # Clear any existing collectors
        collectors_to_remove = []
        for collector in list(REGISTRY._names_to_collectors.values()):
            if hasattr(collector, "_name") and "fastapi" in getattr(
                collector, "_name", ""
            ):
                collectors_to_remove.append(collector)

        for collector in collectors_to_remove:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass

        PrometheusMiddleware._metrics_initialized = False

        app = FastAPI()

        @app.get("/test")
        async def test_endpoint() -> dict:
            return {"status": "ok"}

        with patch("app.middleware.prometheus.trace"):
            PrometheusMiddleware(app, app_name="test-app")

        # Generate metrics output
        metrics_output = generate_latest().decode("utf-8")

        # Check for correct metric name
        assert "fastapi_app_info{" in metrics_output
        # Ensure we don't have the double _info suffix
        assert "fastapi_app_info_info" not in metrics_output

    def test_metrics_endpoint_output_contains_all_metrics(self) -> None:
        """Test that /metrics endpoint outputs all required metrics."""
        from prometheus_client import REGISTRY, generate_latest

        # Clear any existing collectors
        collectors_to_remove = []
        for collector in list(REGISTRY._names_to_collectors.values()):
            if hasattr(collector, "_name") and "fastapi" in getattr(
                collector, "_name", ""
            ):
                collectors_to_remove.append(collector)

        for collector in collectors_to_remove:
            try:
                REGISTRY.unregister(collector)
            except Exception:
                pass

        PrometheusMiddleware._metrics_initialized = False

        app = FastAPI()

        with patch("app.middleware.prometheus.trace"):
            PrometheusMiddleware(app, app_name="test-app")

        # Generate metrics output
        metrics_output = generate_latest().decode("utf-8")

        # Required metrics for the dashboard
        required_metrics = [
            "fastapi_app_info",
            "fastapi_requests_total",
            "fastapi_responses_total",
            "fastapi_requests_duration_seconds",
            "fastapi_requests_in_progress",
            "fastapi_exceptions_total",
        ]

        for metric_name in required_metrics:
            # Check TYPE definition exists
            assert f"# TYPE {metric_name}" in metrics_output, (
                f"Missing TYPE for {metric_name}"
            )
