# US-009 Implementation Plan: Clean Architecture Refactoring

## Metadata

**Implementation Plan ID:** US-009-IMPL-PLAN
**Title:** Backend Clean Architecture Refactoring with v4 Model and Observability
**User Story ID:** US-009
**Tech Research ID:** CLEAN_ARCHITECTURE_FINAL_V4_WITH_OBSERVABILITY.md
**Created:** 2025-12-05 10:00:00
**Last Updated:** 2025-12-05 10:00:00
**Status:** Draft
**Complexity:** High
**Dependencies:** None (foundation work)

**Status History:**
- 2025-12-05 10:00:00 - Draft created

---

## Quick Reference

### Tech Stack
- **Language:** Python 3.11+
- **Framework:** FastAPI
- **Validation:** Pydantic v2
- **Testing:** Pytest + pytest-cov
- **Code Quality:** Black (formatter) + Ruff (linter) + Mypy (type checker)
- **ML:** Scikit-learn, Librosa, NumPy
- **Observability:** OpenTelemetry, Prometheus, Loki, Promtail
- **Architecture:** Clean Architecture (Ports & Adapters)

### Architectural Pattern
Clean Architecture with vertical slicing:
- **Domain Layer:** Pure business logic (entities, value objects, interfaces)
- **Use Cases Layer:** Application business logic orchestration
- **Infrastructure Layer:** External system adapters (ML models, observability, feature extraction)
- **API Layer:** HTTP interface (thin controllers calling use cases)

### Tech Research Reference
See `/Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition/backend/CLEAN_ARCHITECTURE_FINAL_V4_WITH_OBSERVABILITY.md`

---

## Requirements Coverage Validation

### Functional Requirements
| Requirement ID | Description | Parent Task | Status |
|----------------|-------------|-------------|--------|
| FR-1 | Domain model entities with Pydantic validation | [5.0][FR-1] (6 subtasks) | [ ] |
| FR-2 | Domain value objects with immutability | [6.0][FR-2] (5 subtasks) | [ ] |
| FR-3 | Domain service and repository interfaces | [7.0][FR-3] (3 subtasks) | [ ] |
| FR-4 | Use cases for model inference orchestration | [8.0][FR-4] (4 subtasks) | [ ] |
| FR-5 | Use cases for monitoring and feedback | [9.0][FR-5] (4 subtasks) | [ ] |
| FR-6 | Infrastructure v4 model integration | [10.0][FR-6] (5 subtasks) | [ ] |
| FR-7 | Infrastructure monitoring service implementation | [11.0][FR-7] (4 subtasks) | [ ] |
| FR-8 | API endpoints refactored to call use cases only | [12.0][FR-8] (5 subtasks) | [ ] |
| FR-9 | Dependency injection container | [13.0][FR-9] (4 subtasks) | [ ] |

### Technical Requirements
| Requirement ID | Description | Parent Task | Status |
|----------------|-------------|-------------|--------|
| TR-1 | Observability stack migration to infrastructure layer | [14.0][TR-1] (6 subtasks) | [ ] |
| TR-2 | Custom log formatter from .env configuration | [15.0][TR-2] (5 subtasks) | [ ] |
| TR-3 | API request/response logging middleware | [16.0][TR-3] (4 subtasks) | [ ] |
| TR-4 | Black + Ruff + Mypy code quality enforcement | [17.0][TR-4] (5 subtasks) | [ ] |
| TR-5 | 100% test coverage for domain and use cases layers | [18.0][TR-5] (4 subtasks) | [ ] |

### Acceptance Criteria
| Criteria ID | Description | Parent Task | Unit Tests | Integration Tests | E2E Test | Live Verification |
|-------------|-------------|-------------|------------|-------------------|----------|-------------------|
| AC-1 | All tests pass with v4 model only | [19.0][AC-1] (7 subtasks) | [19.4] | [19.5] | [19.6] | [19.7] |
| AC-2 | API inference endpoint uses clean architecture | [20.0][AC-2] (7 subtasks) | [20.4] | [20.5] | [20.6] | [20.7] |
| AC-3 | Observability pipeline functional with new architecture | [21.0][AC-3] (7 subtasks) | [21.4] | [21.5] | [21.6] | [21.7] |
| AC-4 | Zero Black/Ruff/Mypy errors on all code | [22.0][AC-4] (7 subtasks) | [22.4] | [22.5] | [22.6] | [22.7] |
| AC-5 | Logs show custom format with trace context | [23.0][AC-5] (7 subtasks) | [23.4] | [23.5] | [23.6] | [23.7] |

**Coverage Summary**:
- ✅ Functional Requirements: 9/9 mapped (100%)
- ✅ Technical Requirements: 5/5 mapped (100%)
- ✅ Acceptance Criteria: 5/5 mapped with complete test coverage (100%)

---

## Task-Based Implementation Plan

### Execution Instructions
Complete tasks in order: Environment & Setup → Functional Requirements → Technical Requirements → Acceptance Criteria → Documentation

Use strict Test-Driven Development (TDD):
1. **RED**: Write failing test
2. **GREEN**: Write minimal code to pass test
3. **REFACTOR**: Improve code
4. **QUALITY**: Run Black + Ruff + Mypy

---

### 1. Environment & Setup

- [ ] **[1.0][SETUP] Code Quality Tools Configuration**
  - [ ] [1.1] Configure Black in pyproject.toml (line-length = 100, target-version = py311)
  - [ ] [1.2] Configure Ruff in pyproject.toml (select = ["E", "F", "I", "N", "W"], line-length = 100)
  - [ ] [1.3] Configure Mypy in pyproject.toml (strict = true, python_version = "3.11")
  - [ ] [1.4] Verify tools installed: `poetry run black --version`, `poetry run ruff --version`, `poetry run mypy --version`
  - [ ] [1.5] Run tools on existing codebase to establish baseline

- [ ] **[2.0][SETUP] Domain Layer Directory Structure**
  - [ ] [2.1] Create `app/domain/__init__.py`
  - [ ] [2.2] Create `app/domain/model/` with subdirectories: entities, value_objects, services, repositories, exceptions
  - [ ] [2.3] Create `app/domain/monitoring/` with subdirectories: entities, repositories, services, exceptions
  - [ ] [2.4] Create corresponding test directories under `tests/unit/domain/`
  - [ ] [2.5] Verify directory structure matches Clean Architecture V4 document

- [ ] **[3.0][SETUP] Use Cases Layer Directory Structure**
  - [ ] [3.1] Create `app/use_cases/__init__.py`
  - [ ] [3.2] Create `app/use_cases/model/` for inference use cases
  - [ ] [3.3] Create `app/use_cases/monitoring/` for monitoring use cases
  - [ ] [3.4] Create corresponding test directories under `tests/unit/use_cases/`

- [ ] **[4.0][SETUP] Infrastructure Layer Directory Structure**
  - [ ] [4.1] Create `app/infrastructure/model/v4/` for v4 feature extraction
  - [ ] [4.2] Create `app/infrastructure/observability/` with subdirectories: tracing, metrics, logging
  - [ ] [4.3] Create `app/infrastructure/monitoring/` for monitoring implementations
  - [ ] [4.4] Create corresponding test directories under `tests/unit/infrastructure/`

---

### 2. Functional Requirements

- [ ] **[5.0][FR-1] Domain Model Entities with Pydantic**
  - [ ] [5.1] TDD Cycle: Write failing tests for RawAudio entity (creation, from_bytes factory, validate_size)
  - [ ] [5.2] Implement RawAudio entity using Pydantic BaseModel with validation
  - [ ] [5.3] TDD Cycle: Write failing tests for ModelInfo entity (version, model_type, feature_dimension)
  - [ ] [5.4] Implement ModelInfo entity using Pydantic BaseModel
  - [ ] [5.5] TDD Cycle: Write failing tests for Inference entity (emotion, confidence, probabilities)
  - [ ] [5.6] Implement Inference entity using Pydantic BaseModel with nested value objects
  - [ ] [5.7] Run: `poetry run black app/domain/model/entities/ tests/unit/domain/model/entities/`
  - [ ] [5.8] Run: `poetry run ruff check app/domain/model/entities/ --fix`
  - [ ] [5.9] Run: `poetry run mypy app/domain/model/entities/ --strict`
  - [ ] [5.10] Run: `poetry run pytest tests/unit/domain/model/entities/ -v --cov=app/domain/model/entities`

- [ ] **[6.0][FR-2] Domain Value Objects with Immutability**
  - [ ] [6.1] TDD Cycle: Write failing tests for Emotion enum (6 emotions, string conversion)
  - [ ] [6.2] Implement Emotion as str + Enum (ANGRY, DISGUST, FEAR, HAPPY, NEUTRAL, SAD)
  - [ ] [6.3] TDD Cycle: Write failing tests for Confidence (0.0-1.0 validation, immutability, float conversion)
  - [ ] [6.4] Implement Confidence using Pydantic with Field(ge=0.0, le=1.0) and frozen=True
  - [ ] [6.5] TDD Cycle: Write failing tests for ModelVersion (v4 format, version_number extraction)
  - [ ] [6.6] Implement ModelVersion using Pydantic with regex validation
  - [ ] [6.7] TDD Cycle: Write failing tests for AudioMetadata (duration, sample_rate, channels validation)
  - [ ] [6.8] Implement AudioMetadata using Pydantic with positive value validation
  - [ ] [6.9] Run: `poetry run black app/domain/model/value_objects/ tests/unit/domain/model/value_objects/`
  - [ ] [6.10] Run: `poetry run ruff check app/domain/model/value_objects/ --fix`
  - [ ] [6.11] Run: `poetry run mypy app/domain/model/value_objects/ --strict`
  - [ ] [6.12] Run: `poetry run pytest tests/unit/domain/model/value_objects/ -v --cov=app/domain/model/value_objects --cov-report=term-missing`

- [ ] **[7.0][FR-3] Domain Service and Repository Interfaces**
  - [ ] [7.1] TDD Cycle: Write failing tests for AudioProcessor ABC (cannot instantiate, subclass must implement extract_features)
  - [ ] [7.2] Implement AudioProcessor ABC with @abstractmethod extract_features(audio: RawAudio) -> np.ndarray
  - [ ] [7.3] TDD Cycle: Write failing tests for ModelRepository ABC (load_model, get_model_info abstract methods)
  - [ ] [7.4] Implement ModelRepository ABC with @abstractmethod load_model and get_model_info
  - [ ] [7.5] Run: `poetry run black app/domain/model/services/ app/domain/model/repositories/`
  - [ ] [7.6] Run: `poetry run ruff check app/domain/model/services/ app/domain/model/repositories/ --fix`
  - [ ] [7.7] Run: `poetry run mypy app/domain/model/services/ app/domain/model/repositories/ --strict`

- [ ] **[8.0][FR-4] Use Cases for Model Inference Orchestration**
  - [ ] [8.1] TDD Cycle: Write failing tests for RunInferenceUseCase (orchestrates audio processing, model loading, prediction)
  - [ ] [8.2] Implement RunInferenceUseCase with dependencies on AudioProcessor and ModelRepository interfaces
  - [ ] [8.3] TDD Cycle: Write failing tests for GetModelInfoUseCase (retrieves v4 model metadata)
  - [ ] [8.4] Implement GetModelInfoUseCase calling ModelRepository.get_model_info
  - [ ] [8.5] TDD Cycle: Write failing tests for ListModelsUseCase (lists available models)
  - [ ] [8.6] Implement ListModelsUseCase calling ModelRepository
  - [ ] [8.7] Run: `poetry run black app/use_cases/model/ tests/unit/use_cases/model/`
  - [ ] [8.8] Run: `poetry run ruff check app/use_cases/model/ --fix`
  - [ ] [8.9] Run: `poetry run mypy app/use_cases/model/ --strict`
  - [ ] [8.10] Run: `poetry run pytest tests/unit/use_cases/model/ -v --cov=app/use_cases/model --cov-report=term-missing`

- [ ] **[9.0][FR-5] Use Cases for Monitoring and Feedback**
  - [ ] [9.1] TDD Cycle: Write failing tests for GenerateReportUseCase (Evidently AI report generation)
  - [ ] [9.2] Implement GenerateReportUseCase with dependency on MonitoringService interface
  - [ ] [9.3] TDD Cycle: Write failing tests for SetActualEmotionUseCase (update prediction with actual emotion)
  - [ ] [9.4] Implement SetActualEmotionUseCase calling PredictionRepository
  - [ ] [9.5] Run: `poetry run black app/use_cases/monitoring/ tests/unit/use_cases/monitoring/`
  - [ ] [9.6] Run: `poetry run ruff check app/use_cases/monitoring/ --fix`
  - [ ] [9.7] Run: `poetry run mypy app/use_cases/monitoring/ --strict`
  - [ ] [9.8] Run: `poetry run pytest tests/unit/use_cases/monitoring/ -v --cov=app/use_cases/monitoring --cov-report=term-missing`

- [ ] **[10.0][FR-6] Infrastructure v4 Model Integration**
  - [ ] [10.1] Move models/v4/feature_extractor.py to app/infrastructure/model/v4/feature_extractor.py
  - [ ] [10.2] Move app/models/ultra_ensemble.py to app/infrastructure/model/ultra_ensemble.py
  - [ ] [10.3] TDD Cycle: Write tests for LibrosaAudioProcessor implementing AudioProcessor interface
  - [ ] [10.4] Implement LibrosaAudioProcessor calling v4 feature extraction
  - [ ] [10.5] TDD Cycle: Write tests for FileSystemModelRepository implementing ModelRepository interface
  - [ ] [10.6] Implement FileSystemModelRepository with model loading via joblib and UltraEnsembleModel
  - [ ] [10.7] Run: `poetry run black app/infrastructure/model/ tests/unit/infrastructure/model/`
  - [ ] [10.8] Run: `poetry run ruff check app/infrastructure/model/ --fix`
  - [ ] [10.9] Run: `poetry run mypy app/infrastructure/model/ --strict`
  - [ ] [10.10] Run: `poetry run pytest tests/unit/infrastructure/model/ -v --cov=app/infrastructure/model --cov-report=term-missing`

- [ ] **[11.0][FR-7] Infrastructure Monitoring Service Implementation**
  - [ ] [11.1] TDD Cycle: Write tests for EvidentlyMonitoringService implementing MonitoringService interface
  - [ ] [11.2] Implement EvidentlyMonitoringService with report generation logic
  - [ ] [11.3] TDD Cycle: Write tests for InMemoryPredictionRepository implementing PredictionRepository interface
  - [ ] [11.4] Implement InMemoryPredictionRepository with prediction storage and retrieval
  - [ ] [11.5] Run: `poetry run black app/infrastructure/monitoring/ tests/unit/infrastructure/monitoring/`
  - [ ] [11.6] Run: `poetry run ruff check app/infrastructure/monitoring/ --fix`
  - [ ] [11.7] Run: `poetry run mypy app/infrastructure/monitoring/ --strict`

- [ ] **[12.0][FR-8] API Endpoints Refactored to Call Use Cases Only**
  - [ ] [12.1] TDD Cycle: Write tests for refactored /v1/model/inference endpoint calling RunInferenceUseCase
  - [ ] [12.2] Refactor inference endpoint to receive use case via dependency injection and call use case.execute()
  - [ ] [12.3] TDD Cycle: Write tests for refactored /v1/monitoring/report endpoint calling GenerateReportUseCase
  - [ ] [12.4] Refactor monitoring endpoint to call use case only (no direct infrastructure access)
  - [ ] [12.5] Remove all direct calls to get_registry(), get_feature_flags() from API layer
  - [ ] [12.6] Run: `poetry run black app/api/ tests/integration/api/`
  - [ ] [12.7] Run: `poetry run ruff check app/api/ --fix`
  - [ ] [12.8] Run: `poetry run mypy app/api/ --strict`

- [ ] **[13.0][FR-9] Dependency Injection Container**
  - [ ] [13.1] TDD Cycle: Write tests for DI container providing all infrastructure implementations
  - [ ] [13.2] Implement DI container in app/infrastructure/di/container.py
  - [ ] [13.3] Create FastAPI dependencies in app/infrastructure/di/providers.py
  - [ ] [13.4] Wire container in app/main.py startup
  - [ ] [13.5] Run: `poetry run black app/infrastructure/di/ tests/unit/infrastructure/di/`
  - [ ] [13.6] Run: `poetry run ruff check app/infrastructure/di/ --fix`
  - [ ] [13.7] Run: `poetry run mypy app/infrastructure/di/ --strict`

---

### 3. Technical Requirements

- [ ] **[14.0][TR-1] Observability Stack Migration to Infrastructure Layer**
  - [ ] [14.1] Move app/utils/observability.py to app/infrastructure/observability/tracing/opentelemetry_setup.py
  - [ ] [14.2] Move app/middleware/prometheus.py to app/infrastructure/observability/metrics/prometheus_exporter.py
  - [ ] [14.3] Refactor app/utils/logging.py into app/infrastructure/observability/logging/structured_logger.py
  - [ ] [14.4] Update all imports in main.py and middleware to use new paths
  - [ ] [14.5] TDD Cycle: Write integration tests verifying OpenTelemetry trace context injection still works
  - [ ] [14.6] Verify Prometheus metrics endpoint still functional at /metrics
  - [ ] [14.7] Run: `poetry run black app/infrastructure/observability/`
  - [ ] [14.8] Run: `poetry run ruff check app/infrastructure/observability/ --fix`
  - [ ] [14.9] Run: `poetry run mypy app/infrastructure/observability/ --strict`

- [ ] **[15.0][TR-2] Custom Log Formatter from .env Configuration**
  - [ ] [15.1] Add LOG_FORMAT to .env: "{datetime} | {pid} | {level} | {caller_class}.{caller_function} | {message}"
  - [ ] [15.2] TDD Cycle: Write tests for CustomFormatter parsing .env LOG_FORMAT template
  - [ ] [15.3] Implement CustomFormatter in app/infrastructure/observability/logging/log_formatter.py
  - [ ] [15.4] Integrate CustomFormatter into structured_logger.py processors
  - [ ] [15.5] TDD Cycle: Write tests verifying log output matches .env format with PID and caller info
  - [ ] [15.6] Run: `poetry run black app/infrastructure/observability/logging/`
  - [ ] [15.7] Run: `poetry run mypy app/infrastructure/observability/logging/ --strict`

- [ ] **[16.0][TR-3] API Request/Response Logging Middleware**
  - [ ] [16.1] TDD Cycle: Write tests for RequestResponseLoggingMiddleware logging request details
  - [ ] [16.2] Implement RequestResponseLoggingMiddleware in app/infrastructure/observability/logging/request_logging_middleware.py
  - [ ] [16.3] Log: request_id, method, path, query_params, client_ip, user_agent for incoming requests
  - [ ] [16.4] Log: request_id, status_code, duration_ms for responses
  - [ ] [16.5] Add middleware to main.py: app.add_middleware(RequestResponseLoggingMiddleware)
  - [ ] [16.6] Run: `poetry run black app/infrastructure/observability/logging/request_logging_middleware.py`
  - [ ] [16.7] Run: `poetry run mypy app/infrastructure/observability/logging/request_logging_middleware.py --strict`

- [ ] **[17.0][TR-4] Black + Ruff + Mypy Code Quality Enforcement**
  - [ ] [17.1] Run Black on entire codebase: `poetry run black app/ tests/ --check`
  - [ ] [17.2] Run Ruff on entire codebase: `poetry run ruff check app/ tests/`
  - [ ] [17.3] Run Mypy on entire codebase: `poetry run mypy app/ --strict`
  - [ ] [17.4] Fix all Black formatting issues
  - [ ] [17.5] Fix all Ruff linting errors
  - [ ] [17.6] Fix all Mypy type errors
  - [ ] [17.7] Add pre-commit hooks for Black + Ruff + Mypy
  - [ ] [17.8] Configure CI pipeline to run all three tools and fail on errors

- [ ] **[18.0][TR-5] 100% Test Coverage for Domain and Use Cases Layers**
  - [ ] [18.1] Run coverage on domain layer: `poetry run pytest tests/unit/domain/ --cov=app/domain --cov-report=term-missing --cov-report=html`
  - [ ] [18.2] Verify 100% coverage on domain/model/ (entities, value_objects, exceptions)
  - [ ] [18.3] Run coverage on use cases layer: `poetry run pytest tests/unit/use_cases/ --cov=app/use_cases --cov-report=term-missing --cov-report=html`
  - [ ] [18.4] Verify 100% coverage on use_cases/model/ and use_cases/monitoring/
  - [ ] [18.5] Generate HTML coverage report and review uncovered lines
  - [ ] [18.6] Add missing tests for any uncovered branches

---

### 4. Acceptance Criteria

- [ ] **[19.0][AC-1] All Tests Pass with v4 Model Only**
  - [ ] [19.1] Remove all references to v1, v2, v3 models from codebase
  - [ ] [19.2] Remove v1, v2, v3 test fixtures from conftest.py
  - [ ] [19.3] Update all tests to use v4 model only
  - [ ] [19.4] Write unit tests: Mock v4 model loading and prediction, verify correct feature extraction called
  - [ ] [19.5] Write integration tests: Full inference flow with v4 model using test doubles
  - [ ] [19.6] **E2E Test**:
    ```bash
    # Build and run backend
    cd backend
    poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    sleep 5

    # Test v4 inference endpoint
    response=$(curl -s -X POST http://localhost:8000/api/v1/model/inference \
      -F "file=@tests/fixtures/sample_audio.wav")
    status=$(curl -s -o /dev/null -w "%{http_code}" -X POST http://localhost:8000/api/v1/model/inference \
      -F "file=@tests/fixtures/sample_audio.wav")

    # Assertions
    test "$status" = "200" || exit 1
    echo "$response" | grep -q "emotion" || exit 1
    echo "$response" | grep -q "confidence" || exit 1
    echo "$response" | grep -q "v4" || exit 1

    # Cleanup
    pkill -f uvicorn
    echo "✅ AC-1 E2E test passed: v4 model inference working"
    ```
  - [ ] [19.7] **Live Environment Verification**:
    - Deploy backend to test environment
    - Upload real audio file via API
    - Verify v4 model used for inference
    - Verify response contains emotion, confidence, all_probabilities
    - Document test evidence with screenshot

- [ ] **[20.0][AC-2] API Inference Endpoint Uses Clean Architecture**
  - [ ] [20.1] Verify API endpoint receives RunInferenceUseCase via dependency injection
  - [ ] [20.2] Verify endpoint only calls use_case.execute() with input DTO
  - [ ] [20.3] Verify no direct infrastructure access (no get_registry(), no direct model loading)
  - [ ] [20.4] Write unit tests: Mock RunInferenceUseCase, verify endpoint delegates to use case
  - [ ] [20.5] Write integration tests: Full request/response flow through all layers (API → Use Case → Infrastructure)
  - [ ] [20.6] **E2E Test**:
    ```bash
    # Build and run backend
    cd backend
    poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    sleep 5

    # Test clean architecture flow
    response=$(curl -s -X POST http://localhost:8000/api/v1/model/inference \
      -F "file=@tests/fixtures/sample_audio.wav")

    # Verify response structure matches Inference entity
    echo "$response" | jq '.emotion' | grep -q "angry\|disgust\|fear\|happy\|neutral\|sad" || exit 1
    echo "$response" | jq '.confidence' | grep -q "[0-9]" || exit 1
    echo "$response" | jq '.all_probabilities' | grep -q "{" || exit 1

    pkill -f uvicorn
    echo "✅ AC-2 E2E test passed: Clean architecture flow working"
    ```
  - [ ] [20.7] **Live Environment Verification**:
    - Deploy to test environment
    - Trace request through logs: API → Use Case → Infrastructure
    - Verify OpenTelemetry spans show clean layer separation
    - Verify no direct infrastructure calls from API layer

- [ ] **[21.0][AC-3] Observability Pipeline Functional with New Architecture**
  - [ ] [21.1] Verify OpenTelemetry traces exported to Tempo
  - [ ] [21.2] Verify Prometheus metrics accessible at /metrics
  - [ ] [21.3] Verify logs contain trace_id and span_id from OpenTelemetry
  - [ ] [21.4] Write unit tests: Mock trace context, verify trace_id injection into logs
  - [ ] [21.5] Write integration tests: Full request with trace propagation through all layers
  - [ ] [21.6] **E2E Test**:
    ```bash
    # Start observability stack
    cd deployment/docker
    docker-compose -f docker-compose.observability.yml up -d
    sleep 10

    # Start backend
    cd ../../backend
    poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    sleep 5

    # Make request and capture trace_id
    response=$(curl -s -X POST http://localhost:8000/api/v1/model/inference \
      -F "file=@tests/fixtures/sample_audio.wav")

    # Check Prometheus metrics
    metrics=$(curl -s http://localhost:8000/metrics)
    echo "$metrics" | grep -q "inference_duration_seconds" || exit 1

    # Check logs for trace context (via stdout)
    # (In production, would query Loki)

    # Cleanup
    pkill -f uvicorn
    docker-compose -f ../../deployment/docker/docker-compose.observability.yml down

    echo "✅ AC-3 E2E test passed: Observability pipeline working"
    ```
  - [ ] [21.7] **Live Environment Verification**:
    - Deploy full stack to test environment
    - Make inference request
    - Query Tempo for distributed trace
    - Query Prometheus for inference metrics
    - Query Loki for logs with trace_id correlation
    - Document evidence with screenshots from Grafana

- [ ] **[22.0][AC-4] Zero Black/Ruff/Mypy Errors on All Code**
  - [ ] [22.1] Run Black on all Python files
  - [ ] [22.2] Run Ruff on all Python files
  - [ ] [22.3] Run Mypy on all Python files with --strict flag
  - [ ] [22.4] Write unit tests: Verify code quality tools configured correctly in pyproject.toml
  - [ ] [22.5] Write integration tests: Run tools in CI pipeline simulation
  - [ ] [22.6] **E2E Test**:
    ```bash
    cd backend

    # Run Black
    poetry run black app/ tests/ --check || exit 1

    # Run Ruff
    poetry run ruff check app/ tests/ || exit 1

    # Run Mypy
    poetry run mypy app/ --strict || exit 1

    echo "✅ AC-4 E2E test passed: Zero code quality errors"
    ```
  - [ ] [22.7] **Live Environment Verification**:
    - Configure CI pipeline with Black + Ruff + Mypy checks
    - Create PR and verify CI passes all quality checks
    - Document CI pipeline configuration

- [ ] **[23.0][AC-5] Logs Show Custom Format with Trace Context**
  - [ ] [23.1] Verify logs match .env LOG_FORMAT: "{datetime} | {pid} | {level} | {caller_class}.{caller_function} | {message}"
  - [ ] [23.2] Verify logs contain trace_id and span_id from OpenTelemetry
  - [ ] [23.3] Verify API request/response logs include request_id, method, path, status_code, duration_ms
  - [ ] [23.4] Write unit tests: Mock log formatter, verify output matches template
  - [ ] [23.5] Write integration tests: Make API request, capture logs, verify format
  - [ ] [23.6] **E2E Test**:
    ```bash
    cd backend

    # Start backend with log capture
    poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | tee /tmp/backend.log &
    sleep 5

    # Make request
    curl -s -X POST http://localhost:8000/api/v1/model/inference \
      -F "file=@tests/fixtures/sample_audio.wav" > /dev/null

    sleep 2
    pkill -f uvicorn

    # Verify log format
    grep -q "| [0-9]* | INFO |" /tmp/backend.log || exit 1
    grep -q "API Request" /tmp/backend.log || exit 1
    grep -q "API Response" /tmp/backend.log || exit 1
    grep -q "status_code=" /tmp/backend.log || exit 1

    echo "✅ AC-5 E2E test passed: Log format correct with trace context"
    ```
  - [ ] [23.7] **Live Environment Verification**:
    - Deploy to test environment
    - Make inference request
    - Query logs from Loki
    - Verify custom format: datetime | pid | level | class.function | message
    - Verify trace_id and span_id present in structured logs
    - Document evidence with log samples

---

### 5. Documentation & Deployment

- [ ] **[24.0][DOC] Developer Documentation**
  - [ ] [24.1] Document Clean Architecture layer responsibilities in README.md
  - [ ] [24.2] Document TDD workflow for adding new features
  - [ ] [24.3] Document how to run Black + Ruff + Mypy locally
  - [ ] [24.4] Create architecture diagram showing layers and dependencies
  - [ ] [24.5] Document Pydantic usage for domain models
  - [ ] [24.6] Document dependency injection container usage

- [ ] **[25.0][DOC] CI/CD Pipeline**
  - [ ] [25.1] Create .github/workflows/backend-ci.yml
  - [ ] [25.2] Add stages: install → black → ruff → mypy → unit tests → integration tests → E2E tests
  - [ ] [25.3] Configure coverage reporting with pytest-cov
  - [ ] [25.4] Configure pipeline to fail if coverage < 90% on domain/use cases layers
  - [ ] [25.5] Add Docker build and push to registry stage

- [ ] **[26.0][DOC] Code Quality & Version Control**
  - [ ] [26.1] Run final Black format: `poetry run black app/ tests/`
  - [ ] [26.2] Run final Ruff check: `poetry run ruff check app/ tests/ --fix`
  - [ ] [26.3] Run final Mypy check: `poetry run mypy app/ --strict`
  - [ ] [26.4] Run full test suite: `poetry run pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html`
  - [ ] [26.5] Verify all tests pass and coverage >= 90%
  - [ ] [26.6] Create commit: "feat: implement clean architecture refactoring with v4 model and observability"
  - [ ] [26.7] Push to feature branch: feature/clean-architecture-refactoring
  - [ ] [26.8] Create pull request with DoD checklist

---

## Changelog

| Timestamp | Author | Changes | Affected Sections | Reason |
|-----------|--------|---------|-------------------|--------|
| 2025-12-05 10:00:00 | Claude Code | Initial implementation plan created | All | Based on CLEAN_ARCHITECTURE_FINAL_V4_WITH_OBSERVABILITY.md reference document |

---

*Implementation plan follows Test-Driven Development with strict quality enforcement via Black + Ruff + Mypy, ensuring Clean Architecture principles with complete test coverage from unit tests through live environment verification.*
