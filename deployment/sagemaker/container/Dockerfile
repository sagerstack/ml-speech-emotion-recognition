# Custom SageMaker Inference Container with sklearn 1.7.2
# Based on Python 3.10 slim image for smaller size

FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PATH="/opt/program:${PATH}"
ENV MODEL_DIR=/opt/ml/model

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nginx \
    ca-certificates \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Pin exact versions to match local environment
# Add retry logic and increased timeout for network reliability
RUN pip install --no-cache-dir \
    --timeout 300 \
    --retries 5 \
    numpy==2.1.0 \
    scikit-learn==1.7.2 \
    scipy>=1.11.0 \
    joblib>=1.3.0 \
    flask>=2.0.0 \
    gunicorn>=21.0.0 \
    gevent>=23.0.0

# Set up the program directory
COPY serve /opt/program/serve
COPY nginx.conf /opt/program/nginx.conf
COPY wsgi.py /opt/program/wsgi.py

RUN chmod +x /opt/program/serve

WORKDIR /opt/program

# SageMaker will mount model at /opt/ml/model
# and code at /opt/ml/model/code

EXPOSE 8080

ENTRYPOINT ["serve"]
