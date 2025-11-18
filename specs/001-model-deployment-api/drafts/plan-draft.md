# Plan Draft

## Architecture Overview

### System Components

#### Frontend
- UI Framework: Streamlit for ML interaction + React with TypeScript for monitoring dashboard
- State Management: React Context + useReducer for dashboard state
- Styling: Material-UI for React dashboard, Streamlit components for ML interface
- Audio Processing: Web Audio API + File API for client-side validation

#### Data Layer
- Local Storage: Streamlit session state + React localStorage
- State Persistence: WebSocket connection state maintained in Streamlit
- Caching Strategy: No caching for audio files (privacy-first), Redis for API rate limiting

#### Services
- API Mediator: Central FastAPI mediator handling all request/response flow
- Model Service: SageMaker SDK integration with retry logic and circuit breakers
- Audio Processing Service: Librosa-based preprocessing with format validation
- WebSocket Service: Real-time file transfer with 1-second chunking
- Monitoring Service: Prometheus metrics collection + structured logging

## Technology Stack

### Core Technologies
- Language: Python 3.11+ for backend, TypeScript 5.x for React frontend
- Build Tool: Poetry for Python deps, npm/webpack for React
- Package Manager: Poetry for Python, npm for frontend
- Testing: pytest for backend, Jest + Playwright for frontend

### Libraries

| Library | Version | Purpose | Justification |
|---------|---------|---------|---------------|
| fastapi | 0.104+ | REST API framework | Auto-documentation, Pydantic integration |
| uvicorn | 0.24+ | ASGI server | Performance, WebSocket support |
| websockets | 12.0+ | WebSocket support | Standard library compliance |
| librosa | 0.10+ | Audio processing | Industry standard for ML audio |
| boto3 | 1.34+ | AWS SDK | Official AWS integration |
| sagemaker | 2.200+ | SageMaker SDK | Model endpoint management |
| pydantic | 2.5+ | Data validation | Type safety, auto-validation |
| structlog | 23.2+ | Structured logging | JSON logs with correlation IDs |
| prometheus-client | 0.19+ | Metrics collection | Prometheus integration |
| streamlit | 1.28+ | ML interface | Rapid prototyping for ML apps |
| react | 18.2+ | Dashboard framework | Component-based architecture |
| typescript | 5.3+ | Type safety | Frontend type safety |
| mui | 5.14+ | UI components | Professional dashboard components |

### Development Tools
- Docker: Multi-stage builds for optimization
- Minikube: Local 2-pod setup for development
- kubectl: Kubernetes management
- helm: Package management for monitoring stack
- black/flake8/mypy: Code quality tools

## Data Models

### Prediction Request

```python
class PredictionRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    audio_format: str = Field(..., regex="^(wav|mp3|m4a)$")
    file_size_mb: float = Field(..., lt=30.0)
    duration_seconds: float = Field(..., lt=30.0)
    sample_rate: Optional[int] = Field(None, ge=16000, le=48000)
    channels: Optional[int] = Field(None, ge=1, le=2)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

### Prediction Response

```python
class PredictionResponse(BaseModel):
    request_id: str
    emotion: str = Field(..., regex="^(happy|sad|angry|fearful|disgusted|neutral)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    all_emotions: Dict[str, float]
    processing_time_ms: float
    model_version: str
    endpoint_name: str
    timestamp: datetime
```

### Health Check Response

```python
class HealthResponse(BaseModel):
    status: str = Field(..., regex="^(healthy|degraded|unhealthy)$")
    sage_maker_endpoint: EndpointStatus
    s3_connectivity: bool
    websockets_active: int
    uptime_seconds: float
    version: str
    dependencies: Dict[str, DependencyStatus]
```

## Database Schema

No persistent database required for V1. All state is managed in-memory with:
- Redis for rate limiting and caching (if needed)
- S3 for temporary audio file storage during processing
- CloudWatch Logs for structured log persistence

## Component Architecture

### Component Hierarchy

```
ml-emotion-api/
├── app/
│   ├── main.py              # FastAPI application entry
│   ├── mediator.py          # Central request/response mediator
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── prediction.py
│   │   │   │   ├── websocket.py
│   │   │   │   ├── health.py
│   │   │   │   └── metrics.py
│   │   │   └── dependencies.py
│   ├── services/
│   │   ├── model_service.py
│   │   ├── audio_service.py
│   │   ├── websocket_service.py
│   │   └── monitoring_service.py
│   ├── models/
│   │   ├── requests.py
│   │   ├── responses.py
│   │   └── internal.py
│   └── utils/
│       ├── config.py
│       ├── logging.py
│       └── metrics.py
├── frontend/
│   ├── streamlit_app/       # ML interface
│   └── react_dashboard/     # Monitoring dashboard
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── deployment/
    ├── docker/
    ├── k8s/
    └── monitoring/
```

### Key Components

#### API Mediator

```python
class APIMediator:
    """Central mediator for all API requests"""

    def __init__(
        self,
        model_service: ModelService,
        audio_service: AudioService,
        websocket_service: WebSocketService,
        monitoring_service: MonitoringService
    ):
        # Service injection

    async def process_prediction(
        self,
        request: PredictionRequest,
        audio_data: bytes
    ) -> PredictionResponse:
        # Orchestrate all services with correlation tracking
```

#### Model Service

```python
class ModelService:
    """SageMaker integration with retry logic"""

    async def predict(
        self,
        audio_array: np.ndarray,
        request_id: str
    ) -> ModelPrediction:
        # Handle SageMaker serverless endpoint calls
```

## Implementation Strategy

### Phase 1: Core API Infrastructure (Week 1)

1. **FastAPI Project Setup**
   - Poetry configuration with dependencies
   - Project structure following constitution
   - CI/CD pipeline setup
   - Docker multi-stage build

2. **API Mediator Implementation**
   - Central mediator pattern with Pydantic models
   - Structured logging with correlation IDs
   - Prometheus metrics endpoints
   - Error handling and retry logic

3. **Audio Processing Service**
   - Librosa integration with format validation
   - Memory-efficient processing with cleanup
   - Sample rate/channel preservation
   - Size and duration limits enforcement

**Acceptance**: All unit tests pass, Docker builds successfully, basic health endpoints work

### Phase 2: Model Integration (Week 2)

1. **SageMaker Integration**
   - Model deployment to serverless endpoint
   - AWS SDK integration with circuit breakers
   - Model prediction pipeline
   - Performance testing and optimization

2. **REST API Endpoints**
   - File upload prediction endpoint
   - URL-based prediction endpoint
   - Comprehensive error handling
   - Request/response validation

3. **WebSocket Implementation**
   - Audio file transfer with 1-second chunks
   - Connection management and state handling
   - Real-time progress reporting
   - Graceful disconnection handling

**Acceptance**: Model predictions work, WebSocket streaming functional, performance < 2s

### Phase 3: Frontend & Monitoring (Week 3)

1. **Streamlit ML Interface**
   - Audio file upload component
   - Real-time prediction display
   - Confidence visualization
   - Error handling and user guidance

2. **React Dashboard**
   - System health monitoring
   - Performance metrics display
   - WebSocket connection status
   - Alert management interface

3. **Observability Stack**
   - Grafana + Prometheus + Loki deployment
   - Custom metrics and dashboards
   - Log aggregation and searching
   - Alert configuration

**Acceptance**: Complete user journeys work, monitoring comprehensive, documentation complete

## State Management

### Global State

```python
class GlobalState:
    """Application-wide state management"""

    active_websockets: Dict[str, WebSocketConnection]
    prediction_cache: LRUCache  # Optional, for duplicate requests
    rate_limiters: Dict[str, RateLimiter]
    health_status: HealthStatus
    metrics_collector: PrometheusCollector
```

### Local Component State

- FastAPI dependency injection for request-scoped state
- Streamlit session state for user interactions
- React Context for dashboard state management

## Performance Optimization

### Strategies

1. **Audio Processing Optimization**
   - Numpy-based processing for performance
   - Memory-mapped file handling for large files
   - Automatic temporary file cleanup
   - Format validation before full processing

2. **SageMaker Optimization**
   - Connection pooling for SDK clients
   - Batching for multiple predictions (if applicable)
   - Circuit breaker pattern for fast failure
   - Retry with exponential backoff

3. **Caching Strategy**
   - No caching of audio data (privacy)
   - Response caching for duplicate requests (optional)
   - Model endpoint connection caching

### Performance Budgets

- API response time P95: < 2 seconds
- WebSocket latency: < 500ms per chunk
- Memory usage: < 1GB per container
- File processing: < 100MB RAM per request
- Cold start tolerance: 30 seconds for serverless

## Offline Support

### Service Worker Strategy

Not applicable for V1 - system requires live connectivity to SageMaker endpoints.

### Offline Capabilities

- ❌ Audio processing (requires server-side model)
- ❌ Model predictions (requires SageMaker)
- ✅ Dashboard viewing (cached data)
- ✅ Documentation access (static content)

## Security Considerations

### Data Protection

1. **Input Validation**
   - File type validation (magic bytes)
   - File size limits (30MB hard limit)
   - Audio duration validation (30 seconds)
   - Malicious file scanning

2. **Content Security Policy**
   ```
   default-src 'self'
   script-src 'self' 'unsafe-inline'
   style-src 'self' 'unsafe-inline'
   connect-src 'self' wss:
   media-src 'self' blob:
   ```

### AWS Security

- IAM least-privilege roles for SageMaker access
- VPC endpoints for private connectivity
- Encryption at rest (S3) and in transit (TLS 1.3)
- No storage of user audio data beyond processing

## Error Handling

### Error Categories

1. **Validation Errors (400)**
   - Invalid audio format
   - File size exceeded
   - Duration exceeded
   - Corrupted files

2. **Service Errors (500)**
   - SageMaker endpoint failures
   - Audio processing errors
   - Temporary storage issues
   - Network timeouts

3. **Rate Limiting (429)**
   - Concurrent request limits
   - API rate limits
   - WebSocket connection limits

### Error UI

- Streamlit: Error messages with suggested actions
- React Dashboard: Error notifications with troubleshooting steps
- API: Structured error responses with correlation IDs

## Testing Strategy

### Unit Tests
- **Target**: 90% coverage
- **Framework**: pytest with parametrized tests
- **Focus**: Business logic, validation, error handling

### Integration Tests
- **Framework**: pytest with TestClient
- **Focus**: API endpoints, WebSocket connections, SageMaker integration
- **Data**: Real audio files for validation

### E2E Tests
- **Framework**: Playwright
- **Focus**: Complete user journeys
- **Scenarios**: File upload, WebSocket streaming, monitoring dashboard

### Performance Tests
- **Framework**: Locust
- **Metrics**: Response times, concurrent users, memory usage
- **Targets**: P95 < 2s, 50 concurrent requests

## Accessibility Implementation

### WCAG 2.1 Level AA Requirements

1. **Keyboard Navigation**
   - All interactive elements keyboard accessible
   - Focus indicators visible
   - Tab order logical

2. **Screen Reader Support**
   - Semantic HTML elements
   - ARIA labels for dynamic content
   - Audio prediction results announced

3. **Visual Accessibility**
   - High contrast color schemes
   - Resizable text (200% zoom)
   - Color-blind friendly visualizations

## Browser Compatibility

### Target Browsers
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Polyfills Needed
- Web Audio API (for older browsers)
- WebSocket (if needed)
- Fetch API (if needed)

## Deployment Plan

### Build Process

```bash
# Backend
poetry install --no-dev
poetry run pytest --cov=app tests/
docker build -t ml-emotion-api:latest .

# Frontend - Streamlit
poetry export -f requirements.txt

# Frontend - React Dashboard
npm ci
npm run test
npm run build
```

### Continuous Integration

GitHub Actions with:
- Python code quality checks (black, flake8, mypy)
- Unit and integration test execution
- Security scanning (bandit, safety)
- Docker image building and scanning
- E2E test execution on deploy preview

### Release Checklist

- [ ] All automated tests pass
- [ ] Code coverage >= 90%
- [ ] Security scan shows no vulnerabilities
- [ ] Performance benchmarks meet requirements
- [ ] E2E tests validate complete user journeys
- [ ] Documentation is updated
- [ ] Load testing successful
- [ ] Rollback plan tested

## Monitoring & Analytics

### Performance Monitoring

**Key Metrics:**
- Request latency (P95, P99)
- Error rate by endpoint
- WebSocket connection success rate
- Memory and CPU usage
- SageMaker endpoint latency

**Dashboards:**
- System Overview (Grafana)
- API Performance (custom)
- Model Metrics (SageMaker + custom)
- Infrastructure Health (Prometheus)

### Error Tracking

**Implementation:**
- Structured logging with correlation IDs
- Error categorization and alerting
- Performance anomaly detection
- Automatic failure recovery

**Alert Configuration:**
- Error rate > 1% (critical)
- P95 latency > 2s (warning)
- WebSocket success rate < 99% (critical)
- Memory usage > 80% (warning)

## Migration Strategy

No migration required for V1 (greenfield development).

For future versions:
- Model version migration through blue/green deployment
- Database migrations (if persistence is added)
- API versioning strategy with backward compatibility

## Open Technical Questions

1. **Rate Limiting Strategy**
   - Option A: Redis-based distributed rate limiting
   - Option B: In-memory rate limiting per instance
   - Decision needed before production deployment

2. **Audio Caching Policy**
   - Option A: No caching (privacy-first)
   - Option B: Hash-based caching for duplicate requests
   - Decision needed for performance optimization

3. **WebSocket Connection Limits**
   - Option A: Fixed limit per instance
   - Option B: Dynamic scaling based on load
   - Decision needed for capacity planning

4. **Monitoring Data Retention**
   - Option A: 30 days for logs, 90 days for metrics
   - Option B: 7 days for logs, 30 days for metrics
   - Decision needed for cost optimization

5. **Blue/Green Deployment Automation**
   - Option A: SageMaker built-in traffic shifting
   - Option B: Custom deployment scripts with gradual traffic shift
   - Decision needed for model version management