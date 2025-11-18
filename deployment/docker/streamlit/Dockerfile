# Streamlit application Dockerfile
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install system dependencies for audio processing and Poetry
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    libsox-dev \
    libsox-fmt-all \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir poetry==1.8.3

# Set work directory
WORKDIR /app

# Create non-root user
RUN useradd --create-home --shell /bin/bash streamlit

# Copy project files
COPY frontend/streamlit_app/pyproject.toml frontend/streamlit_app/poetry.lock ./

# Copy environment files (if they exist)
COPY frontend/.env.example ./.env.example
COPY frontend/.env.local ./.env.local

# Install Python dependencies using Poetry
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

# Copy application code
COPY frontend/streamlit_app/ .

# Set correct permissions
RUN chown -R streamlit:streamlit /app /tmp/poetry_cache

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
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]