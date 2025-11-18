# Implementation Plan Artifact

## Purpose

Task-based execution guide template for solution-architect to generate implementation plans from user stories. Provides requirement-driven task organization with complete test coverage and direct traceability from requirements to implementation to validation.

**Key Elements**: Requirement-driven structure, hierarchical tasks, complete test coverage (unit + integration + E2E + live), 15-30min sub-tasks

**Companion Document**: Tech research (US-###-tech-research.md) provides WHAT/WHY, impl plan provides HOW

## Template Structure

**Core Sections**:
1. **Metadata** - ID (`US-###-IMPL-PLAN`), Title, User Story ID, Tech Research ID, timestamps, complexity, dependencies
2. **Quick Reference** - Tech stack, architectural pattern, link to tech research
3. **Requirements Coverage Validation** (mandatory) - 100% FR/TR/AC mapping with test coverage tracking
4. **Task-Based Implementation Plan** - Requirement-driven organization with hierarchical parent/sub-task structure
5. **Changelog** - Timestamp, author, changes, affected sections, reason

**Execution Guidelines**:
- Checkbox usage: All tasks unchecked `[ ]` by default
- Task hierarchy: Parent tasks organized by requirement type with sequential numbering
- Requirement-aligned: Each FR/TR/AC has dedicated parent task
- Test coverage: All ACs include unit tests, integration tests, E2E tests, and live environment verification

See Section Requirements below for detailed specifications.

## Section Requirements

| Section | Key Requirements |
|---------|------------------|
| **Metadata** | ID format `US-###-IMPL-PLAN`, Tech Research ID link, full timestamps (YYYY-MM-DD HH:mm:ss), status history |
| **Quick Reference** | Tech stack summary, architectural pattern, tech research link |
| **Requirements Coverage** | 100% FR/TR/AC coverage with test tracking: Unit Tests, Integration Tests, E2E Tests, Live Verification |
| **Task Plan** | Requirement-driven organization: Manual Prerequisites → Environment & Setup → FR tasks → TR tasks → AC tasks → Documentation |
| **Changelog** | Full timestamp, author, change summary, affected sections, reason |

### Abstraction Guidelines
- Describe **capabilities** (WHAT), not file paths (WHERE)
- Specify **requirements/behavior**, not structure
- Use placeholders: [entity names], [feature capabilities], [business logic requirements]
- Trust developer to apply Clean Architecture standards

### API Field Extraction Task Requirements (CRITICAL)

**When to Apply**: If tech research document includes "API Research" section with field extraction mappings

**Mandatory Task Pattern** for each API endpoint:

```markdown
- [ ] **[{X}.0][FR-Y] {API Name} Data Extraction**
  - [ ] [{X}.1] Query {API Name} endpoint: {METHOD} {URL}
    - Request payload: {exact payload from tech research}
    - Authentication: {auth method from tech research}
  - [ ] [{X}.2] Parse response and extract fields per tech research mapping:
    - Extract `{api_field_path}` → store as `{domain_field_name}` ({data type})
    - Extract `{api_field_path}` → store as `{domain_field_name}` ({data type})
    - (List ALL fields from tech research "Field Extraction Mapping")
  - [ ] [{X}.3] Validate extracted data matches expected structure:
    - Assert `{domain_field_name}` is not None
    - Assert `{domain_field_name}` type is {expected_type}
    - Log extraction: logger.debug("Extracted fields", {field_name}={value})
  - [ ] [{X}.4] Handle missing/malformed fields:
    - If `{critical_field}` missing → log warning, skip record
    - If `{optional_field}` missing → use default value
  - [ ] [{X}.5] Integration test: Verify extraction with real API call
    - Call real API (use .env.local credentials)
    - Assert extracted fields match tech research documentation
    - Assert field types match domain model
```

**Anti-Pattern Example (FORBIDDEN)**:
```markdown
❌ WRONG: Vague task without field-specific extraction
- [ ] [14.1] Query Hyperliquid API for prices
- [ ] [14.2] Extract price data

✅ CORRECT: Field-specific extraction per tech research
- [ ] [14.1] Query Hyperliquid metaAndAssetCtxs endpoint: POST https://api.hyperliquid.xyz/info
  - Request payload: {"type": "metaAndAssetCtxs"}
- [ ] [14.2] Parse response and extract fields per tech research section 2.3:
  - Extract `data[0].universe[i].name` → store as `base_token` (str)
  - Extract `data[1][i].midPx` → store as `direct_price` (Decimal)
  - Extract `data[1][i].dayNtlVlm` → store as `liquidity_usd` (Decimal)
- [ ] [14.3] Validate extracted data matches expected structure:
  - Assert `direct_price` is not None (critical field)
  - Assert `direct_price` > 0 (business rule validation)
  - Log extraction: logger.debug("Extracted Hyperliquid pool", base_token=base_token, direct_price=direct_price)
```

**Enforcement**:
- If tech research has "API Research" section BUT implementation plan has vague tasks → **BLOCKING FAILURE**
- If tasks don't reference exact field paths from tech research → **BLOCKING FAILURE**
- If no validation subtask exists to verify extracted fields → **BLOCKING FAILURE**

### Requirements Coverage Validation (Mandatory Section)

**Location:** After Quick Reference, before Task-Based Plan

**Format:**
```markdown
## Requirements Coverage Validation

### Functional Requirements
| Requirement ID | Description | Parent Task | Status |
|----------------|-------------|-------------|--------|
| FR-1 | {Description} | [{X}.0][FR-1] (N subtasks) | [ ] |
| FR-2 | {Description} | [{X}.0][FR-2] (N subtasks) | [ ] |

### Technical Requirements
| Requirement ID | Description | Parent Task | Status |
|----------------|-------------|-------------|--------|
| TR-1 | {Description} | [{X}.0][TR-1] (N subtasks) | [ ] |
| TR-2 | {Description} | [{X}.0][TR-2] (N subtasks) | [ ] |

### Acceptance Criteria
| Criteria ID | Description | Parent Task | Unit Tests | Integration Tests | E2E Test | Live Verification |
|-------------|-------------|-------------|------------|-------------------|----------|-------------------|
| AC-1 | {Description} | [{X}.0][AC-1] (N subtasks) | [{X}.4] | [{X}.5] | [{X}.6] | [{X}.7] |
| AC-2 | {Description} | [{X}.0][AC-2] (N subtasks) | [{X}.4] | [{X}.5] | [{X}.6] | [{X}.7] |

**Coverage Summary**:
- ✅ Functional Requirements: X/X mapped (100%)
- ✅ Technical Requirements: Y/Y mapped (100%)
- ✅ Acceptance Criteria: Z/Z mapped with complete test coverage (100%)
```

**Validation:** solution-architect MUST verify:
1. Every FR/TR/AC has dedicated parent task
2. Every AC has 4 test levels: unit, integration, E2E, live verification
3. Parent task numbering matches requirement IDs

### Task Type Markers

**Marker Usage**:
- **Parent tasks**: `[{X}.0][CATEGORY]` where CATEGORY = MANUAL, SETUP, FR-X, TR-X, AC-X, TEST, DOC
- **Subtasks**: `[{X}.Y]` (default: automated) or `[{X}.Y][MANUAL]` (requires human action)
- **Default assumption**: Tasks are automated unless marked `[MANUAL]`
- **No `[AUTO]` marker**: Redundant, automation is default

**Marker Definitions**:
- `[MANUAL]` - Human action required (subscription, payment, external UI navigation, manual verification, approval)
- No marker - Automated task executed by py-developer or CI/CD

**Rules:**
- Parent tasks NEVER have `[MANUAL]` or automation markers (only category prefix)
- Subtasks marked `[MANUAL]` only when human action required
- py-developer STOPS at `[MANUAL]` tasks, executes all unmarked tasks automatically

## Task-Based Implementation Plan Structure

### Organization Overview

Tasks organized by requirement type for direct traceability:

1. **Manual Prerequisites** (`[{X}.0][MANUAL]`) - Human-required actions (subscriptions, external account setup)
2. **Environment & Setup** (`[{X}.0][SETUP]`) - Foundational infrastructure (Docker, dependencies, base classes)
3. **Functional Requirements** (`[{X}.0][FR-N]`) - One parent task per functional requirement
4. **Technical Requirements** (`[{X}.0][TR-N]`) - One parent task per technical requirement
5. **Acceptance Criteria** (`[{X}.0][AC-N]`) - One parent task per acceptance criterion with 4 test levels
6. **Documentation & Deployment** (`[{X}.0][DOC]`) - Final deliverables

### Parent Task Numbering Rules

**Task Numbering Format**:
- Manual Prerequisites: `[1.0][MANUAL]`, `[2.0][MANUAL]`, ...
- Environment & Setup: `[3.0][SETUP]`, `[4.0][SETUP]`, ...
- Functional Requirements: `[5.0][FR-1]`, `[6.0][FR-2]`, ... (matches user story FR IDs)
- Technical Requirements: `[{X}.0][TR-1]`, `[{X}.0][TR-2]`, ... (matches user story TR IDs)
- Acceptance Criteria: `[{X}.0][AC-1]`, `[{X}.0][AC-2]`, ... (matches user story AC IDs)
- Documentation: `[{X}.0][DOC]` (sequential)

**Subtask Numbering Format**: `[{X}.1]`, `[{X}.2]`, `[{X}.3]`, ..., `[{X}.N]`

**Example**:
```
- [ ] **[5.0][FR-1] API Key Environment Management**
  - [ ] [5.1] Implement load_api_key() function
  - [ ] [5.2] Add error handling for missing credentials
  - [ ] [5.3] Implement format validation
  - [ ] [5.4] Write unit tests
  - [ ] [5.5] Live environment test
```

### Standard Parent Task Structure

**Functional/Technical Requirements**:
```markdown
- [ ] **[{X}.0][{REQ-ID}] {Requirement Description}**
  - [ ] [{X}.1] Implement {capability 1}
  - [ ] [{X}.2] Implement {capability 2}
  - [ ] [{X}.3] Implement {capability 3}
  - [ ] [{X}.{N-1}] Write unit tests: {test scenarios}
  - [ ] [{X}.{N}] Live environment test: {deployment → verification steps}
```

**Acceptance Criteria** (MUST include all 4 test levels):
```markdown
- [ ] **[{X}.0][AC-N] {Acceptance Criterion Description}**
  - [ ] [{X}.1-{X}.3] Implementation subtasks
  - [ ] [{X}.4] Write unit tests: {mocked scenarios}
  - [ ] [{X}.5] Write integration tests: {component integration with test doubles}
  - [ ] [{X}.6] **E2E Test**:
    ```bash
    # Build and deploy
    docker-compose build
    docker-compose up -d

    # Test with curl
    response=$(curl -s http://localhost:8000/endpoint)
    status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/endpoint)

    # Assertions
    test "$status" = "200" || exit 1
    echo "$response" | grep -q "expected text" || exit 1

    echo "✅ AC-N E2E test passed"
    ```
  - [ ] [{X}.7] **Live Environment Verification**:
    - Deploy to test environment
    - Verify with real external APIs (not mocks)
    - Validate production-like behavior
    - Document evidence of successful validation
```


### Acceptance Criteria Requirements

**Mandatory Test Levels** (all ACs MUST include):

1. **Unit Tests** (`[{X}.4]`):
   - Fast, isolated tests with mocked dependencies
   - Test individual functions/methods
   - Verify logic correctness without external dependencies

2. **Integration Tests** (`[{X}.5]`):
   - Test component integration with test doubles/stubs
   - Verify request/response flows through layers
   - Faster than E2E, more realistic than unit tests

3. **E2E Tests** (`[{X}.6]`):
   - Deployed Docker environment with bash scripts
   - Use `docker-compose build` and `docker-compose up -d`
   - Validate with `curl` commands and bash assertions
   - Exit codes: 0 = pass, 1 = fail

4. **Live Environment Verification** (`[{X}.7]`):
   - Deploy to test/staging/production environment
   - Use REAL external APIs (no mocks/stubs)
   - Verify actual production-like behavior
   - Document evidence (logs, metrics, responses)


## Complete Example: US-025 Authentication Setup

```markdown
## Task-Based Implementation Plan

### Execution Instructions
Complete tasks in order: Manual Prerequisites → Environment & Setup → Functional Requirements → Technical Requirements → Acceptance Criteria → Additional Tests → Documentation

---

### 1. Manual Prerequisites

- [ ] **[1.0][MANUAL] External Service Provisioning**
  - [ ] [1.1][MANUAL] Subscribe to LunarCrush Individual Plan ($30/month) at https://lunarcrush.com/pricing
  - [ ] [1.2][MANUAL] Navigate to Dashboard > Developers > API > Authentication
  - [ ] [1.3][MANUAL] Generate API key and copy to .env.local
  - [ ] [1.4][MANUAL] Test API key with curl command

---

### 2. Environment & Setup

- [ ] **[2.0][SETUP] Development Environment Setup**
  - [ ] [2.1] Verify Python 3.11+ installed
  - [ ] [2.2] Create poetry virtual environment
  - [ ] [2.3] Install dependencies: httpx, python-dotenv
  - [ ] [2.4] Create .env.example template

- [ ] **[3.0][SETUP] Docker Infrastructure**
  - [ ] [3.1] Create Dockerfile with Python 3.11+ base
  - [ ] [3.2] Create docker-compose.yml
  - [ ] [3.3] Configure volume mounts for .env.local
  - [ ] [3.4] Test Docker build

- [ ] **[4.0][SETUP] Exception Hierarchy**
  - [ ] [4.1] Implement LunarCrushAuthenticationError (base)
  - [ ] [4.2] Implement LunarCrushInvalidAPIKeyError (401)
  - [ ] [4.3] Implement LunarCrushPermissionError (403)
  - [ ] [4.4] Implement LunarCrushNetworkError
  - [ ] [4.5] Implement LunarCrushMissingCredentialsError

---

### 3. Functional Requirements

- [ ] **[5.0][FR-1] API Key Environment Management**
  - [ ] [5.1] Implement load_api_key() with python-dotenv
  - [ ] [5.2] Add error handling for missing LUNARCRUSH_API_KEY
  - [ ] [5.3] Implement API key format validation: regex ^[a-zA-Z0-9]{32,64}$
  - [ ] [5.4] Write unit tests: valid key, missing key, invalid format
  - [ ] [5.5] Live test: deploy without .env → verify startup fails

- [ ] **[6.0][FR-2] HTTP Request Header Configuration**
  - [ ] [6.1] Implement automatic Bearer token header injection
  - [ ] [6.2] Set Content-Type: application/json
  - [ ] [6.3] Write unit tests: verify headers constructed correctly
  - [ ] [6.4] Live test: verify Authorization header sent to real API

---

### 4. Technical Requirements

- [ ] **[11.0][TR-1] Authentication Response Time <2s p95**
  - [ ] [11.1] Implement performance measurement instrumentation
  - [ ] [11.2] Create performance test: 100 consecutive calls
  - [ ] [11.3] Measure latency distribution: p50, p95, p99
  - [ ] [11.4] Write unit tests: verify instrumentation
  - [ ] [11.5] Live test: run 100 calls → verify p95 <2s

---

### 5. Acceptance Criteria

- [ ] **[16.0][AC-1] Valid API Key Returns 200 OK, Confirmation Message, No Key Exposure**
  - [ ] [16.1] Implement /health/lunarcrush/auth endpoint
  - [ ] [16.2] Return status="healthy" + confirmation message
  - [ ] [16.3] Ensure API key never in response/logs
  - [ ] [16.4] Write unit tests: mock 200 OK, verify response structure
  - [ ] [16.5] Write integration tests: full request/response flow, credential redaction
  - [ ] [16.6] **E2E Test**:
    ```bash
    docker-compose up -d
    response=$(curl -s http://localhost:8000/health/lunarcrush/auth)
    status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health/lunarcrush/auth)
    test "$status" = "200" || exit 1
    echo "$response" | grep -q "Authentication successful" || exit 1
    echo "✅ AC-1 E2E test passed"
    ```
  - [ ] [16.7] **Live Environment Verification**:
    - Deploy to test environment
    - Verify HTTP 200 with real LunarCrush API call
    - Verify logs show no API key exposure

---

### 6. Documentation & Deployment

- [ ] **[22.0][DOC] Developer Documentation**
  - [ ] [22.1] Write setup guide
  - [ ] [22.2] Write troubleshooting guide
  - [ ] [22.3] Document security best practices
  - [ ] [22.4] Add inline code documentation

- [ ] **[23.0][DOC] CI/CD Pipeline**
  - [ ] [23.1] Create .github/workflows/ci.yml
  - [ ] [23.2] Add stages: build → unit → integration → E2E → live tests
  - [ ] [23.3] Configure pipeline to run all test levels
  - [ ] [23.4] Configure build failure if any test fails

- [ ] **[24.0][DOC] Code Quality & Version Control**
  - [ ] [24.1] Run code formatter: black
  - [ ] [24.2] Run linter: flake8
  - [ ] [24.3] Run type checker: mypy
  - [ ] [24.4] Fix all issues
  - [ ] [24.5] Create commit with descriptive message
  - [ ] [24.6] Push to feature branch
  - [ ] [24.7] Create pull request with DoD checklist
```

---

*Implementation plan artifact provides requirement-driven task organization with complete test coverage, ensuring comprehensive validation from unit tests through live environment verification.*
