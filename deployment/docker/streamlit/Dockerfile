# Streamlit application Dockerfile - Optimized for minimal size
FROM python:3.11-slim

# Set environment variables
# NUMBA_CACHE_DIR=/tmp allows numba to cache compiled functions in a writable location
# (required because the container filesystem is read-only)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NUMBA_CACHE_DIR=/tmp/numba_cache

# Install only essential system dependencies
# - libsndfile1: Required by soundfile (librosa dependency) for audio file I/O
# - curl: Required for Docker health checks
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash streamlit

# Copy only Streamlit-specific requirements file
COPY frontend/streamlit_app/requirements.txt ./requirements.txt

# Install Python dependencies directly with pip (no Poetry overhead)
# Using Streamlit-specific requirements instead of root pyproject.toml
# This excludes heavyweight ML packages: tensorflow, keras, transformers, sagemaker, etc.
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY frontend/streamlit_app/ .

# Create .streamlit directory and copy config
RUN mkdir -p /app/.streamlit
COPY frontend/streamlit_app/.streamlit/config.toml /app/.streamlit/config.toml

# Set correct permissions
RUN chown -R streamlit:streamlit /app

# Switch to non-root user
USER streamlit

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Expose port
EXPOSE 8501

# Set environment variables for Streamlit
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Run the Streamlit application
CMD ["streamlit", "run", "src/ml-app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
