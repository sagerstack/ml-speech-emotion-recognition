# Multi-stage build for Python backend
FROM python:3.11-slim AS builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.3

# Set work directory
WORKDIR /app

# Copy poetry files
COPY backend/pyproject.toml backend/poetry.lock ./

# Configure Poetry
RUN poetry config virtualenvs.create false

# Install dependencies (without dev dependencies)
RUN poetry install --without dev --no-interaction --no-ansi

# Production stage
FROM python:3.11-slim AS production

# Set environment variables
# LIBROSA_CACHE_DIR/LEVEL: Redirect librosa cache to /tmp to prevent "cannot cache function" errors
# NUMBA_CACHE_DIR: Set writable cache directory for numba JIT compilation
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    LIBROSA_CACHE_DIR="/tmp/librosa_cache" \
    LIBROSA_CACHE_LEVEL="50" \
    NUMBA_CACHE_DIR="/tmp/numba_cache"

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Set work directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/app/ ./app/
COPY backend/.env.example .env

# Copy ML models
COPY backend/models/ ./models/

# Set correct permissions
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]