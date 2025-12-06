"""
Unit tests for OpenTelemetry observability module.

This module tests the OpenTelemetry configuration for distributed tracing,
including TracerProvider setup, instrumentation, and helper functions.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from app.utils.observability import (
    get_current_span_id,
    get_current_trace_id,
    get_tracer,
    setup_tracing,
)


@pytest.mark.unit
class TestSetupTracing:
    """Test cases for setup_tracing function."""

    def test_setup_tracing_basic(self) -> None:
        """Test basic tracing setup."""
        app = FastAPI()

        with patch("app.utils.observability.OTLPSpanExporter") as mock_exporter:
            with patch("app.utils.observability.TracerProvider") as mock_provider:
                with patch("app.utils.observability.BatchSpanProcessor"):
                    with patch("app.utils.observability.trace.set_tracer_provider"):
                        with patch(
                            "app.utils.observability.FastAPIInstrumentor"
                        ) as mock_instrumentor:
                            with patch("app.utils.observability.HTTPXClientInstrumentor"):
                                with patch("app.utils.observability.LoggingInstrumentor"):
                                    setup_tracing(
                                        app=app,
                                        service_name="test-service",
                                        service_version="1.0.0",
                                        otlp_endpoint="localhost:4317",
                                    )

                                    # Verify OTLP exporter was called with endpoint
                                    mock_exporter.assert_called_once()
                                    call_kwargs = mock_exporter.call_args[1]
                                    assert call_kwargs["endpoint"] == "localhost:4317"
                                    assert call_kwargs["insecure"] is True

    def test_setup_tracing_with_env_endpoint(self) -> None:
        """Test tracing setup using environment variable for endpoint."""
        app = FastAPI()

        with patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "env-endpoint:4317"}):
            with patch("app.utils.observability.OTLPSpanExporter") as mock_exporter:
                with patch("app.utils.observability.TracerProvider"):
                    with patch("app.utils.observability.BatchSpanProcessor"):
                        with patch("app.utils.observability.trace.set_tracer_provider"):
                            with patch("app.utils.observability.FastAPIInstrumentor"):
                                with patch("app.utils.observability.HTTPXClientInstrumentor"):
                                    with patch("app.utils.observability.LoggingInstrumentor"):
                                        setup_tracing(
                                            app=app,
                                            service_name="test-service",
                                        )

                                        # Should use env variable
                                        mock_exporter.assert_called_once()

    def test_setup_tracing_creates_resource(self) -> None:
        """Test that tracing setup creates proper resource with attributes."""
        app = FastAPI()

        with patch("app.utils.observability.Resource.create") as mock_resource:
            with patch("app.utils.observability.OTLPSpanExporter"):
                with patch("app.utils.observability.TracerProvider"):
                    with patch("app.utils.observability.BatchSpanProcessor"):
                        with patch("app.utils.observability.trace.set_tracer_provider"):
                            with patch("app.utils.observability.FastAPIInstrumentor"):
                                with patch("app.utils.observability.HTTPXClientInstrumentor"):
                                    with patch("app.utils.observability.LoggingInstrumentor"):
                                        setup_tracing(
                                            app=app,
                                            service_name="my-service",
                                            service_version="2.0.0",
                                        )

                                        # Verify resource was created with service info
                                        mock_resource.assert_called_once()
                                        call_kwargs = mock_resource.call_args[1]
                                        attrs = call_kwargs["attributes"]
                                        assert "service.name" in attrs or any(
                                            "my-service" in str(v) for v in attrs.values()
                                        )

    def test_setup_tracing_instruments_fastapi(self) -> None:
        """Test that FastAPI is instrumented."""
        app = FastAPI()

        with patch("app.utils.observability.OTLPSpanExporter"):
            with patch("app.utils.observability.TracerProvider"):
                with patch("app.utils.observability.BatchSpanProcessor"):
                    with patch("app.utils.observability.trace.set_tracer_provider"):
                        with patch(
                            "app.utils.observability.FastAPIInstrumentor"
                        ) as mock_instrumentor:
                            with patch("app.utils.observability.HTTPXClientInstrumentor"):
                                with patch("app.utils.observability.LoggingInstrumentor"):
                                    setup_tracing(
                                        app=app,
                                        service_name="test-service",
                                    )

                                    # Verify FastAPI was instrumented
                                    mock_instrumentor.instrument_app.assert_called_once()

    def test_setup_tracing_instruments_httpx(self) -> None:
        """Test that HTTPX client is instrumented."""
        app = FastAPI()

        with patch("app.utils.observability.OTLPSpanExporter"):
            with patch("app.utils.observability.TracerProvider"):
                with patch("app.utils.observability.BatchSpanProcessor"):
                    with patch("app.utils.observability.trace.set_tracer_provider"):
                        with patch("app.utils.observability.FastAPIInstrumentor"):
                            with patch(
                                "app.utils.observability.HTTPXClientInstrumentor"
                            ) as mock_httpx:
                                with patch("app.utils.observability.LoggingInstrumentor"):
                                    setup_tracing(
                                        app=app,
                                        service_name="test-service",
                                    )

                                    # Verify HTTPX was instrumented
                                    mock_httpx.return_value.instrument.assert_called_once()

    def test_setup_tracing_with_logging_instrumentation(self) -> None:
        """Test that logging instrumentation is enabled by default."""
        app = FastAPI()

        with patch("app.utils.observability.OTLPSpanExporter"):
            with patch("app.utils.observability.TracerProvider"):
                with patch("app.utils.observability.BatchSpanProcessor"):
                    with patch("app.utils.observability.trace.set_tracer_provider"):
                        with patch("app.utils.observability.FastAPIInstrumentor"):
                            with patch("app.utils.observability.HTTPXClientInstrumentor"):
                                with patch(
                                    "app.utils.observability.LoggingInstrumentor"
                                ) as mock_logging:
                                    setup_tracing(
                                        app=app,
                                        service_name="test-service",
                                        enable_logging_instrumentation=True,
                                    )

                                    # Verify logging was instrumented
                                    mock_logging.return_value.instrument.assert_called_once()

    def test_setup_tracing_without_logging_instrumentation(self) -> None:
        """Test that logging instrumentation can be disabled."""
        app = FastAPI()

        with patch("app.utils.observability.OTLPSpanExporter"):
            with patch("app.utils.observability.TracerProvider"):
                with patch("app.utils.observability.BatchSpanProcessor"):
                    with patch("app.utils.observability.trace.set_tracer_provider"):
                        with patch("app.utils.observability.FastAPIInstrumentor"):
                            with patch("app.utils.observability.HTTPXClientInstrumentor"):
                                with patch(
                                    "app.utils.observability.LoggingInstrumentor"
                                ) as mock_logging:
                                    setup_tracing(
                                        app=app,
                                        service_name="test-service",
                                        enable_logging_instrumentation=False,
                                    )

                                    # Verify logging was NOT instrumented
                                    mock_logging.return_value.instrument.assert_not_called()


@pytest.mark.unit
class TestGetCurrentTraceId:
    """Test cases for get_current_trace_id function."""

    def test_get_current_trace_id_with_valid_span(self) -> None:
        """Test getting trace ID from a valid active span."""
        mock_span = MagicMock()
        mock_span_context = MagicMock()
        mock_span_context.trace_id = 0x0102030405060708090A0B0C0D0E0F10
        mock_span_context.is_valid = True
        mock_span.get_span_context.return_value = mock_span_context

        with patch("app.utils.observability.trace.get_current_span", return_value=mock_span):
            trace_id = get_current_trace_id()

        assert trace_id is not None
        assert len(trace_id) == 32  # 128-bit trace ID as hex string

    def test_get_current_trace_id_without_span(self) -> None:
        """Test getting trace ID when no active span exists."""
        mock_span = MagicMock()
        mock_span_context = MagicMock()
        mock_span_context.is_valid = False
        mock_span.get_span_context.return_value = mock_span_context

        with patch("app.utils.observability.trace.get_current_span", return_value=mock_span):
            trace_id = get_current_trace_id()

        assert trace_id is None

    def test_get_current_trace_id_with_none_span(self) -> None:
        """Test getting trace ID when span is None."""
        with patch("app.utils.observability.trace.get_current_span", return_value=None):
            trace_id = get_current_trace_id()

        assert trace_id is None


@pytest.mark.unit
class TestGetCurrentSpanId:
    """Test cases for get_current_span_id function."""

    def test_get_current_span_id_with_valid_span(self) -> None:
        """Test getting span ID from a valid active span."""
        mock_span = MagicMock()
        mock_span_context = MagicMock()
        mock_span_context.span_id = 0x0102030405060708
        mock_span_context.is_valid = True
        mock_span.get_span_context.return_value = mock_span_context

        with patch("app.utils.observability.trace.get_current_span", return_value=mock_span):
            span_id = get_current_span_id()

        assert span_id is not None
        assert len(span_id) == 16  # 64-bit span ID as hex string

    def test_get_current_span_id_without_span(self) -> None:
        """Test getting span ID when no active span exists."""
        mock_span = MagicMock()
        mock_span_context = MagicMock()
        mock_span_context.is_valid = False
        mock_span.get_span_context.return_value = mock_span_context

        with patch("app.utils.observability.trace.get_current_span", return_value=mock_span):
            span_id = get_current_span_id()

        assert span_id is None

    def test_get_current_span_id_with_none_span(self) -> None:
        """Test getting span ID when span is None."""
        with patch("app.utils.observability.trace.get_current_span", return_value=None):
            span_id = get_current_span_id()

        assert span_id is None


@pytest.mark.unit
class TestGetTracer:
    """Test cases for get_tracer function."""

    def test_get_tracer_returns_tracer(self) -> None:
        """Test that get_tracer returns a tracer instance."""
        mock_tracer = MagicMock()

        with patch("app.utils.observability.trace.get_tracer", return_value=mock_tracer):
            tracer = get_tracer("test-module")

        assert tracer == mock_tracer

    def test_get_tracer_with_module_name(self) -> None:
        """Test that get_tracer passes the module name correctly."""
        with patch("app.utils.observability.trace.get_tracer") as mock_get_tracer:
            get_tracer("my.module.name")

            mock_get_tracer.assert_called_once_with("my.module.name")

    def test_get_tracer_can_be_used_for_spans(self) -> None:
        """Test that returned tracer can create spans."""
        mock_tracer = MagicMock()
        mock_span = MagicMock()
        mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
        mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=None)

        with patch("app.utils.observability.trace.get_tracer", return_value=mock_tracer):
            tracer = get_tracer("test-module")
            with tracer.start_as_current_span("test-span"):
                pass

            mock_tracer.start_as_current_span.assert_called_once_with("test-span")


@pytest.mark.unit
class TestObservabilityIntegration:
    """Integration tests for observability module."""

    def test_trace_context_flow(self) -> None:
        """Test the flow of trace context through the system."""
        # Create mock span with valid context
        mock_span = MagicMock()
        mock_span_context = MagicMock()
        mock_span_context.trace_id = 0x0102030405060708090A0B0C0D0E0F10
        mock_span_context.span_id = 0x0102030405060708
        mock_span_context.is_valid = True
        mock_span.get_span_context.return_value = mock_span_context

        with patch("app.utils.observability.trace.get_current_span", return_value=mock_span):
            trace_id = get_current_trace_id()
            span_id = get_current_span_id()

            assert trace_id is not None
            assert span_id is not None
            assert len(trace_id) == 32
            assert len(span_id) == 16

    def test_full_tracing_setup(self) -> None:
        """Test complete tracing setup with all components."""
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint() -> dict:
            return {"status": "ok"}

        # Mock all external dependencies
        with patch("app.utils.observability.OTLPSpanExporter"):
            with patch("app.utils.observability.TracerProvider"):
                with patch("app.utils.observability.BatchSpanProcessor"):
                    with patch("app.utils.observability.trace.set_tracer_provider"):
                        with patch("app.utils.observability.FastAPIInstrumentor"):
                            with patch("app.utils.observability.HTTPXClientInstrumentor"):
                                with patch("app.utils.observability.LoggingInstrumentor"):
                                    # Should not raise any exceptions
                                    setup_tracing(
                                        app=app,
                                        service_name="integration-test",
                                        service_version="1.0.0",
                                        otlp_endpoint="test:4317",
                                        enable_logging_instrumentation=True,
                                    )

    def test_environment_based_configuration(self) -> None:
        """Test that environment variables are properly used for configuration."""
        app = FastAPI()

        test_env = {
            "OTEL_EXPORTER_OTLP_ENDPOINT": "tempo:4317",
            "ENVIRONMENT": "production",
        }

        with patch.dict(os.environ, test_env, clear=False):
            with patch("app.utils.observability.OTLPSpanExporter") as mock_exporter:
                with patch("app.utils.observability.TracerProvider"):
                    with patch("app.utils.observability.BatchSpanProcessor"):
                        with patch("app.utils.observability.trace.set_tracer_provider"):
                            with patch("app.utils.observability.FastAPIInstrumentor"):
                                with patch("app.utils.observability.HTTPXClientInstrumentor"):
                                    with patch("app.utils.observability.LoggingInstrumentor"):
                                        setup_tracing(
                                            app=app,
                                            service_name="env-test-service",
                                        )

                                        # Verify exporter was configured
                                        mock_exporter.assert_called_once()
