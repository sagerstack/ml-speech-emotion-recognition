"""
Unit tests for OpenTelemetry setup.

Tests the OpenTelemetry configuration including:
- Tracing setup with FastAPI
- Trace ID and span ID retrieval
- Tracer creation
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import FastAPI

from app.infrastructure.observability.tracing.opentelemetry_setup import (
    get_current_span_id,
    get_current_trace_id,
    get_tracer,
    setup_tracing,
)


class TestGetCurrentTraceId:
    """Test get_current_trace_id functionality."""

    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.trace")
    def test_get_current_trace_id_with_valid_span(self, mock_trace):
        """Test getting trace ID when there's a valid span."""
        mock_span_context = Mock()
        mock_span_context.is_valid = True
        mock_span_context.trace_id = 0x1234567890ABCDEF1234567890ABCDEF

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context

        mock_trace.get_current_span.return_value = mock_span

        result = get_current_trace_id()

        assert result == "1234567890abcdef1234567890abcdef"

    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.trace")
    def test_get_current_trace_id_with_invalid_span(self, mock_trace):
        """Test getting trace ID when span is invalid."""
        mock_span_context = Mock()
        mock_span_context.is_valid = False

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context

        mock_trace.get_current_span.return_value = mock_span

        result = get_current_trace_id()

        assert result is None

    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.trace")
    def test_get_current_trace_id_with_no_span(self, mock_trace):
        """Test getting trace ID when there's no span."""
        mock_trace.get_current_span.return_value = None

        result = get_current_trace_id()

        assert result is None


class TestGetCurrentSpanId:
    """Test get_current_span_id functionality."""

    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.trace")
    def test_get_current_span_id_with_valid_span(self, mock_trace):
        """Test getting span ID when there's a valid span."""
        mock_span_context = Mock()
        mock_span_context.is_valid = True
        mock_span_context.span_id = 0x1234567890ABCDEF

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context

        mock_trace.get_current_span.return_value = mock_span

        result = get_current_span_id()

        assert result == "1234567890abcdef"

    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.trace")
    def test_get_current_span_id_with_invalid_span(self, mock_trace):
        """Test getting span ID when span is invalid."""
        mock_span_context = Mock()
        mock_span_context.is_valid = False

        mock_span = Mock()
        mock_span.get_span_context.return_value = mock_span_context

        mock_trace.get_current_span.return_value = mock_span

        result = get_current_span_id()

        assert result is None

    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.trace")
    def test_get_current_span_id_with_no_span(self, mock_trace):
        """Test getting span ID when there's no span."""
        mock_trace.get_current_span.return_value = None

        result = get_current_span_id()

        assert result is None


class TestGetTracer:
    """Test get_tracer functionality."""

    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.trace")
    def test_get_tracer(self, mock_trace):
        """Test getting a tracer instance."""
        mock_tracer = Mock()
        mock_trace.get_tracer.return_value = mock_tracer

        result = get_tracer("test_module")

        assert result == mock_tracer
        mock_trace.get_tracer.assert_called_once_with("test_module")


class TestSetupTracing:
    """Test setup_tracing functionality."""

    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.HTTPXClientInstrumentor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.FastAPIInstrumentor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.LoggingInstrumentor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.trace")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.BatchSpanProcessor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.OTLPSpanExporter")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.TracerProvider")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.Resource")
    def test_setup_tracing_with_defaults(
        self,
        mock_resource_class,
        mock_tracer_provider_class,
        mock_exporter_class,
        mock_processor_class,
        mock_trace,
        mock_logging_instrumentor_class,
        mock_fastapi_instrumentor,
        mock_httpx_instrumentor_class,
    ):
        """Test setup_tracing with default parameters."""
        # Setup mocks
        mock_app = Mock(spec=FastAPI)
        mock_resource = Mock()
        mock_resource_class.create.return_value = mock_resource

        mock_tracer_provider = Mock()
        mock_tracer_provider_class.return_value = mock_tracer_provider

        mock_exporter = Mock()
        mock_exporter_class.return_value = mock_exporter

        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor

        mock_logging_instrumentor = Mock()
        mock_logging_instrumentor_class.return_value = mock_logging_instrumentor

        mock_httpx_instrumentor = Mock()
        mock_httpx_instrumentor_class.return_value = mock_httpx_instrumentor

        # Call setup_tracing
        setup_tracing(mock_app, "test-service")

        # Verify resource creation
        mock_resource_class.create.assert_called_once()

        # Verify tracer provider creation and configuration
        mock_tracer_provider_class.assert_called_once()
        mock_tracer_provider.add_span_processor.assert_called_once_with(mock_processor)

        # Verify tracer provider is set as global
        mock_trace.set_tracer_provider.assert_called_once_with(mock_tracer_provider)

        # Verify logging instrumentation is enabled by default
        mock_logging_instrumentor.instrument.assert_called_once_with(set_logging_format=True)

        # Verify FastAPI instrumentation
        mock_fastapi_instrumentor.instrument_app.assert_called_once()

        # Verify HTTPX instrumentation
        mock_httpx_instrumentor.instrument.assert_called_once()

    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.HTTPXClientInstrumentor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.FastAPIInstrumentor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.LoggingInstrumentor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.trace")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.BatchSpanProcessor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.OTLPSpanExporter")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.TracerProvider")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.Resource")
    def test_setup_tracing_with_logging_disabled(
        self,
        mock_resource_class,
        mock_tracer_provider_class,
        mock_exporter_class,
        mock_processor_class,
        mock_trace,
        mock_logging_instrumentor_class,
        mock_fastapi_instrumentor,
        mock_httpx_instrumentor_class,
    ):
        """Test setup_tracing with logging instrumentation disabled."""
        mock_app = Mock(spec=FastAPI)
        mock_resource_class.create.return_value = Mock()
        mock_tracer_provider_class.return_value = Mock()
        mock_exporter_class.return_value = Mock()
        mock_processor_class.return_value = Mock()

        mock_logging_instrumentor = Mock()
        mock_logging_instrumentor_class.return_value = mock_logging_instrumentor

        mock_httpx_instrumentor = Mock()
        mock_httpx_instrumentor_class.return_value = mock_httpx_instrumentor

        setup_tracing(
            mock_app,
            "test-service",
            enable_logging_instrumentation=False,
        )

        # Verify logging instrumentation is NOT called
        mock_logging_instrumentor.instrument.assert_not_called()

    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.HTTPXClientInstrumentor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.FastAPIInstrumentor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.LoggingInstrumentor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.trace")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.BatchSpanProcessor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.OTLPSpanExporter")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.TracerProvider")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.Resource")
    def test_setup_tracing_with_custom_endpoint(
        self,
        mock_resource_class,
        mock_tracer_provider_class,
        mock_exporter_class,
        mock_processor_class,
        mock_trace,
        mock_logging_instrumentor_class,
        mock_fastapi_instrumentor,
        mock_httpx_instrumentor_class,
    ):
        """Test setup_tracing with custom OTLP endpoint."""
        mock_app = Mock(spec=FastAPI)
        mock_resource_class.create.return_value = Mock()
        mock_tracer_provider_class.return_value = Mock()
        mock_processor_class.return_value = Mock()

        mock_logging_instrumentor = Mock()
        mock_logging_instrumentor_class.return_value = mock_logging_instrumentor

        mock_httpx_instrumentor = Mock()
        mock_httpx_instrumentor_class.return_value = mock_httpx_instrumentor

        setup_tracing(
            mock_app,
            "test-service",
            otlp_endpoint="custom-tempo:4317",
        )

        # Verify exporter was created with custom endpoint
        mock_exporter_class.assert_called_once_with(
            endpoint="custom-tempo:4317",
            insecure=True,
        )

    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.HTTPXClientInstrumentor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.FastAPIInstrumentor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.LoggingInstrumentor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.trace")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.BatchSpanProcessor")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.OTLPSpanExporter")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.TracerProvider")
    @patch("app.infrastructure.observability.tracing.opentelemetry_setup.Resource")
    def test_setup_tracing_with_custom_version(
        self,
        mock_resource_class,
        mock_tracer_provider_class,
        mock_exporter_class,
        mock_processor_class,
        mock_trace,
        mock_logging_instrumentor_class,
        mock_fastapi_instrumentor,
        mock_httpx_instrumentor_class,
    ):
        """Test setup_tracing with custom service version."""
        mock_app = Mock(spec=FastAPI)
        mock_resource = Mock()
        mock_resource_class.create.return_value = mock_resource
        mock_tracer_provider_class.return_value = Mock()
        mock_exporter_class.return_value = Mock()
        mock_processor_class.return_value = Mock()

        mock_logging_instrumentor = Mock()
        mock_logging_instrumentor_class.return_value = mock_logging_instrumentor

        mock_httpx_instrumentor = Mock()
        mock_httpx_instrumentor_class.return_value = mock_httpx_instrumentor

        setup_tracing(
            mock_app,
            "test-service",
            service_version="2.0.0",
        )

        # Verify resource was created with service attributes
        call_args = mock_resource_class.create.call_args
        attributes = call_args[1]["attributes"]
        assert attributes["service.version"] == "2.0.0"
