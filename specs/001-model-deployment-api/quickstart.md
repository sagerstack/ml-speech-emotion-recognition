# Quick Start Guide

## Prerequisites

- Python 3.11+ installed
- Docker and Docker Compose
- Minikube for local development
- kubectl configured
- AWS CLI configured (for production deployment)
- Node.js 18+ and npm (for React dashboard)

## Local Development Setup

### 1. Clone and Setup

```bash
git clone <repository-url>
cd ml-speech-emotion-recognition
git checkout 001-model-deployment-api
```

### 2. Backend Setup

```bash
cd backend

# Install dependencies with Poetry
poetry install

# Copy environment template
cp .env.example .env

# Edit .env with your local settings
# - AWS credentials (optional for local development)
# - SageMaker endpoint name (will use mock locally)
# - Logging configuration
```

### 3. Frontend Setup

```bash
# Streamlit ML Interface
cd frontend/streamlit_app
pip install -r requirements.txt

# React Dashboard
cd ../react_dashboard
npm install
```

### 4. Start Local Development

```bash
# Start Minikube with required addons
minikube start --addons=ingress,metrics-server

# Apply local Kubernetes configurations
kubectl apply -f deployment/k8s/local/

# Build and start services with Docker Compose
docker-compose up -d

# Or run services individually:
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
cd frontend/streamlit_app && streamlit run app.py --server.port 8501
cd frontend/react_dashboard && npm start
```

### 5. Verify Installation

```bash
# Check API health
curl http://localhost:8000/v1/health

# Test with sample audio file
curl -X POST \
  -F "audio_file=@test_audio.wav" \
  http://localhost:8000/v1/predict-emotion
```

## API Usage Examples

### 1. File Upload Prediction

```python
import requests

# Upload audio file for emotion prediction
with open('audio.wav', 'rb') as f:
    files = {'audio_file': f}
    response = requests.post(
        'http://localhost:8000/v1/predict-emotion',
        files=files
    )

result = response.json()
print(f"Predicted emotion: {result['emotion']}")
print(f"Confidence: {result['confidence']}")
```

### 2. URL-based Prediction

```python
import requests

# Predict from audio URL
data = {
    "audio_url": "https://example.com/audio.wav",
    "timeout_seconds": 30
}

response = requests.post(
    'http://localhost:8000/v1/predict-emotion-url',
    json=data
)

result = response.json()
print(f"Prediction result: {result}")
```

### 3. WebSocket Streaming

```python
import asyncio
import websockets
import base64
import json

async def stream_audio_for_prediction(audio_file_path):
    uri = "ws://localhost:8000/v1/stream-emotion"

    async with websockets.connect(uri) as websocket:
        # Read and send audio file in chunks
        with open(audio_file_path, 'rb') as f:
            chunk_index = 0
            while True:
                chunk = f.read(16000)  # 1 second of audio at 16kHz
                if not chunk:
                    break

                message = {
                    "chunk_index": chunk_index,
                    "audio_data": base64.b64encode(chunk).decode(),
                    "is_final": False
                }

                await websocket.send(json.dumps(message))

                # Wait for acknowledgment
                ack = await websocket.recv()
                print(f"Chunk {chunk_index}: {ack}")

                chunk_index += 1

            # Send final chunk marker
            final_message = {
                "chunk_index": chunk_index,
                "audio_data": "",
                "is_final": True
            }
            await websocket.send(json.dumps(final_message))

            # Receive prediction result
            result = await websocket.recv()
            prediction = json.loads(result)
            print(f"Prediction: {prediction}")

# Run the streaming client
asyncio.run(stream_audio_for_prediction("audio.wav"))
```

## Streamlit Interface Usage

### 1. Start Streamlit App

```bash
cd frontend/streamlit_app
streamlit run app.py --server.port 8501
```

### 2. Use the Interface

1. **Upload Tab**: Drag and drop audio files or click to upload
2. **Record Tab**: Record audio directly from your microphone
3. **Results**: View emotion predictions with confidence scores
4. **History**: See previous predictions and their metadata

## React Dashboard Usage

### 1. Start Dashboard

```bash
cd frontend/react_dashboard
npm start
```

### 2. Monitor System

- **Health Status**: Real-time system and dependency health
- **Performance Metrics**: Response times, error rates, throughput
- **WebSocket Status**: Active connections and streaming statistics
- **Model Metrics**: SageMaker endpoint performance and costs

## Production Deployment

### 1. AWS Prerequisites

```bash
# Configure AWS CLI
aws configure

# Create EKS cluster (if not exists)
aws eks create-cluster \
  --name ml-emotion-cluster \
  --role-arn <arn:eks:service-role> \
  --resources-vpc-config subnetIds=<subnet-ids>

# Update kubeconfig
aws eks update-kubeconfig --name ml-emotion-cluster
```

### 2. Deploy Model to SageMaker

```python
import sagemaker
from sagemaker.huggingface import HuggingFaceModel

# Create SageMaker client
role = "arn:aws:iam::<account-id>:role/SageMakerExecutionRole"

# Deploy Hugging Face model
hub_model = HuggingFaceModel(
    model_id="firdhokk/speech-emotion-recognition-with-openai-whisper-large-v3",
    role=role,
    transformers_version="4.26.0",
    pytorch_version="1.13.1",
    py_version="py39",
    instance_type="ml.m5.large",
    serverless_inference_config={
        'MemorySizeInMB': 2048,
        'MaxConcurrency': 10
    }
)

# Deploy to serverless endpoint
predictor = hub_model.deploy(
    endpoint_name="speech-emotion-endpoint",
    serverless_inference_config=True
)
```

### 3. Deploy Application

```bash
# Build and push Docker images
docker build -t <your-registry>/ml-emotion-api:latest ./backend
docker push <your-registry>/ml-emotion-api:latest

# Deploy to EKS
kubectl apply -f deployment/k8s/production/

# Set up monitoring stack
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace

helm install grafana grafana/grafana \
  --namespace monitoring --create-namespace
```

### 4. Configure Monitoring

```bash
# Import Grafana dashboards
kubectl apply -f deployment/monitoring/grafana/dashboards/

# Set up Prometheus rules
kubectl apply -f deployment/monitoring/prometheus/rules/

# Configure alerting (optional)
kubectl apply -f deployment/monitoring/alertmanager/
```

## Configuration

### Environment Variables

**Backend (.env):**
```bash
# AWS Configuration
AWS_REGION=us-west-2
SAGEMAKER_ENDPOINT_NAME=speech-emotion-endpoint

# API Configuration
API_V1_STR=/v1
PROJECT_NAME=ML Speech Emotion Recognition
VERSION=1.0.0

# Logging
LOG_LEVEL=INFO
STRUCTURED_LOGGING=true

# Performance
MAX_UPLOAD_SIZE_MB=30
MAX_AUDIO_DURATION_SECONDS=30
MAX_CONCURRENT_REQUESTS=50

# Redis (optional for rate limiting)
REDIS_URL=redis://localhost:6379

# Monitoring
PROMETHEUS_ENABLED=true
METRICS_PORT=9090
```

**Streamlit (.streamlit/config.toml):**
```toml
[server]
port = 8501
headless = true
enableCORS = false

[browser]
gatherUsageStats = false

[logger]
level = "info"
```

**React (.env):**
```bash
REACT_APP_API_URL=http://localhost:8000/v1
REACT_APP_WS_URL=ws://localhost:8000/v1
REACT_APP_ENVIRONMENT=development
```

## Testing

### 1. Run Tests

```bash
# Backend tests
cd backend
poetry run pytest --cov=app tests/

# Frontend tests
cd frontend/react_dashboard
npm test

# E2E tests
cd backend
poetry run playwright test tests/e2e/
```

### 2. Load Testing

```bash
# Install Locust
pip install locust

# Run load test
locust -f tests/load/locustfile.py \
  --host=http://localhost:8000 \
  --users 50 \
  --spawn-rate 5 \
  --run-time 60s
```

### 3. Performance Validation

```bash
# Check response times meet requirements
curl -w "@curl-format.txt" -X POST \
  -F "audio_file=@test_audio.wav" \
  http://localhost:8000/v1/predict-emotion

# Expected: < 2000ms (P95 requirement)
```

## Troubleshooting

### Common Issues

1. **SageMaker Endpoint Timeout**
   - Check endpoint status: `aws sagemaker describe-endpoint`
   - Increase memory size in serverless config
   - Verify model loading time

2. **WebSocket Connection Issues**
   - Check firewall rules allow WebSocket connections
   - Verify CORS configuration in FastAPI
   - Check nginx configuration if using reverse proxy

3. **Audio Processing Errors**
   - Validate audio file format and integrity
   - Check librosa installation and dependencies
   - Verify file size and duration limits

4. **Memory Issues**
   - Monitor memory usage during processing
   - Implement proper file cleanup
   - Adjust container memory limits

### Monitoring Commands

```bash
# Check pod status
kubectl get pods -n ml-emotion

# View logs
kubectl logs -f deployment/ml-emotion-api -n ml-emotion

# Check resource usage
kubectl top pods -n ml-emotion

# Access Grafana dashboard
kubectl port-forward svc/grafana 3000:80 -n monitoring
```

## Next Steps

1. **Production Hardening**: Set up proper TLS, authentication, and rate limiting
2. **Model Monitoring**: Implement model drift detection and performance tracking
3. **Cost Optimization**: Configure auto-scaling and serverless cost controls
4. **Documentation**: Create comprehensive API documentation and user guides
5. **Testing**: Set up CI/CD pipeline with automated testing

## Support

- **API Documentation**: Available at `/docs` endpoint when running locally
- **Health Checks**: `/v1/health` for system status
- **Metrics**: `/v1/metrics` for performance data
- **Logs**: Structured JSON logs with correlation IDs for debugging