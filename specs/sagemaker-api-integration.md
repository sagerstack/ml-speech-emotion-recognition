# FastAPI-SageMaker Integration Technical Specification

## Table of Contents
1. [Overview](#overview)
2. [Current Architecture Analysis](#current-architecture-analysis)
3. [Integration Approaches](#integration-approaches)
4. [Authentication and Security](#authentication-and-security)
5. [Input/Output Format Specifications](#inputoutput-format-specifications)
6. [Performance Optimization](#performance-optimization)
7. [Error Handling and Resilience](#error-handling-and-resilience)
8. [Production Best Practices](#production-best-practices)
9. [Implementation Strategy](#implementation-strategy)
10. [Monitoring and Observability](#monitoring-and-observability)
11. [Deployment Considerations](#deployment-considerations)

## Overview

This document outlines the technical architecture and implementation patterns for integrating FastAPI backend services with AWS SageMaker for speech emotion recognition. The integration follows a production-ready approach with proper error handling, monitoring, and scalability considerations.

### Key Components
- **FastAPI Backend**: REST API service for handling audio uploads and emotion predictions
- **SageMaker Endpoint**: ML model serving platform for emotion recognition
- **Audio Processing Pipeline**: Audio validation, preprocessing, and feature extraction
- **Authentication & Security**: AWS IAM roles, API security, and data protection

## Current Architecture Analysis

### Existing FastAPI Structure

The current FastAPI application (`/backend/app/main.py`) provides:

```python
# Core FastAPI application with middleware
app = FastAPI(
    title="ML Speech Emotion Recognition API",
    description="Production-ready FastAPI backend for speech emotion recognition using SageMaker deployed models",
    version="1.0.0"
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

# Prometheus metrics integration
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests')
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
```

### Audio Processing Service

The audio service (`/backend/app/services/audio_service.py`) handles:

- **Supported Formats**: `.wav`, `.mp3`, `.flac`, `.m4a`, `.ogg`
- **Target Sample Rate**: 22050 Hz
- **Max Duration**: 60 seconds
- **Max File Size**: 25MB
- **Feature Extraction**: MFCC, chroma, spectral features, temporal features

### SageMaker Client Architecture

The SageMaker client (`/sagemaker/model-deployment/sagemaker_client.py`) provides:

```python
@dataclass
class SageMakerConfig:
    endpoint_name: str
    region: str = "us-east-1"
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 60.0
    content_type: str = "application/json"
    accept_type: str = "application/json"
```

## Integration Approaches

### 1. Direct Integration Pattern

**Description**: FastAPI directly calls SageMaker endpoint using boto3 client.

**Implementation**:

```python
from app.services.sagemaker_service import SageMakerService

class PredictionService:
    def __init__(self):
        self.sagemaker_client = SageMakerClient.from_env()

    async def predict_emotion(self, audio_features: AudioFeatures) -> EmotionResult:
        # Convert features to base64
        audio_base64 = self._features_to_base64(audio_features)

        # Call SageMaker
        result = await self.sagemaker_client.predict_emotion_from_base64(audio_base64)

        return result
```

**Pros**:
- Simple implementation
- Direct control over request/response handling
- Easy debugging and monitoring

**Cons**:
- Tight coupling to SageMaker
- Manual retry logic required
- Limited scalability options

### 2. Service Layer Pattern (Recommended)

**Description**: Abstract SageMaker operations through a dedicated service layer.

**Implementation**:

```python
# app/services/sagemaker_service.py
class SageMakerService:
    def __init__(self, config: SageMakerConfig):
        self.client = SageMakerClient(config)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30,
            expected_exception=SageMakerClientError
        )

    @circuit_breaker
    async def predict_emotion(self, audio_data: bytes) -> EmotionResult:
        try:
            # Convert audio to required format
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # Async prediction with timeout
            result = await asyncio.wait_for(
                self._async_predict(audio_base64),
                timeout=self.config.timeout
            )

            return self._validate_result(result)

        except asyncio.TimeoutError:
            raise PredictionTimeoutError("SageMaker prediction timed out")
        except Exception as e:
            logger.error(f"SageMaker prediction failed: {e}")
            raise SageMakerServiceError(f"Prediction failed: {str(e)}")

    async def _async_predict(self, audio_base64: str) -> EmotionResult:
        # Run synchronous SageMaker call in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.client.predict_emotion_from_base64,
            audio_base64
        )
```

**Pros**:
- Clean separation of concerns
- Easy to mock and test
- Supports circuit breaker pattern
- Async/await support
- Better error handling

**Cons**:
- Additional abstraction layer
- More complex implementation

### 3. Message Queue Pattern

**Description**: Use message queues (SQS/SNS) for asynchronous processing.

**Implementation**:

```python
class AsyncPredictionService:
    def __init__(self):
        self.sqs_client = boto3.client('sqs')
        self.s3_client = boto3.client('s3')
        self.results_cache = RedisCache()

    async def submit_prediction(self, audio_file: UploadFile) -> str:
        # Upload audio to S3
        s3_key = f"predictions/{uuid.uuid4()}/{audio_file.filename}"
        await self._upload_to_s3(audio_file, s3_key)

        # Send prediction request to SQS
        message = {
            "s3_key": s3_key,
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat()
        }

        response = await self.sqs_client.send_message(
            QueueUrl=settings.prediction_queue_url,
            MessageBody=json.dumps(message)
        )

        return response['MessageId']

    async def get_prediction_result(self, request_id: str) -> Optional[EmotionResult]:
        return await self.results_cache.get(f"prediction:{request_id}")
```

**Pros**:
- High scalability
- Decoupled architecture
- Better for batch processing
- Handles load spikes well

**Cons**:
- Increased complexity
- Latency for real-time predictions
- Additional infrastructure costs

## Authentication and Security

### AWS IAM Configuration

**SageMaker Execution Role**:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sagemaker:InvokeEndpoint"
            ],
            "Resource": "arn:aws:sagemaker:us-east-1:account-id:endpoint/emotion-recognition-endpoint"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:us-east-1:account-id:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "cloudwatch:PutMetricData"
            ],
            "Resource": "*"
        }
    ]
}
```

### API Security Patterns

**1. JWT Authentication**:

```python
from app.utils.auth import get_current_user

@router.post("/predict")
async def predict_emotion(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    # User is authenticated via JWT
    user_id = current_user.id

    # Rate limiting per user
    await rate_limiter.check_limit(user_id)

    # Process prediction
    result = await prediction_service.predict_emotion(file, user_id)
    return result
```

**2. API Key Authentication**:

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key not in valid_api_keys:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key
```

**3. Request Validation and Sanitization**:

```python
class PredictionRequest(BaseModel):
    audio_data: bytes
    sample_rate: int = 16000
    user_id: Optional[str] = None

    @validator('audio_data')
    def validate_audio_size(cls, v):
        if len(v) > 25 * 1024 * 1024:  # 25MB limit
            raise ValueError('Audio file too large')
        return v

    @validator('sample_rate')
    def validate_sample_rate(cls, v):
        if v not in [16000, 22050, 44100]:
            raise ValueError('Unsupported sample rate')
        return v
```

### Data Encryption

**In Transit**: TLS 1.2+ for all API communications
**At Rest**:
- S3 server-side encryption (SSE-S3 or SSE-KMS)
- SageMaker endpoint encryption
- Database encryption for stored results

## Input/Output Format Specifications

### Input Format

**Multipart Form Data**:

```http
POST /v1/predictions/predict
Content-Type: multipart/form-data

--boundary
Content-Disposition: form-data; name="file"; filename="audio.wav"
Content-Type: audio/wav

<binary audio data>
--boundary
Content-Disposition: form-data; name="user_id"

user123
--boundary--
```

**JSON Input with Base64 Audio**:

```json
{
    "audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA...",
    "sample_rate": 16000,
    "format": "wav",
    "user_id": "user123",
    "metadata": {
        "duration": 5.2,
        "channels": 1
    }
}
```

### Output Format

**Successful Response**:

```json
{
    "success": true,
    "message": "Emotion prediction completed",
    "data": {
        "predictions": [
            {
                "label": "happy",
                "confidence": 0.85
            },
            {
                "label": "neutral",
                "confidence": 0.10
            },
            {
                "label": "sad",
                "confidence": 0.05
            }
        ],
        "audio_metadata": {
            "duration": 5.2,
            "sample_rate": 16000,
            "channels": 1,
            "format": "wav"
        },
        "processing_info": {
            "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
            "model_version": "v1.0.0",
            "processed_at": "2024-01-01T12:00:00Z",
            "processing_time_ms": 1250
        }
    },
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Response**:

```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Audio file exceeds maximum duration of 30 seconds",
        "details": {
            "provided_duration": 45.2,
            "max_duration": 30.0,
            "correlation_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    },
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### SageMaker Endpoint Interface

**Input to SageMaker**:

```json
{
    "audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA...",
    "sample_rate": 16000
}
```

**Output from SageMaker**:

```json
{
    "predicted_emotion": "happy",
    "confidence": 0.85,
    "all_emotions": {
        "happy": 0.85,
        "neutral": 0.10,
        "sad": 0.05
    },
    "top_3_emotions": [
        {"emotion": "happy", "score": 0.85},
        {"emotion": "neutral", "score": 0.10},
        {"emotion": "sad", "score": 0.05}
    ],
    "model_info": {
        "model_type": "wav2vec2-lg-xlsr-speech-emotion",
        "num_labels": 6,
        "supported_emotions": ["happy", "sad", "angry", "neutral", "fear", "disgust"]
    }
}
```

## Performance Optimization

### 1. Connection Pooling

```python
# app/core/sagemaker_client.py
import aioboto3
from botocore.config import Config

class OptimizedSageMakerClient:
    def __init__(self):
        config = Config(
            region_name='us-east-1',
            max_pool_connections=50,
            retries={'max_attempts': 3, 'mode': 'adaptive'}
        )

        self.session = aioboto3.Session()
        self.client_config = config

    async def get_client(self):
        return self.session.client(
            'sagemaker-runtime',
            config=self.client_config
        )
```

### 2. Caching Strategy

```python
# app/services/cache_service.py
from app.core.redis_cache import RedisCache

class PredictionCache:
    def __init__(self):
        self.cache = RedisCache()
        self.cache_ttl = 3600  # 1 hour

    def _generate_cache_key(self, audio_hash: str) -> str:
        return f"prediction:{audio_hash}"

    async def get_cached_result(self, audio_data: bytes) -> Optional[EmotionResult]:
        audio_hash = hashlib.sha256(audio_data).hexdigest()
        cache_key = self._generate_cache_key(audio_hash)

        cached_data = await self.cache.get(cache_key)
        if cached_data:
            return EmotionResult.parse_obj(cached_data)

        return None

    async def cache_result(self, audio_data: bytes, result: EmotionResult):
        audio_hash = hashlib.sha256(audio_data).hexdigest()
        cache_key = self._generate_cache_key(audio_hash)

        await self.cache.set(
            cache_key,
            result.dict(),
            expire=self.cache_ttl
        )
```

### 3. Batch Processing

```python
class BatchPredictionService:
    async def predict_batch(self, audio_files: List[UploadFile]) -> List[EmotionResult]:
        # Process in chunks to avoid overwhelming SageMaker
        chunk_size = 5
        results = []

        for i in range(0, len(audio_files), chunk_size):
            chunk = audio_files[i:i + chunk_size]

            # Parallel processing within chunk
            tasks = [
                self.predict_single(audio_file)
                for audio_file in chunk
            ]

            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle exceptions
            for result in chunk_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch prediction failed: {result}")
                    results.append(self._create_error_result())
                else:
                    results.append(result)

            # Small delay between chunks
            await asyncio.sleep(0.1)

        return results
```

### 4. Resource Management

```python
# app/middleware/resource_limiter.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

@app.post("/v1/predictions/predict")
@limiter.limit("10/minute")  # 10 predictions per minute per IP
async def predict_emotion(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    # Implementation
    pass
```

## Error Handling and Resilience

### 1. Circuit Breaker Pattern

```python
# app/utils/circuit_breaker.py
import asyncio
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    async def __call__(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
```

### 2. Retry Logic

```python
# app/utils/retry.py
import asyncio
import random
from functools import wraps
from typing import Callable, Type, Tuple

def async_retry(
    max_attempts: int = 3,
    backoff_factor: float = 1.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts - 1:
                        break

                    # Calculate delay with exponential backoff and jitter
                    delay = min(
                        backoff_factor * (2 ** attempt) + random.uniform(0, 0.1),
                        max_delay
                    )

                    logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)

            raise last_exception

        return wrapper
    return decorator
```

### 3. Comprehensive Exception Hierarchy

```python
# app/exceptions/prediction_exceptions.py
class PredictionException(Exception):
    """Base exception for prediction errors"""
    pass

class AudioProcessingError(PredictionException):
    """Audio file processing errors"""
    pass

class SageMakerServiceError(PredictionException):
    """SageMaker service related errors"""
    pass

class PredictionTimeoutError(PredictionException):
    """Prediction timeout errors"""
    pass

class CircuitBreakerOpenError(PredictionException):
    """Circuit breaker is open"""
    pass

class RateLimitExceededError(PredictionException):
    """Rate limit exceeded"""
    pass

class ValidationError(PredictionException):
    """Input validation errors"""
    pass
```

### 4. Global Exception Handler

```python
# app/core/exception_handlers.py
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(PredictionException)
async def prediction_exception_handler(request: Request, exc: PredictionException):
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": exc.__class__.__name__,
                "message": str(exc),
                "correlation_id": correlation_id
            },
            "request_id": correlation_id
        }
    )

@app.exception_handler(RateLimitExceededError)
async def rate_limit_handler(request: Request, exc: RateLimitExceededError):
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please try again later.",
                "retry_after": 60
            }
        },
        headers={"Retry-After": "60"}
    )
```

## Production Best Practices

### 1. Health Checks

```python
# app/api/v1/endpoints/health.py
from app.services.sagemaker_service import SageMakerService
from app.core.database import DatabaseService

@router.get("/health")
async def health_check():
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "services": {}
    }

    # Check SageMaker endpoint
    try:
        sagemaker_health = await sagemaker_service.health_check()
        health_status["services"]["sagemaker"] = {
            "status": "healthy" if sagemaker_health["status"] == "healthy" else "unhealthy",
            "response_time": sagemaker_health.get("response_time"),
            "endpoint_name": sagemaker_health.get("endpoint_name")
        }
    except Exception as e:
        health_status["services"]["sagemaker"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"

    # Check database connectivity
    try:
        await database_service.ping()
        health_status["services"]["database"] = {"status": "healthy"}
    except Exception as e:
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"

    # Determine overall HTTP status
    status_code = 200
    if health_status["status"] == "degraded":
        status_code = 200  # Still serve traffic but indicate issues
    elif health_status["status"] == "unhealthy":
        status_code = 503

    return JSONResponse(content=health_status, status_code=status_code)
```

### 2. Graceful Shutdown

```python
# app/main.py
import signal
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting FastAPI application...")

    # Initialize services
    await initialize_services()

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application...")
    await cleanup_services()

app = FastAPI(
    title="ML Speech Emotion Recognition API",
    lifespan=lifespan
)

async def initialize_services():
    """Initialize all services on startup"""
    await sagemaker_service.initialize()
    await cache_service.connect()
    await database_service.connect()

async def cleanup_services():
    """Cleanup services on shutdown"""
    await sagemaker_service.cleanup()
    await cache_service.disconnect()
    await database_service.disconnect()
```

### 3. Configuration Management

```python
# app/core/config.py
from pydantic import BaseSettings
from typing import Optional

class ProductionSettings(BaseSettings):
    # SageMaker Configuration
    sagemaker_endpoint_name: str
    aws_region: str = "us-east-1"

    # Performance Settings
    max_concurrent_predictions: int = 100
    prediction_timeout_seconds: int = 30
    circuit_breaker_threshold: int = 5

    # Cache Settings
    redis_url: str
    cache_ttl_seconds: int = 3600

    # Monitoring
    prometheus_enabled: bool = True
    log_level: str = "INFO"

    # Security
    jwt_secret_key: str
    allowed_origins: list[str]

    class Config:
        env_file = ".env.production"

class DevelopmentSettings(BaseSettings):
    # Development defaults with mock SageMaker
    sagemaker_endpoint_name: str = "mock-endpoint"
    aws_region: str = "us-east-1"

    # Relaxed settings for development
    max_concurrent_predictions: int = 10
    prediction_timeout_seconds: int = 60

    # In-memory cache for development
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 300

    # Development security
    jwt_secret_key: str = "dev-secret-key"
    allowed_origins: list[str] = ["*"]

    class Config:
        env_file = ".env.development"

def get_settings() -> BaseSettings:
    """Get appropriate settings based on environment"""
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        return ProductionSettings()
    else:
        return DevelopmentSettings()
```

### 4. Request/Response Logging

```python
# app/middleware/logging_middleware.py
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        # Log request
        start_time = time.time()
        logger.info(
            "Request started",
            correlation_id=correlation_id,
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host
        )

        # Process request
        response = await call_next(request)

        # Log response
        duration = time.time() - start_time
        logger.info(
            "Request completed",
            correlation_id=correlation_id,
            status_code=response.status_code,
            duration_ms=duration * 1000
        )

        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id

        return response
```

## Implementation Strategy

### Phase 1: Core Integration (Week 1-2)

**Objectives**:
- Implement basic SageMaker client integration
- Replace mock predictions with real SageMaker calls
- Add error handling and retry logic

**Tasks**:

1. **Create SageMaker Service Module**:
   ```bash
   mkdir -p backend/app/services
   touch backend/app/services/sagemaker_service.py
   touch backend/app/services/prediction_service.py
   ```

2. **Implement Basic Integration**:
   ```python
   # backend/app/services/sagemaker_service.py
   class SageMakerService:
       def __init__(self):
           self.client = SageMakerClient.from_env()

       async def predict_emotion(self, audio_data: bytes) -> EmotionResult:
           # Basic implementation without advanced features
           pass
   ```

3. **Update Prediction Endpoint**:
   ```python
   # backend/app/api/v1/endpoints/predictions.py
   @router.post("/predict")
   async def predict_emotion(file: UploadFile = File(...)):
       # Use real SageMaker instead of mock
       result = await sagemaker_service.predict_emotion(file_content)
       return result
   ```

4. **Add Environment Configuration**:
   ```env
   # .env
   SAGEMAKER_ENDPOINT_NAME=your-endpoint-name
   AWS_REGION=us-east-1
   SAGEMAKER_TIMEOUT=30
   SAGEMAKER_MAX_RETRIES=3
   ```

### Phase 2: Performance Optimization (Week 3)

**Objectives**:
- Add connection pooling and caching
- Implement circuit breaker pattern
- Add batch processing capabilities

**Tasks**:

1. **Implement Connection Pooling**:
   ```python
   # backend/app/core/sagemaker_pool.py
   class SageMakerConnectionPool:
       def __init__(self, max_connections: int = 50):
           self.semaphore = asyncio.Semaphore(max_connections)
           self.clients = []
   ```

2. **Add Caching Layer**:
   ```python
   # backend/app/services/cache_service.py
   class PredictionCache:
       async def get_cached_prediction(self, audio_hash: str) -> Optional[EmotionResult]:
           pass

       async def cache_prediction(self, audio_hash: str, result: EmotionResult):
           pass
   ```

3. **Implement Circuit Breaker**:
   ```python
   # backend/app/utils/circuit_breaker.py
   class CircuitBreaker:
       # Implementation from previous section
       pass
   ```

### Phase 3: Advanced Features (Week 4)

**Objectives**:
- Add comprehensive monitoring and metrics
- Implement graceful shutdown
- Add batch prediction API

**Tasks**:

1. **Enhanced Monitoring**:
   ```python
   # backend/app/middleware/metrics_middleware.py
   class MetricsMiddleware:
       async def track_prediction_metrics(self, prediction_result: EmotionResult):
           # Track custom metrics
           PREDICTION_REQUESTS.labels(
               emotion=prediction_result.predicted_emotion,
               confidence_level=self._get_confidence_level(prediction_result.confidence)
           ).inc()
   ```

2. **Batch Prediction API**:
   ```python
   @router.post("/predict-batch")
   async def predict_emotions_batch(
       files: List[UploadFile] = File(...)
   ) -> Dict[str, Any]:
       results = await batch_service.predict_batch(files)
       return {"results": results}
   ```

3. **Graceful Shutdown**:
   ```python
   # backend/app/main.py
   @asynccontextmanager
   async def lifespan(app: FastAPI):
       # Startup and shutdown logic
       pass
   ```

### Phase 4: Production Deployment (Week 5-6)

**Objectives**:
- Containerize the application
- Set up CI/CD pipeline
- Deploy to production environment

**Tasks**:

1. **Docker Configuration**:
   ```dockerfile
   # Dockerfile
   FROM python:3.11-slim

   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt

   COPY . .

   EXPOSE 8000
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **Kubernetes Deployment**:
   ```yaml
   # k8s/deployment.yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: emotion-api
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: emotion-api
     template:
       metadata:
         labels:
           app: emotion-api
       spec:
         containers:
         - name: emotion-api
           image: emotion-api:latest
           ports:
           - containerPort: 8000
           env:
           - name: SAGEMAKER_ENDPOINT_NAME
             valueFrom:
               secretKeyRef:
                 name: api-secrets
                 key: sagemaker-endpoint
   ```

## Monitoring and Observability

### 1. Prometheus Metrics

```python
# app/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Custom metrics for SageMaker integration
SAGEMAKER_REQUESTS = Counter(
    'sagemaker_requests_total',
    'Total SageMaker requests',
    ['endpoint', 'status']
)

SAGEMAKER_RESPONSE_TIME = Histogram(
    'sagemaker_response_time_seconds',
    'SageMaker response time',
    ['endpoint']
)

ACTIVE_PREDICTIONS = Gauge(
    'active_predictions',
    'Number of active prediction requests'
)

PREDICTION_CACHE_HIT_RATE = Gauge(
    'prediction_cache_hit_rate',
    'Prediction cache hit rate'
)

# Emotion-specific metrics
EMOTION_PREDICTIONS = Counter(
    'emotion_predictions_total',
    'Total predictions per emotion',
    ['emotion', 'confidence_range']
)
```

### 2. Structured Logging

```python
# app/utils/logging.py
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
```

### 3. Distributed Tracing

```python
# app/middleware/tracing_middleware.py
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

class TracingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.tracer = trace.get_tracer(__name__)

    async def dispatch(self, request: Request, call_next):
        with self.tracer.start_as_current_span("http_request") as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))

            response = await call_next(request)

            span.set_attribute("http.status_code", response.status_code)

            return response
```

### 4. Health Check Dashboard

```python
# app/api/v1/endpoints/monitoring.py
@router.get("/metrics/detailed")
async def get_detailed_metrics():
    """Get detailed metrics for monitoring dashboard"""
    return {
        "sagemaker": {
            "endpoint_status": await sagemaker_service.get_endpoint_status(),
            "average_response_time": get_sagemaker_response_time(),
            "error_rate": get_sagemaker_error_rate(),
            "requests_per_minute": get_sagemaker_rpm()
        },
        "cache": {
            "hit_rate": cache_service.get_hit_rate(),
            "memory_usage": cache_service.get_memory_usage(),
            "total_cached_items": cache_service.get_total_items()
        },
        "predictions": {
            "total_today": get_total_predictions_today(),
            "emotion_distribution": get_emotion_distribution(),
            "average_confidence": get_average_confidence()
        }
    }
```

## Deployment Considerations

### 1. Environment Configuration

**Development Environment**:
- Mock SageMaker responses
- Local Redis cache
- File-based logging
- Relaxed rate limits

**Staging Environment**:
- Real SageMaker endpoint
- Redis cache cluster
- Structured JSON logging
- Production-like rate limits

**Production Environment**:
- Multiple SageMaker endpoints for load balancing
- Redis cluster with replication
- Centralized logging (ELK stack)
- Strict rate limiting
- Auto-scaling policies

### 2. Scaling Strategies

**Horizontal Scaling**:
```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: emotion-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: emotion-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**SageMaker Endpoint Scaling**:
- Configure endpoint auto-scaling based on CPU utilization and request count
- Use multiple variants for A/B testing
- Implement blue-green deployments for model updates

### 3. Security Best Practices

**Network Security**:
- VPC endpoints for SageMaker and S3
- Security groups restricting traffic
- AWS WAF for API protection
- DDoS protection

**Data Protection**:
- Encrypt audio data at rest and in transit
- Implement data retention policies
- Audit logging for all predictions
- GDPR compliance for user data

### 4. Disaster Recovery

**Backup Strategy**:
- Regular S3 backups of configuration and models
- Multi-region deployment for high availability
- Database replication and point-in-time recovery

**Failover Planning**:
- Automatic failover to backup SageMaker endpoints
- Graceful degradation when services are unavailable
- Health check-based traffic routing

---

## Conclusion

This technical specification provides a comprehensive framework for integrating FastAPI with SageMaker for speech emotion recognition. The recommended approach uses the Service Layer Pattern with proper error handling, performance optimization, and production-ready features.

Key implementation priorities:
1. **Start with basic integration** and gradually add advanced features
2. **Focus on reliability** with proper error handling and circuit breakers
3. **Implement comprehensive monitoring** from day one
4. **Plan for scalability** with connection pooling and caching
5. **Follow security best practices** throughout the implementation

The phased implementation approach ensures a systematic rollout with proper testing and validation at each stage.