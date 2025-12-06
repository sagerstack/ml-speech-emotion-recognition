"""
FastAPI Application for ML Speech Emotion Recognition

This is the main entry point for the FastAPI backend service that provides
emotion prediction capabilities through AWS SageMaker integration.

Observability stack includes:
- OpenTelemetry distributed tracing (export to Tempo)
- Prometheus metrics (compatible with FastAPI Observability Dashboard 16110)
- Structured logging with trace correlation (export to Loki)

Configuration: Local development first, then AWS deployment
"""

import os
from typing import Any

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_client import Counter, Histogram

from app.api.v1 import api_router
from app.api.v2 import api_v2_router
from app.infrastructure.observability.logging import (
    RequestLoggingMiddleware,
    get_logger,
    setup_logging,
)
from app.infrastructure.observability.metrics import (
    PrometheusMiddleware,
    metrics_endpoint,
)
from app.infrastructure.observability.tracing import setup_tracing
from app.utils.config import get_settings

# Initialize settings and logging
settings = get_settings()
setup_logging()

# Get logger for this module
logger = get_logger(__name__)

# Define custom ML-specific Prometheus metrics
# Note: Basic HTTP metrics are handled by custom PrometheusMiddleware
PREDICTION_REQUESTS = Counter(
    "ml_prediction_requests_total",
    "Total prediction requests",
    ["emotion", "confidence_level"],
)

AUDIO_PROCESSING_DURATION = Histogram(
    "ml_audio_processing_duration_seconds",
    "Time spent processing audio files",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, float("inf")),
)

# Application name for observability
APP_NAME = "ml-emotion-api"

# Create FastAPI application
app = FastAPI(
    title="ML Speech Emotion Recognition API",
    description="Production-ready FastAPI backend for speech emotion recognition using SageMaker deployed models",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Setup OpenTelemetry tracing (must be done before adding middleware)
# Only setup if OTLP endpoint is configured or in non-local environment
otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTLP_GRPC_ENDPOINT")
if otlp_endpoint or os.getenv("ENVIRONMENT", "development") != "development":
    setup_tracing(
        app=app,
        service_name=APP_NAME,
        service_version="1.0.0",
        otlp_endpoint=otlp_endpoint,
    )
    logger.info(
        "OpenTelemetry tracing enabled",
        otlp_endpoint=otlp_endpoint or "localhost:4317",
        service_name=APP_NAME,
    )
else:
    logger.info("OpenTelemetry tracing disabled (no OTLP endpoint configured)")

# Add GZIP compression middleware for large responses (audio_features data)
# Must be added before other middleware to compress all responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8501",
        "*",  # Allow all origins for testing
    ],  # React and Streamlit
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Add Prometheus metrics middleware (compatible with FastAPI Observability Dashboard)
app.add_middleware(PrometheusMiddleware, app_name=APP_NAME)

# Add request logging middleware
app.add_middleware(RequestLoggingMiddleware, app_name=APP_NAME)

# Include API routers
app.include_router(api_router, prefix=settings.api_v1_str)  # v1 API (legacy)
app.include_router(api_v2_router, prefix="/v2")  # v2 API (clean architecture)


@app.get("/metrics", include_in_schema=False)
async def prometheus_metrics(request: Request) -> Response:
    """Prometheus metrics endpoint."""
    return await metrics_endpoint(request)


@app.get("/")
@app.options("/")
async def root() -> dict[str, Any]:
    """Root endpoint for basic connectivity check"""
    return {
        "message": "ML Speech Emotion Recognition API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": APP_NAME,
        "version": "1.0.0",
    }


@app.on_event("startup")
async def startup_event() -> None:
    """Application startup event handler."""
    logger.info(
        "Application starting",
        service=APP_NAME,
        version="1.0.0",
        environment=os.getenv("ENVIRONMENT", "development"),
    )


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Application shutdown event handler."""
    logger.info("Application shutting down", service=APP_NAME)


def main() -> None:
    """Main function for running the application"""
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable auto-reload for development
        log_level="info",
    )


if __name__ == "__main__":
    main()
