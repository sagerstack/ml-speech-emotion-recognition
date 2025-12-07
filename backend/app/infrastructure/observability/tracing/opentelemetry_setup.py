"""
OpenTelemetry configuration for distributed tracing and observability.

This module sets up:
- TracerProvider with OTLP exporter to Tempo
- FastAPI automatic instrumentation
- HTTPX instrumentation for outgoing HTTP calls
- Logging instrumentation for trace context injection
"""

import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_tracing(
    app: FastAPI,
    service_name: str,
    service_version: str = "1.0.0",
    otlp_endpoint: str | None = None,
    enable_logging_instrumentation: bool = True,
) -> None:
    """
    Configure OpenTelemetry tracing for the FastAPI application.

    Args:
        app: The FastAPI application instance
        service_name: Name of the service (used in traces)
        service_version: Version of the service
        otlp_endpoint: OTLP gRPC endpoint (e.g., "tempo:4317")
                      If None, uses OTEL_EXPORTER_OTLP_ENDPOINT env var or defaults
        enable_logging_instrumentation: Whether to inject trace context into logs
    """
    # Get endpoint from environment or parameter
    endpoint = otlp_endpoint or os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        os.getenv("OTLP_GRPC_ENDPOINT", "localhost:4317"),
    )

    # Create resource with service metadata
    resource = Resource.create(
        attributes={
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
        }
    )

    # Create and configure TracerProvider
    tracer_provider = TracerProvider(resource=resource)

    # Add OTLP exporter (gRPC, insecure for local development)
    otlp_exporter = OTLPSpanExporter(
        endpoint=endpoint,
        insecure=True,  # Use insecure for local/k8s internal communication
    )

    # Use BatchSpanProcessor for efficient trace export
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Set as global tracer provider
    trace.set_tracer_provider(tracer_provider)

    # Instrument logging to inject trace context
    if enable_logging_instrumentation:
        LoggingInstrumentor().instrument(set_logging_format=True)

    # Instrument FastAPI for automatic span creation
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=tracer_provider,
        excluded_urls="health,metrics",  # Don't trace health/metrics endpoints
    )

    # Instrument HTTPX for outgoing HTTP calls
    HTTPXClientInstrumentor().instrument()


def get_current_trace_id() -> str | None:
    """
    Get the current trace ID from the active span.

    Returns:
        Trace ID as hex string, or None if no active span
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().trace_id, "032x")
    return None


def get_current_span_id() -> str | None:
    """
    Get the current span ID from the active span.

    Returns:
        Span ID as hex string, or None if no active span
    """
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        return format(span.get_span_context().span_id, "016x")
    return None


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer instance for creating custom spans.

    Args:
        name: Name for the tracer (usually module name)

    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)
