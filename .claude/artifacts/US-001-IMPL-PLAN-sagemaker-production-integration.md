# Implementation Plan: SageMaker Production Integration

## Metadata

| Field | Value |
|-------|-------|
| ID | US-001-IMPL-PLAN |
| Title | SageMaker Production Integration |
| User Story ID | N/A (Direct requirement from stakeholder) |
| Tech Research ID | N/A |
| Created | 2025-12-08 |
| Status | Draft - Awaiting Stakeholder Approval |
| Status History | 2025-12-08: Draft - Initial plan creation |
| Last Updated | 2025-12-08 |
| Estimated Complexity | Medium (6/10) |
| Dependencies | - Working SageMaker endpoint (ml-ser-endpoint4)<br/>- Custom sklearn 1.7.2 container in ECR<br/>- Existing clean architecture backend |

## Quick Reference

**Tech Stack**:
- **Backend**: FastAPI, Python 3.11+, Clean Architecture
- **AWS Services**: SageMaker Runtime API, boto3 SDK
- **ML Framework**: scikit-learn 1.7.2, numpy 2.x
- **Infrastructure**: Docker, Kubernetes (local minikube)
- **Feature Extraction**: Librosa (remains in backend API)

**Architectural Pattern**:
- Clean Architecture with Repository Pattern
- Interface-driven design (Domain ↔ Infrastructure separation)
- Environment-based strategy pattern for model repository selection
- Adapter pattern for model interface abstraction

**Key Design Decisions**:
1. **Feature extraction stays in backend API** - Both local and production extract features using LibrosaAudioProcessor
2. **Only model inference goes to SageMaker** - Production sends 180 features to SageMaker endpoint for prediction
3. **Interface-driven integration** - No changes to use cases, only infrastructure layer modifications
4. **Environment-based switching** - Settings control whether to use FileSystemModelRepository (local) or SageMakerModelRepository (production)
5. **Backward compatibility** - Local development workflow remains completely unchanged

**Tech Research**: Existing backend architecture analyzed in previous conversation

---

## Requirements Coverage Validation

### Functional Requirements

| Requirement ID | Description | Parent Task | Status |
|----------------|-------------|-------------|--------|
| FR-1 | Environment-based model repository selection | [5.0][FR-1] (5 subtasks) | [ ] |
| FR-2 | SageMaker endpoint integration for production inference | [6.0][FR-2] (6 subtasks) | [ ] |
| FR-3 | Feature extraction remains in backend API | [7.0][FR-3] (4 subtasks) | [ ] |
| FR-4 | Backward compatibility with local development workflow | [8.0][FR-4] (5 subtasks) | [ ] |

### Technical Requirements

| Requirement ID | Description | Parent Task | Status |
|----------------|-------------|-------------|--------|
| TR-1 | Clean Architecture compliance (domain/infrastructure separation) | [9.0][TR-1] (4 subtasks) | [ ] |
| TR-2 | Interface-driven design (no changes to use cases) | [10.0][TR-2] (4 subtasks) | [ ] |
| TR-3 | AWS SDK integration with proper error handling | [11.0][TR-3] (6 subtasks) | [ ] |
| TR-4 | Configuration management via environment variables | [12.0][TR-4] (4 subtasks) | [ ] |
| TR-5 | Response time <3 seconds p95 for SageMaker inference | [13.0][TR-5] (5 subtasks) | [ ] |

### Acceptance Criteria

| Criteria ID | Description | Parent Task | Unit Tests | Integration Tests | E2E Test | Live Verification |
|-------------|-------------|-------------|------------|-------------------|----------|-------------------|
| AC-1 | Local development uses FileSystemModelRepository unchanged | [14.0][AC-1] (7 subtasks) | [14.4] | [14.5] | [14.6] | [14.7] |
| AC-2 | Production deployment uses SageMakerModelRepository | [15.0][AC-2] (7 subtasks) | [15.4] | [15.5] | [15.6] | [15.7] |
| AC-3 | Feature extraction runs in backend API (not SageMaker) | [16.0][AC-3] (7 subtasks) | [16.4] | [16.5] | [16.6] | [16.7] |
| AC-4 | Response format identical between local and production | [17.0][AC-4] (7 subtasks) | [17.4] | [17.5] | [17.6] | [17.7] |
| AC-5 | SageMaker integration handles network/timeout errors gracefully | [18.0][AC-5] (7 subtasks) | [18.4] | [18.5] | [18.6] | [18.7] |

**Coverage Summary**:
- ✅ Functional Requirements: 4/4 mapped (100%)
- ✅ Technical Requirements: 5/5 mapped (100%)
- ✅ Acceptance Criteria: 5/5 mapped with complete test coverage (100%)

---

## Task-Based Implementation Plan

### Execution Instructions

**Order of Execution**: Environment & Setup → Functional Requirements → Technical Requirements → Acceptance Criteria → Documentation

**Key Principles**:
- All tasks default to automated execution unless marked `[MANUAL]`
- Complete all subtasks within a parent task before moving to next parent
- Run tests immediately after implementation (unit → integration → E2E → live)
- Maintain backward compatibility with local development at all times

---

### 1. Environment & Setup

- [ ] **[1.0][SETUP] AWS SDK Dependencies**
  - [ ] [1.1] Add boto3>=1.34.0 to pyproject.toml dependencies
  - [ ] [1.2] Add botocore>=1.34.0 to pyproject.toml dependencies
  - [ ] [1.3] Run poetry install to update dependencies
  - [ ] [1.4] Verify boto3 imported successfully in Python environment

- [ ] **[2.0][SETUP] Exception Hierarchy for SageMaker**
  - [ ] [2.1] Create `backend/app/domain/model/exceptions.py` with base `ModelRepositoryError`
  - [ ] [2.2] Implement `SageMakerInferenceError` (base for all SageMaker errors)
  - [ ] [2.3] Implement `SageMakerEndpointNotFoundError` (404 endpoint not found)
  - [ ] [2.4] Implement `SageMakerTimeoutError` (network timeout)
  - [ ] [2.5] Implement `SageMakerThrottlingError` (429 rate limit)
  - [ ] [2.6] Implement `SageMakerInvalidResponseError` (malformed response)
  - [ ] [2.7] Implement `SageMakerAuthenticationError` (403 IAM permission denied)

- [ ] **[3.0][SETUP] Configuration Schema Updates**
  - [ ] [3.1] Update `backend/app/infrastructure/config/settings.py` to add `use_sagemaker: bool` field
  - [ ] [3.2] Add `sagemaker_timeout_seconds: int` field (default: 30)
  - [ ] [3.3] Add `sagemaker_max_retries: int` field (default: 3)
  - [ ] [3.4] Ensure existing `aws_region` and `sagemaker_endpoint_name` are properly typed
  - [ ] [3.5] Add validation: if `use_sagemaker=True`, require `sagemaker_endpoint_name` to be non-empty

- [ ] **[4.0][SETUP] Environment Variable Configuration**
  - [ ] [4.1] Update `.env.example` to add `USE_SAGEMAKER=false` (local default)
  - [ ] [4.2] Update `.env.example` to add `SAGEMAKER_TIMEOUT_SECONDS=30`
  - [ ] [4.3] Update `.env.example` to add `SAGEMAKER_MAX_RETRIES=3`
  - [ ] [4.4] Document environment variable usage in comments

---

### 2. Functional Requirements

- [ ] **[5.0][FR-1] Environment-Based Model Repository Selection**
  - [ ] [5.1] Create repository factory function in DI container: `_create_model_repository()`
  - [ ] [5.2] Implement conditional logic: if `settings.use_sagemaker == False`, return `FileSystemModelRepository()`
  - [ ] [5.3] Implement conditional logic: if `settings.use_sagemaker == True`, return `SageMakerModelRepository()`
  - [ ] [5.4] Write unit tests: verify factory returns correct repository type based on settings
  - [ ] [5.5] Live test: toggle `USE_SAGEMAKER` env var, verify correct repository instantiated

- [ ] **[6.0][FR-2] SageMaker Endpoint Integration for Production Inference**
  - [ ] [6.1] Create `backend/app/infrastructure/model/sagemaker_model_repository.py` implementing `ModelRepository` interface
  - [ ] [6.2] Implement `load_model(version: ModelVersion) -> EmotionModel` method that returns `SageMakerEmotionModelAdapter`
  - [ ] [6.3] Implement `get_model_info(version: ModelVersion)` to return metadata from SageMaker endpoint tags
  - [ ] [6.4] Implement `model_exists(version: ModelVersion)` by checking endpoint status (InService)
  - [ ] [6.5] Create `backend/app/infrastructure/model/sagemaker_emotion_model_adapter.py` implementing `EmotionModel` interface
  - [ ] [6.6] Implement `predict_emotion_probabilities(features: np.ndarray) -> dict[Emotion, float]` using boto3 SageMaker Runtime
  - [ ] [6.7] Write unit tests: mock boto3 client, verify request payload format
  - [ ] [6.8] Live test: deploy to test environment with `USE_SAGEMAKER=true`, verify endpoint called

- [ ] **[7.0][FR-3] Feature Extraction Remains in Backend API**
  - [ ] [7.1] Verify `RunInferenceUseCase` calls `audio_processor.extract_features()` BEFORE calling `model_repository.load_model()`
  - [ ] [7.2] Ensure `SageMakerEmotionModelAdapter.predict_emotion_probabilities()` receives pre-extracted features (180 floats)
  - [ ] [7.3] Document in code comments: "Feature extraction happens in backend API, only inference goes to SageMaker"
  - [ ] [7.4] Write integration test: verify features extracted locally, then sent to SageMaker adapter
  - [ ] [7.5] Live test: inspect CloudWatch logs, confirm SageMaker receives 180-feature array (not raw audio)

- [ ] **[8.0][FR-4] Backward Compatibility with Local Development Workflow**
  - [ ] [8.1] Verify `USE_SAGEMAKER=false` in `.env.local` (local development default)
  - [ ] [8.2] Verify local Docker Compose uses `USE_SAGEMAKER=false` environment variable
  - [ ] [8.3] Verify local minikube deployment uses `USE_SAGEMAKER=false` in ConfigMap
  - [ ] [8.4] Test: run backend locally with `poetry run uvicorn`, verify `FileSystemModelRepository` used
  - [ ] [8.5] Test: run Docker Compose locally, verify `FileSystemModelRepository` used
  - [ ] [8.6] Test: deploy to local minikube, verify `FileSystemModelRepository` used
  - [ ] [8.7] Live test: confirm no AWS credentials required for local development

---

### 3. Technical Requirements

- [ ] **[9.0][TR-1] Clean Architecture Compliance (Domain/Infrastructure Separation)**
  - [ ] [9.1] Verify `SageMakerModelRepository` lives in `backend/app/infrastructure/model/` (not domain)
  - [ ] [9.2] Verify `SageMakerEmotionModelAdapter` implements domain interface `EmotionModel`
  - [ ] [9.3] Verify no boto3 imports in domain layer (`backend/app/domain/`)
  - [ ] [9.4] Verify no SageMaker-specific logic in use cases (`backend/app/use_cases/`)
  - [ ] [9.5] Write architectural test: scan domain layer for infrastructure dependencies, assert none found

- [ ] **[10.0][TR-2] Interface-Driven Design (No Changes to Use Cases)**
  - [ ] [10.1] Verify `RunInferenceUseCase` unchanged (uses `ModelRepository` interface)
  - [ ] [10.2] Verify `EmotionModel` interface unchanged
  - [ ] [10.3] Verify `ModelRepository` interface unchanged
  - [ ] [10.4] Write integration test: run inference with both repositories, verify use case code identical
  - [ ] [10.5] Live test: deploy production, verify use case layer has zero SageMaker references

- [ ] **[11.0][TR-3] AWS SDK Integration with Proper Error Handling**
  - [ ] [11.1] Implement boto3 SageMaker Runtime client initialization in `SageMakerEmotionModelAdapter.__init__()`
  - [ ] [11.2] Configure client with region from settings: `boto3.client('sagemaker-runtime', region_name=settings.aws_region)`
  - [ ] [11.3] Implement retry logic with exponential backoff for transient errors (throttling, timeouts)
  - [ ] [11.4] Implement error mapping: `ClientError` → domain exceptions (`SageMakerEndpointNotFoundError`, `SageMakerAuthenticationError`, etc.)
  - [ ] [11.5] Implement timeout configuration: `invoke_endpoint()` with `InferenceTimeout=settings.sagemaker_timeout_seconds`
  - [ ] [11.6] Add logging: log request payload size, response time, errors
  - [ ] [11.7] Write unit tests: mock `ClientError` responses, verify correct exception raised
  - [ ] [11.8] Write integration test: simulate network timeout, verify `SageMakerTimeoutError` raised
  - [ ] [11.9] Live test: intentionally use wrong endpoint name, verify `SageMakerEndpointNotFoundError` raised

- [ ] **[12.0][TR-4] Configuration Management via Environment Variables**
  - [ ] [12.1] Verify `Settings` class loads from environment variables via pydantic
  - [ ] [12.2] Add default values: `use_sagemaker=False`, `sagemaker_timeout_seconds=30`, `sagemaker_max_retries=3`
  - [ ] [12.3] Implement validation: raise `ValueError` if `use_sagemaker=True` but `sagemaker_endpoint_name` is empty
  - [ ] [12.4] Write unit tests: test settings validation with various env var combinations
  - [ ] [12.5] Live test: deploy with missing `SAGEMAKER_ENDPOINT_NAME`, verify startup fails with clear error message

- [ ] **[13.0][TR-5] Response Time <3 Seconds p95 for SageMaker Inference**
  - [ ] [13.1] Implement performance instrumentation: measure time from `invoke_endpoint()` call to response
  - [ ] [13.2] Add metrics logging: log inference latency per request
  - [ ] [13.3] Configure SageMaker timeout: set `InferenceTimeout=30` seconds (hard limit)
  - [ ] [13.4] Create performance test: run 100 inference requests, measure p50/p95/p99 latency
  - [ ] [13.5] Write unit tests: verify performance instrumentation captures timing
  - [ ] [13.6] Live test: run 100 production requests, verify p95 <3 seconds

---

### 4. Acceptance Criteria

- [ ] **[14.0][AC-1] Local Development Uses FileSystemModelRepository Unchanged**
  - [ ] [14.1] Verify `.env.local` has `USE_SAGEMAKER=false`
  - [ ] [14.2] Verify DI container creates `FileSystemModelRepository` when `use_sagemaker=False`
  - [ ] [14.3] Verify local model loading from `backend/models/v5/model.pkl` still works
  - [ ] [14.4] Write unit tests: mock settings with `use_sagemaker=False`, verify `FileSystemModelRepository` instantiated
  - [ ] [14.5] Write integration tests: run full inference flow locally, verify no SageMaker calls
  - [ ] [14.6] **E2E Test**:
    ```bash
    # Build and deploy locally
    export USE_SAGEMAKER=false
    docker-compose build backend
    docker-compose up -d backend

    # Test inference endpoint
    response=$(curl -s -X POST http://localhost:8000/api/v1/inference \
      -H "Content-Type: multipart/form-data" \
      -F "audio=@test_audio.wav")
    status=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/v1/inference \
      -F "audio=@test_audio.wav")

    # Assertions
    test "$status" = "200" || exit 1
    echo "$response" | grep -q "emotion" || exit 1
    echo "$response" | grep -q "probabilities" || exit 1

    # Verify no AWS calls
    docker-compose logs backend | grep -i "sagemaker" && exit 1

    echo "✅ AC-1 E2E test passed"
    ```
  - [ ] [14.7] **Live Environment Verification**:
    - Deploy backend locally with `USE_SAGEMAKER=false`
    - Run inference with real audio file
    - Verify response contains emotion probabilities
    - Verify no AWS SDK calls in logs
    - Verify no AWS credentials required

- [ ] **[15.0][AC-2] Production Deployment Uses SageMakerModelRepository**
  - [ ] [15.1] Verify production `.env` has `USE_SAGEMAKER=true`
  - [ ] [15.2] Verify production `.env` has `SAGEMAKER_ENDPOINT_NAME=ml-ser-endpoint4`
  - [ ] [15.3] Verify DI container creates `SageMakerModelRepository` when `use_sagemaker=True`
  - [ ] [15.4] Write unit tests: mock settings with `use_sagemaker=True`, verify `SageMakerModelRepository` instantiated
  - [ ] [15.5] Write integration tests: mock boto3 client, verify `invoke_endpoint()` called with correct payload
  - [ ] [15.6] **E2E Test**:
    ```bash
    # Build and deploy with SageMaker enabled
    export USE_SAGEMAKER=true
    export SAGEMAKER_ENDPOINT_NAME=ml-ser-endpoint4
    export AWS_REGION=us-east-1
    docker-compose build backend
    docker-compose up -d backend

    # Test inference endpoint
    response=$(curl -s -X POST http://localhost:8000/api/v1/inference \
      -H "Content-Type: multipart/form-data" \
      -F "audio=@test_audio.wav")
    status=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/v1/inference \
      -F "audio=@test_audio.wav")

    # Assertions
    test "$status" = "200" || exit 1
    echo "$response" | grep -q "emotion" || exit 1
    echo "$response" | grep -q "probabilities" || exit 1

    # Verify SageMaker called
    docker-compose logs backend | grep -q "SageMaker" || exit 1

    echo "✅ AC-2 E2E test passed"
    ```
  - [ ] [15.7] **Live Environment Verification**:
    - Deploy backend to test environment with `USE_SAGEMAKER=true`
    - Configure AWS credentials (IAM role or environment variables)
    - Run inference with real audio file
    - Verify response contains emotion probabilities
    - Verify CloudWatch logs show SageMaker endpoint invocation
    - Verify endpoint `ml-ser-endpoint4` was called

- [ ] **[16.0][AC-3] Feature Extraction Runs in Backend API (Not SageMaker)**
  - [ ] [16.1] Verify `RunInferenceUseCase` calls `audio_processor.extract_features()` before model loading
  - [ ] [16.2] Verify `SageMakerEmotionModelAdapter.predict_emotion_probabilities()` receives numpy array (not audio bytes)
  - [ ] [16.3] Verify SageMaker endpoint receives JSON payload with `{"features": [180 floats]}`, not audio bytes
  - [ ] [16.4] Write unit tests: mock audio processor, verify features extracted before SageMaker call
  - [ ] [16.5] Write integration tests: trace full flow, assert feature extraction happens in backend
  - [ ] [16.6] **E2E Test**:
    ```bash
    # Build and deploy with SageMaker enabled
    export USE_SAGEMAKER=true
    export SAGEMAKER_ENDPOINT_NAME=ml-ser-endpoint4
    docker-compose up -d backend

    # Test inference and inspect logs
    curl -s -X POST http://localhost:8000/api/v1/inference \
      -F "audio=@test_audio.wav" > /dev/null

    # Assertions - verify feature extraction logged
    docker-compose logs backend | grep -q "Extracted.*features" || exit 1
    docker-compose logs backend | grep -q "shape.*180" || exit 1

    # Assertions - verify SageMaker receives features, not audio
    docker-compose logs backend | grep -q '{"features":' || exit 1

    echo "✅ AC-3 E2E test passed"
    ```
  - [ ] [16.7] **Live Environment Verification**:
    - Deploy to test environment with `USE_SAGEMAKER=true`
    - Run inference with real audio file
    - Check backend logs: verify "Extracted features" log message
    - Check CloudWatch logs for SageMaker endpoint: verify request body has `{"features": [...]}`
    - Verify request body does NOT contain raw audio bytes

- [ ] **[17.0][AC-4] Response Format Identical Between Local and Production**
  - [ ] [17.1] Verify both `SklearnEmotionModelAdapter` and `SageMakerEmotionModelAdapter` return `dict[Emotion, float]`
  - [ ] [17.2] Verify both adapters map class indices to `Emotion` enum values
  - [ ] [17.3] Verify both adapters return probabilities in same order and format
  - [ ] [17.4] Write unit tests: mock both adapters, verify output format identical
  - [ ] [17.5] Write integration tests: run inference with both repositories, assert response schemas match
  - [ ] [17.6] **E2E Test**:
    ```bash
    # Test local inference
    export USE_SAGEMAKER=false
    docker-compose up -d backend
    local_response=$(curl -s -X POST http://localhost:8000/api/v1/inference -F "audio=@test_audio.wav")
    docker-compose down

    # Test SageMaker inference
    export USE_SAGEMAKER=true
    docker-compose up -d backend
    sagemaker_response=$(curl -s -X POST http://localhost:8000/api/v1/inference -F "audio=@test_audio.wav")
    docker-compose down

    # Assertions - verify same fields exist
    echo "$local_response" | jq -e '.emotion' || exit 1
    echo "$local_response" | jq -e '.probabilities' || exit 1
    echo "$sagemaker_response" | jq -e '.emotion' || exit 1
    echo "$sagemaker_response" | jq -e '.probabilities' || exit 1

    # Assertions - verify same emotion keys
    local_keys=$(echo "$local_response" | jq -r '.probabilities | keys[]' | sort)
    sagemaker_keys=$(echo "$sagemaker_response" | jq -r '.probabilities | keys[]' | sort)
    test "$local_keys" = "$sagemaker_keys" || exit 1

    echo "✅ AC-4 E2E test passed"
    ```
  - [ ] [17.7] **Live Environment Verification**:
    - Deploy local environment with `USE_SAGEMAKER=false`
    - Run inference, save response as `local_response.json`
    - Deploy test environment with `USE_SAGEMAKER=true`
    - Run inference with same audio file, save response as `sagemaker_response.json`
    - Compare JSON schemas: verify identical structure
    - Compare emotion keys: verify identical set

- [ ] **[18.0][AC-5] SageMaker Integration Handles Network/Timeout Errors Gracefully**
  - [ ] [18.1] Implement timeout handling: if SageMaker call exceeds `sagemaker_timeout_seconds`, raise `SageMakerTimeoutError`
  - [ ] [18.2] Implement retry logic: retry up to `sagemaker_max_retries` times with exponential backoff
  - [ ] [18.3] Implement error mapping: map boto3 `ClientError` codes to domain exceptions
  - [ ] [18.4] Write unit tests: mock timeout scenarios, verify `SageMakerTimeoutError` raised
  - [ ] [18.5] Write integration tests: simulate endpoint unavailable, verify graceful error handling
  - [ ] [18.6] **E2E Test**:
    ```bash
    # Build and deploy with invalid endpoint
    export USE_SAGEMAKER=true
    export SAGEMAKER_ENDPOINT_NAME=invalid-endpoint-name
    docker-compose up -d backend

    # Test inference with invalid endpoint
    response=$(curl -s -X POST http://localhost:8000/api/v1/inference -F "audio=@test_audio.wav")
    status=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/v1/inference -F "audio=@test_audio.wav")

    # Assertions - verify graceful error
    test "$status" = "500" || exit 1
    echo "$response" | grep -q "error" || exit 1
    echo "$response" | grep -qi "endpoint.*not found" || exit 1

    # Verify error logged, not crash
    docker-compose logs backend | grep -q "SageMakerEndpointNotFoundError" || exit 1

    echo "✅ AC-5 E2E test passed"
    ```
  - [ ] [18.7] **Live Environment Verification**:
    - Deploy to test environment with `USE_SAGEMAKER=true`
    - Intentionally use wrong endpoint name
    - Run inference, verify returns HTTP 500 with error message (not crash)
    - Verify logs show `SageMakerEndpointNotFoundError` with clear message
    - Restore correct endpoint name, verify recovery

---

### 5. Documentation & Deployment

- [ ] **[19.0][DOC] Update Developer Documentation**
  - [ ] [19.1] Update `README.md` with SageMaker integration section
  - [ ] [19.2] Document environment variables: `USE_SAGEMAKER`, `SAGEMAKER_ENDPOINT_NAME`, `SAGEMAKER_TIMEOUT_SECONDS`, `SAGEMAKER_MAX_RETRIES`
  - [ ] [19.3] Add local development setup instructions (ensure `USE_SAGEMAKER=false`)
  - [ ] [19.4] Add production deployment instructions (set `USE_SAGEMAKER=true`, configure AWS credentials)
  - [ ] [19.5] Document SageMaker error handling and retry behavior
  - [ ] [19.6] Add troubleshooting section for common SageMaker errors

- [ ] **[20.0][DOC] Update Architecture Documentation**
  - [ ] [20.1] Update architecture diagrams to show SageMaker integration
  - [ ] [20.2] Document repository selection strategy (environment-based)
  - [ ] [20.3] Document data flow: Audio → Feature Extraction (Backend) → Model Inference (SageMaker/Local)
  - [ ] [20.4] Add sequence diagram for production inference flow

- [ ] **[21.0][DOC] Code Documentation**
  - [ ] [21.1] Add docstrings to `SageMakerModelRepository` class and methods
  - [ ] [21.2] Add docstrings to `SageMakerEmotionModelAdapter` class and methods
  - [ ] [21.3] Add inline comments explaining SageMaker request/response format
  - [ ] [21.4] Add comments explaining error handling and retry logic

- [ ] **[22.0][DOC] Testing Documentation**
  - [ ] [22.1] Document how to run unit tests for SageMaker integration
  - [ ] [22.2] Document how to run integration tests (requires AWS credentials)
  - [ ] [22.3] Document how to run E2E tests locally
  - [ ] [22.4] Document live environment testing procedures

- [ ] **[23.0][DOC] Deployment Configuration**
  - [ ] [23.1] Update Docker Compose `.env` template with SageMaker variables
  - [ ] [23.2] Update Kubernetes ConfigMap template for local minikube
  - [ ] [23.3] Update GitHub Actions workflow for production deployment
  - [ ] [23.4] Document AWS IAM permissions required for SageMaker Runtime API

- [ ] **[24.0][DOC] Code Quality & Version Control**
  - [ ] [24.1] Run code formatter: black backend/app/
  - [ ] [24.2] Run linter: flake8 backend/app/
  - [ ] [24.3] Run type checker: mypy backend/app/
  - [ ] [24.4] Fix all linting/typing issues
  - [ ] [24.5] Create commit with message: "feat: add SageMaker production integration with environment-based repository selection"
  - [ ] [24.6] Push to feature branch: feature/sagemaker-production-integration
  - [ ] [24.7] Create pull request with full DoD checklist

---

## Implementation Notes

### SageMaker Request/Response Format

**Request to SageMaker Endpoint**:
```json
{
  "features": [0.1, 0.2, ..., 0.9]  // 180 floats from LibrosaAudioProcessor
}
```

**Response from SageMaker Endpoint**:
```json
{
  "predictions": [2],  // Class index
  "probabilities": [[0.05, 0.10, 0.70, 0.05, 0.05, 0.05]],  // 6 emotion probabilities
  "classes": [0, 1, 2, 3, 4, 5]  // Class indices
}
```

**Adapter Mapping**:
- Extract `probabilities[0]` array (6 floats)
- Map indices to Emotion enum based on model's `classes_` attribute
- Return `dict[Emotion, float]`

### Repository Selection Logic

```python
# In backend/app/infrastructure/di/container.py

def _create_model_repository(self) -> ModelRepository:
    settings = self.get_settings()

    if settings.use_sagemaker:
        logger.info("Using SageMakerModelRepository (production mode)")
        return SageMakerModelRepository(
            endpoint_name=settings.sagemaker_endpoint_name,
            region=settings.aws_region,
            timeout_seconds=settings.sagemaker_timeout_seconds,
            max_retries=settings.sagemaker_max_retries
        )
    else:
        logger.info("Using FileSystemModelRepository (local mode)")
        return FileSystemModelRepository()
```

### Error Handling Strategy

1. **Transient Errors** (throttling, temporary network issues):
   - Retry up to `sagemaker_max_retries` times
   - Use exponential backoff: 1s, 2s, 4s

2. **Permanent Errors** (endpoint not found, authentication failure):
   - Do NOT retry
   - Raise domain exception immediately
   - Log error with full context

3. **Timeout Errors**:
   - Raise `SageMakerTimeoutError` after `sagemaker_timeout_seconds`
   - Do NOT retry (already waited long enough)

### Environment Configuration

**Local Development (`.env.local`)**:
```bash
USE_SAGEMAKER=false
# No AWS credentials required
```

**Production (`.env.production`)**:
```bash
USE_SAGEMAKER=true
SAGEMAKER_ENDPOINT_NAME=ml-ser-endpoint4
AWS_REGION=us-east-1
SAGEMAKER_TIMEOUT_SECONDS=30
SAGEMAKER_MAX_RETRIES=3
# AWS credentials via IAM role or AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY
```

### AWS IAM Permissions Required

The backend service (or IAM role) needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sagemaker:InvokeEndpoint"
      ],
      "Resource": "arn:aws:sagemaker:us-east-1:303440520181:endpoint/ml-ser-endpoint4"
    }
  ]
}
```

---

## Changelog

| Date | Author | Summary | Sections Affected | Reason |
|------|--------|---------|-------------------|--------|
| 2025-12-08 | Solution Architect (Claude) | Initial implementation plan creation | All sections | Stakeholder requirement for SageMaker production integration while maintaining local development workflow |

---

## Approval Required

**Stakeholder**: Please review this implementation plan and confirm:

1. ✅ Environment-based switching approach (local vs production)
2. ✅ Feature extraction stays in backend API (not moved to SageMaker)
3. ✅ Clean Architecture compliance (interface-driven design)
4. ✅ Local development workflow remains unchanged
5. ✅ Task breakdown and execution order

**Questions for Stakeholder**:

1. **AWS Credentials**: How should production backend authenticate with AWS?
   - Option A: IAM role attached to ECS/EKS service
   - Option B: Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
   - Option C: AWS credentials file mounted as volume

2. **Endpoint Selection**: Should we support multiple SageMaker endpoints (e.g., different model versions)?
   - Current plan: Single endpoint configured via `SAGEMAKER_ENDPOINT_NAME`
   - Alternative: Support endpoint selection per request (e.g., `?model_version=v5`)

3. **Fallback Strategy**: If SageMaker is unavailable, should production fall back to local model?
   - Current plan: Return error to client
   - Alternative: Automatic fallback to FileSystemModelRepository

4. **Performance Requirements**: Is <3 seconds p95 latency acceptable for production?
   - Current plan: 30-second timeout, 3 retries, p95 <3s target
   - Alternative: Adjust timeout/retries based on production SLA

**Once approved, implementation will proceed with python-developer subagent.**

---

*Implementation plan provides comprehensive task breakdown with complete test coverage, ensuring production SageMaker integration while preserving local development workflow.*
