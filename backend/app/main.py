"""
FastAPI Application for ML Speech Emotion Recognition

This is the main entry point for the FastAPI backend service that provides
emotion prediction capabilities through AWS SageMaker integration.

Configuration: Local development first, then AWS deployment
"""

from typing import Any

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

from app.api.v1 import api_router
from app.utils.config import get_settings
from app.utils.logging import setup_logging

# Initialize settings and logging
settings = get_settings()
setup_logging()

# Define Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

PREDICTION_REQUESTS = Counter(
    'prediction_requests_total',
    'Total prediction requests',
    ['emotion', 'confidence_level']
)

AUDIO_PROCESSING_DURATION = Histogram(
    'audio_processing_duration_seconds',
    'Time spent processing audio files'
)

# Create FastAPI application
app = FastAPI(
    title="ML Speech Emotion Recognition API",
    description="Production-ready FastAPI backend for speech emotion recognition using SageMaker deployed models",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

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


@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Middleware to collect Prometheus metrics"""
    import time

    start_time = time.time()

    response = await call_next(request)

    # Record request duration
    duration = time.time() - start_time
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    # Record request count
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=str(response.status_code)
    ).inc()

    return response

# Include API router
app.include_router(api_router, prefix=settings.api_v1_str)


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
        "service": "ml-emotion-api",
        "version": "1.0.0",
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


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
