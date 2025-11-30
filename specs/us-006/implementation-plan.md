# Implementation Plan: Tab 3 Results Redesign

## Metadata
| Field | Value |
|-------|-------|
| ID | US-006-IMPL-PLAN |
| Title | Tab 3 Results Redesign Implementation |
| User Story ID | US-006 |
| Tech Research ID | N/A |
| Created | 2025-01-30 15:30:00 |
| Status | Ready for Implementation |
| Last Updated | 2025-01-30 15:30:00 |
| Estimated Complexity | Medium (6-8 hours) |

## Quick Reference

### Tech Stack
- **Frontend**: Streamlit 1.51.0+, Python 3.11+
- **UI Components**: streamlit-antd-components 0.3.2, Material Symbols Rounded (CSS)
- **Visualization**: Plotly (for progress bars if needed)
- **API**: Backend FastAPI running on `http://127.0.0.1:8000`

### Architectural Pattern
- **Pattern**: Component-based UI with API-driven data
- **Data Flow**: Backend API → Streamlit frontend → Ant Design cards display
- **State Management**: Streamlit session_state for results caching

### Backend API Endpoints
1. **Inference**: `POST /v1/infer/local/latest` - Returns prediction results
2. **Metadata**: `GET /v1/models/local/latest` - Returns model metadata

## Requirements Coverage Validation

### Functional Requirements
| Requirement ID | Description | Parent Task | Status |
|----------------|-------------|-------------|--------|
| FR-1 | Primary Emotion Display | [5.0][FR-1] (5 subtasks) | [ ] |
| FR-2 | Confidence Metrics | [6.0][FR-2] (5 subtasks) | [ ] |
| FR-3 | Model Information Card | [7.0][FR-3] (5 subtasks) | [ ] |
| FR-4 | Model Description Card | [8.0][FR-4] (5 subtasks) | [ ] |
| FR-5 | Performance Metrics Visualization | [9.0][FR-5] (5 subtasks) | [ ] |
| FR-6 | Two-Column Card Layout | [10.0][FR-6] (5 subtasks) | [ ] |
| FR-7 | Backend API Integration | [11.0][FR-7] (6 subtasks) | [ ] |
| FR-8 | Mock Mode Support | [12.0][FR-8] (5 subtasks) | [ ] |

### Technical Requirements
| Requirement ID | Description | Parent Task | Status |
|----------------|-------------|-------------|--------|
| TR-1 | UI Render Time <500ms | [13.0][TR-1] (4 subtasks) | [ ] |
| TR-2 | API Response Parsing | [14.0][TR-2] (5 subtasks) | [ ] |
| TR-3 | Error Handling | [15.0][TR-3] (5 subtasks) | [ ] |
| TR-4 | Processing Time Categorization | [16.0][TR-4] (4 subtasks) | [ ] |

### Acceptance Criteria
| Criteria ID | Description | Parent Task | Unit Tests | Integration Tests | E2E Test | Live Verification |
|-------------|-------------|-------------|------------|-------------------|----------|-------------------|
| AC-1 | Primary emotion with metrics displayed | [17.0][AC-1] (7 subtasks) | [17.4] | [17.5] | [17.6] | [17.7] |
| AC-2 | Model information card displays correctly | [18.0][AC-2] (7 subtasks) | [18.4] | [18.5] | [18.6] | [18.7] |
| AC-3 | Model description card displays correctly | [19.0][AC-3] (7 subtasks) | [19.4] | [19.5] | [19.6] | [19.7] |
| AC-4 | Processing time with color-coded progress bar | [20.0][AC-4] (7 subtasks) | [20.4] | [20.5] | [20.6] | [20.7] |
| AC-5 | Cards in 2-column grid layout | [21.0][AC-5] (7 subtasks) | [21.4] | [21.5] | [21.6] | [21.7] |
| AC-6 | Real API calls when not in mock mode | [22.0][AC-6] (7 subtasks) | [22.4] | [22.5] | [22.6] | [22.7] |
| AC-7 | Mock data when backend unavailable | [23.0][AC-7] (7 subtasks) | [23.4] | [23.5] | [23.6] | [23.7] |
| AC-8 | Error handling for API failures | [24.0][AC-8] (7 subtasks) | [24.4] | [24.5] | [24.6] | [24.7] |
| AC-9 | End-to-end workflow completion | [25.0][AC-9] (7 subtasks) | [25.4] | [25.5] | [25.6] | [25.7] |

**Coverage Summary**:
- ✅ Functional Requirements: 8/8 mapped (100%)
- ✅ Technical Requirements: 4/4 mapped (100%)
- ✅ Acceptance Criteria: 9/9 mapped with complete test coverage (100%)

## Task-Based Implementation Plan

### Execution Instructions
Complete tasks in order: Environment & Setup → Functional Requirements → Technical Requirements → Acceptance Criteria → Documentation

---

### 1. Environment & Setup

- [x] **[1.0][SETUP] Development Environment Verification**
  - [x] [1.1] Verify Streamlit 1.51.0+ installed: `streamlit --version`
  - [x] [1.2] Verify streamlit-antd-components 0.3.2+ installed
  - [x] [1.3] Verify Material Symbols Rounded CSS already imported in ml-app.py
  - [x] [1.4] Verify backend API accessible at http://127.0.0.1:8000
  - [x] [1.5] Test API endpoints with curl:
    ```bash
    # Test inference endpoint
    curl -X POST "http://127.0.0.1:8000/v1/infer/local/latest" \
      -H "Content-Type: multipart/form-data" \
      -F "file=@data/AudioWAV/1001_DFA_ANG_XX.wav;type=audio/wav"

    # Test metadata endpoint
    curl -s "http://127.0.0.1:8000/v1/models/local/latest"
    ```

- [x] **[2.0][SETUP] Material Icon Mapping Configuration**
  - [x] [2.1] Create emotion-to-icon mapping dictionary:
    - angry → "sentiment_very_dissatisfied"
    - disgust → "sick"
    - fear → "sentiment_stressed"
    - happy → "sentiment_very_satisfied"
    - neutral → "sentiment_neutral"
    - sad → "sentiment_dissatisfied"
  - [x] [2.2] Document Material Symbols Rounded usage pattern
  - [x] [2.3] Create helper function `get_emotion_icon(emotion: str) -> str`

- [x] **[3.0][SETUP] Mock Data Structure**
  - [x] [3.1] Create mock inference response matching real API structure:
    ```python
    {
        "version": "2",
        "prediction": {
            "emotion": "happy",
            "confidence": 0.95,
            "all_probabilities": {"happy": 0.95}
        },
        "model_info": {
            "type": "Pipeline (StandardScaler + RFE + SVC)",
            "features_used": 78
        },
        "processing_time_ms": 45.32
    }
    ```
  - [x] [3.2] Create mock metadata response matching real API structure:
    ```python
    {
        "version": "2",
        "model_name": "SVM with MFCC Features",
        "model_type": "Pipeline (StandardScaler + RFE + SVC)",
        "description": "Support Vector Machine with MFCC-based features...",
        "feature_dimension": 78,
        "feature_extraction": "MFCCs with delta and delta-delta coefficients",
        "classes": ["angry", "disgust", "fear", "happy", "neutral", "sad"],
        "num_classes": 6,
        "created_date": "2024-01-20",
        "dataset": "CREMA-D",
        "notes": "Improved model with feature selection and SVM classifier"
    }
    ```
  - [x] [3.3] Implement `get_mock_inference_result()` function
  - [x] [3.4] Implement `get_mock_model_metadata()` function

- [x] **[4.0][SETUP] API Client Functions**
  - [x] [4.1] Implement `fetch_latest_model_metadata()` function:
    - Call GET /v1/models/local/latest
    - Parse JSON response
    - Return metadata dict or None on error
  - [x] [4.2] Add error handling for API timeouts and connection errors
  - [x] [4.3] Add logging for API calls
  - [x] [4.4] Test with real backend

---

### 2. Functional Requirements

- [x] **[5.0][FR-1] Primary Emotion Display with Material Icon**
  - [x] [5.1] Create `render_emotion_hero(emotion: str)` function
  - [x] [5.2] Use Material Symbols Rounded icon via CSS class
  - [x] [5.3] Display large icon (64px or larger) with emotion label below
  - [x] [5.4] Implement responsive sizing for different screen widths
  - [ ] [5.5] Write unit tests: verify correct icon returned for each emotion

- [x] **[6.0][FR-2] Confidence Metrics Display**
  - [x] [6.1] Create three metric cards using `st.metric()`:
    - Confidence percentage (formatted as "95%")
    - Processing time (formatted as "45.32 ms")
    - Model version (formatted as "v2")
  - [x] [6.2] Arrange in 3-column layout using `st.columns(3)`
  - [x] [6.3] Add metric labels with clear typography
  - [ ] [6.4] Write unit tests: verify metrics format correctly
  - [x] [6.5] Live test: verify metrics display with real API data

- [x] **[7.0][FR-3] Model Information Card**
  - [x] [7.1] Create Ant Design card with title "📊 Model Information"
  - [x] [7.2] Display fields using label: value format:
    - Model Name
    - Architecture
    - Feature Extraction
    - Feature Dimension
    - Training Dataset
    - Created Date
    - Emotion Classes (formatted as comma-separated list)
  - [x] [7.3] Implement clean typography with proper spacing
  - [ ] [7.4] Write unit tests: verify all fields extracted from metadata
  - [x] [7.5] Live test: verify card displays real metadata

- [x] **[8.0][FR-4] Model Description Card**
  - [x] [8.1] Create Ant Design card with title "📝 Model Description"
  - [x] [8.2] Display description text from metadata
  - [x] [8.3] Display notes section below description
  - [ ] [8.4] Write unit tests: verify description and notes rendered
  - [x] [8.5] Live test: verify description card with real metadata

- [x] **[9.0][FR-5] Performance Metrics with Color-Coded Progress Bar**
  - [x] [9.1] Implement `get_performance_color(time_ms: float) -> str` function:
    - Returns "green" if time_ms < 100
    - Returns "yellow" if 100 <= time_ms < 500
    - Returns "red" if time_ms >= 500
  - [x] [9.2] Create Ant Design card with title "⚡ Performance Metrics"
  - [x] [9.3] Display processing time value with unit (e.g., "45.32 ms")
  - [x] [9.4] Implement progress bar using `st.progress()` or custom HTML with color coding
  - [ ] [9.5] Write unit tests: verify color logic for all ranges

- [x] **[10.0][FR-6] Two-Column Card Layout**
  - [x] [10.1] Implement 2-column layout using `st.columns([1, 1])`
  - [x] [10.2] Organize cards:
    - Column 1: Emotion Hero + Metrics, Model Information
    - Column 2: Model Description, Performance Metrics
  - [x] [10.3] Use Ant Design cards via `streamlit_antd_components.sac.card()`
  - [x] [10.4] Ensure proper spacing between cards
  - [ ] [10.5] Write unit tests: verify column structure

- [x] **[11.0][FR-7] Backend API Integration**
  - [x] [11.1] Implement API call in `stage_inference_results()` function
  - [x] [11.2] Call `fetch_latest_model_metadata()` to get model info
  - [x] [11.3] Combine inference result (already in session state) with metadata
  - [x] [11.4] Handle case where inference result is from `/infer/local/latest` endpoint
  - [ ] [11.5] Write unit tests: verify API integration with mocked responses
  - [x] [11.6] Live test: verify real API calls when backend available

- [x] **[12.0][FR-8] Mock Mode Support**
  - [x] [12.1] Check `get_backend_status()` to determine if using real or mock backend
  - [x] [12.2] If mock mode or backend unavailable, use `get_mock_inference_result()`
  - [x] [12.3] If mock mode, use `get_mock_model_metadata()`
  - [x] [12.4] Ensure mock data structure matches real API responses exactly
  - [ ] [12.5] Write unit tests: verify mock mode activated correctly

---

### 3. Technical Requirements

- [x] **[13.0][TR-1] UI Render Time <500ms**
  - [x] [13.1] Minimize API calls - cache metadata in session_state
  - [x] [13.2] Use `@st.cache_data` for static content where appropriate
  - [ ] [13.3] Write unit tests: verify caching mechanism
  - [x] [13.4] Performance test: measure render time, ensure <500ms

- [x] **[14.0][TR-2] API Response Parsing Accuracy**
  - [x] [14.1] Implement strict field extraction from inference response:
    - Extract `version` → store as `model_version` (str)
    - Extract `prediction.emotion` → store as `emotion` (str)
    - Extract `prediction.confidence` → store as `confidence` (float)
    - Extract `model_info.type` → store as `model_type` (str)
    - Extract `model_info.features_used` → store as `features_used` (int)
    - Extract `processing_time_ms` → store as `processing_time_ms` (float)
  - [x] [14.2] Implement strict field extraction from metadata response:
    - Extract `model_name` → store as `model_name` (str)
    - Extract `description` → store as `description` (str)
    - Extract `feature_extraction` → store as `feature_extraction` (str)
    - Extract `classes` → store as `emotion_classes` (list)
    - Extract `created_date` → store as `created_date` (str)
    - Extract `dataset` → store as `dataset` (str)
    - Extract `notes` → store as `notes` (str)
  - [x] [14.3] Validate field types match expectations
  - [ ] [14.4] Write unit tests: verify all fields extracted correctly
  - [x] [14.5] Integration test: parse real API responses

- [x] **[15.0][TR-3] Graceful Error Handling**
  - [x] [15.1] Implement try-except blocks for API calls
  - [x] [15.2] Display user-friendly error message: "Unable to fetch results. Please try again."
  - [x] [15.3] Add suggestion: "Check backend connection at http://127.0.0.1:8000"
  - [x] [15.4] Log errors with details for debugging
  - [ ] [15.5] Write unit tests: verify error handling paths

- [x] **[16.0][TR-4] Processing Time Categorization**
  - [x] [16.1] Implement categorization logic:
    - time < 100ms → "Fast" (green)
    - 100ms <= time < 500ms → "Medium" (yellow)
    - time >= 500ms → "Slow" (red)
  - [x] [16.2] Apply color to progress bar or text indicator
  - [ ] [16.3] Write unit tests: test all boundary conditions
  - [x] [16.4] Live test: verify color changes based on actual processing times

---

### 4. Acceptance Criteria

- [ ] **[17.0][AC-1] Primary Emotion with Metrics Displayed**
  - [ ] [17.1] Render emotion hero section with Material Icon
  - [ ] [17.2] Display confidence percentage formatted correctly
  - [ ] [17.3] Display processing time in milliseconds
  - [ ] [17.4] Write unit tests: verify all metrics render with mocked data
  - [ ] [17.5] Write integration tests: verify metrics extracted from session_state
  - [ ] [17.6] **E2E Test**:
    ```bash
    # Launch Streamlit app
    streamlit run frontend/streamlit_app/src/ml-app.py --server.port 8510 &
    STREAMLIT_PID=$!
    sleep 15

    # Verify app accessible
    curl -s http://localhost:8510 | grep -q "Speech Emotion Recognition" || exit 1

    # Manual verification step (document in test log)
    echo "✅ AC-1 E2E: Upload audio, navigate to Tab 3, verify emotion + metrics display"

    kill $STREAMLIT_PID
    ```
  - [ ] [17.7] **Live Environment Verification**:
    - Deploy with real backend
    - Upload sample audio file
    - Navigate to Tab 3
    - Verify emotion icon displays correctly
    - Verify confidence shows as percentage (e.g., "100%")
    - Verify processing time shows in ms (e.g., "59.27 ms")

- [ ] **[18.0][AC-2] Model Information Card Displays Correctly**
  - [ ] [18.1] Fetch metadata from `/v1/models/local/latest`
  - [ ] [18.2] Render all 7 fields in Model Information card
  - [ ] [18.3] Format emotion classes as readable list
  - [ ] [18.4] Write unit tests: verify card renders with all fields
  - [ ] [18.5] Write integration tests: verify metadata API call and parsing
  - [ ] [18.6] **E2E Test**:
    ```bash
    # Verify metadata endpoint returns data
    response=$(curl -s http://127.0.0.1:8000/v1/models/local/latest)
    echo "$response" | grep -q "SVM with MFCC Features" || exit 1
    echo "✅ AC-2 E2E: Metadata endpoint working, card should display"
    ```
  - [ ] [18.7] **Live Environment Verification**:
    - Navigate to Tab 3
    - Verify "Model Information" card displays
    - Verify all fields present: name, architecture, feature extraction, dimension, dataset, date, classes

- [ ] **[19.0][AC-3] Model Description Card Displays Correctly**
  - [ ] [19.1] Extract description and notes from metadata
  - [ ] [19.2] Render description card with proper formatting
  - [ ] [19.3] Handle missing description/notes gracefully
  - [ ] [19.4] Write unit tests: verify description rendering
  - [ ] [19.5] Write integration tests: verify description extraction
  - [ ] [19.6] **E2E Test**:
    ```bash
    response=$(curl -s http://127.0.0.1:8000/v1/models/local/latest)
    echo "$response" | grep -q "Support Vector Machine" || exit 1
    echo "✅ AC-3 E2E: Description available in metadata"
    ```
  - [ ] [19.7] **Live Environment Verification**:
    - Verify "Model Description" card displays
    - Verify description text matches metadata.json
    - Verify notes section displays

- [ ] **[20.0][AC-4] Processing Time with Color-Coded Progress Bar**
  - [ ] [20.1] Calculate color based on processing time value
  - [ ] [20.2] Render progress bar with correct color
  - [ ] [20.3] Display processing time value alongside bar
  - [ ] [20.4] Write unit tests: verify color logic for all ranges
  - [ ] [20.5] Write integration tests: verify progress bar renders
  - [ ] [20.6] **E2E Test**:
    ```bash
    # Test with fast processing time (<100ms)
    # Manual: Verify green color displays
    echo "✅ AC-4 E2E: Check progress bar color coding manually"
    ```
  - [ ] [20.7] **Live Environment Verification**:
    - Test with fast audio file (expect green)
    - Test with slow audio file if available (expect yellow/red)
    - Verify color matches performance category

- [ ] **[21.0][AC-5] Cards in 2-Column Grid Layout**
  - [ ] [21.1] Implement `st.columns([1, 1])` for 2-column layout
  - [ ] [21.2] Place cards in appropriate columns
  - [ ] [21.3] Verify responsive behavior on different screen widths
  - [ ] [21.4] Write unit tests: verify column structure
  - [ ] [21.5] Write integration tests: verify all cards render in correct positions
  - [ ] [21.6] **E2E Test**:
    ```bash
    # Visual verification of layout
    echo "✅ AC-5 E2E: Manually verify 2-column layout in browser"
    ```
  - [ ] [21.7] **Live Environment Verification**:
    - Open Tab 3 in browser
    - Verify 2 columns visible side-by-side
    - Verify cards distributed across columns
    - Test on narrow screen (verify stacking behavior)

- [ ] **[22.0][AC-6] Real API Calls When Not in Mock Mode**
  - [ ] [22.1] Check backend health status
  - [ ] [22.2] If backend healthy and not in mock mode, call real APIs
  - [ ] [22.3] Verify session_state contains real inference result
  - [ ] [22.4] Write unit tests: verify API call logic
  - [ ] [22.5] Write integration tests: test with real backend
  - [ ] [22.6] **E2E Test**:
    ```bash
    # Disable mock mode
    export ENABLE_MOCK_MODE=false

    # Launch Streamlit
    streamlit run frontend/streamlit_app/src/ml-app.py --server.port 8510 &
    STREAMLIT_PID=$!
    sleep 15

    # Verify backend called (check logs)
    echo "✅ AC-6 E2E: Verify real API calls in Streamlit logs"

    kill $STREAMLIT_PID
    ```
  - [ ] [22.7] **Live Environment Verification**:
    - Ensure ENABLE_MOCK_MODE=false
    - Ensure backend running at http://127.0.0.1:8000
    - Upload audio and navigate to Tab 3
    - Verify data comes from real API (check model_version matches backend)

- [ ] **[23.0][AC-7] Mock Data When Backend Unavailable**
  - [ ] [23.1] Implement backend health check
  - [ ] [23.2] If backend unavailable, use mock data
  - [ ] [23.3] Verify mock data structure matches real API
  - [ ] [23.4] Write unit tests: verify mock mode activation
  - [ ] [23.5] Write integration tests: test mock data rendering
  - [ ] [23.6] **E2E Test**:
    ```bash
    # Stop backend
    # Set mock mode
    export ENABLE_MOCK_MODE=true

    # Launch Streamlit
    streamlit run frontend/streamlit_app/src/ml-app.py --server.port 8510 &
    STREAMLIT_PID=$!
    sleep 15

    # Verify app still works
    curl -s http://localhost:8510 | grep -q "Speech Emotion Recognition" || exit 1
    echo "✅ AC-7 E2E: Mock mode allows app to run without backend"

    kill $STREAMLIT_PID
    ```
  - [ ] [23.7] **Live Environment Verification**:
    - Stop backend service
    - Enable mock mode
    - Upload audio and navigate to Tab 3
    - Verify mock data displays (emotion: happy, confidence: 95%)

- [ ] **[24.0][AC-8] Error Handling for API Failures**
  - [ ] [24.1] Simulate network error in API call
  - [ ] [24.2] Display error message to user
  - [ ] [24.3] Suggest troubleshooting steps
  - [ ] [24.4] Write unit tests: verify error message display
  - [ ] [24.5] Write integration tests: test error scenarios
  - [ ] [24.6] **E2E Test**:
    ```bash
    # Simulate backend down (wrong port)
    export ML_APP_BASE_URL=http://127.0.0.1:9999

    # Launch Streamlit
    streamlit run frontend/streamlit_app/src/ml-app.py --server.port 8510 &
    STREAMLIT_PID=$!
    sleep 15

    # Manual: Verify error message displays
    echo "✅ AC-8 E2E: Error message should display when backend unreachable"

    kill $STREAMLIT_PID
    ```
  - [ ] [24.7] **Live Environment Verification**:
    - Configure invalid backend URL
    - Attempt analysis
    - Verify error message: "Unable to fetch results. Please try again."
    - Verify suggestion to check backend connection

- [ ] **[25.0][AC-9] End-to-End Workflow Completion**
  - [ ] [25.1] Test complete workflow: upload → Tab 1 → Tab 2 → Tab 3
  - [ ] [25.2] Verify data flows correctly through all tabs
  - [ ] [25.3] Verify Tab 3 displays final results correctly
  - [ ] [25.4] Write unit tests: verify workflow state management
  - [ ] [25.5] Write integration tests: test full data flow
  - [ ] [25.6] **E2E Test**:
    ```bash
    # Full workflow test
    export ENABLE_MOCK_MODE=false

    # Start backend
    cd backend && poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    sleep 5

    # Start frontend
    cd frontend/streamlit_app/src
    streamlit run ml-app.py --server.port 8510 &
    STREAMLIT_PID=$!
    sleep 15

    # Verify both services running
    curl -s http://127.0.0.1:8000/health | grep -q "ok" || exit 1
    curl -s http://localhost:8510 | grep -q "Speech Emotion Recognition" || exit 1

    echo "✅ AC-9 E2E: Full stack running, manual workflow test required"

    kill $STREAMLIT_PID
    kill $BACKEND_PID
    ```
  - [ ] [25.7] **Live Environment Verification**:
    - Upload sample audio file: data/AudioWAV/1001_DFA_ANG_XX.wav
    - Click "Analyze Audio" on Tab 1
    - Verify Tab 2 displays features (from US-005)
    - Navigate to Tab 3
    - Verify complete results display:
      - Emotion: angry (with icon)
      - Confidence: 100%
      - Processing time: ~59ms (green bar)
      - Model info card shows SVM details
      - Description card shows model notes

---

### 5. Documentation & Deployment

- [ ] **[26.0][DOC] Code Documentation**
  - [ ] [26.1] Add docstrings to all new functions
  - [ ] [26.2] Add inline comments for complex logic
  - [ ] [26.3] Update component documentation in CLAUDE.md if needed
  - [ ] [26.4] Document API endpoint usage

- [ ] **[27.0][DOC] Testing Documentation**
  - [ ] [27.1] Document test scenarios
  - [ ] [27.2] Create testing checklist
  - [ ] [27.3] Document mock mode vs real mode behavior
  - [ ] [27.4] Add troubleshooting guide

- [ ] **[28.0][DOC] Code Quality**
  - [ ] [28.1] Run code formatter if applicable
  - [ ] [28.2] Check for unused imports
  - [ ] [28.3] Verify consistent naming conventions
  - [ ] [28.4] Review code against Streamlit best practices

---

## Implementation Notes

### File Modifications
**Primary file**: `frontend/streamlit_app/src/ml-app.py`
- Function: `stage_inference_results()` (lines 308-372) - Complete rewrite
- New helper functions:
  - `get_emotion_icon(emotion: str) -> str`
  - `get_performance_color(time_ms: float) -> str`
  - `get_mock_inference_result() -> dict`
  - `get_mock_model_metadata() -> dict`
  - `fetch_latest_model_metadata() -> dict | None`

**Secondary file**: `frontend/streamlit_app/src/mock_inference.py` (if needed)
- Update mock response structure to match real API

### Key Design Decisions
1. **Material Icons over Emoji**: Using Material Symbols Rounded for professional appearance
2. **Ant Design Cards**: Provides better visual hierarchy and organization
3. **2-Column Layout**: Balances information density with readability
4. **Progress Bar for Performance**: Visual indicator more intuitive than just numbers
5. **Separate Metadata API Call**: Ensures complete model information available

### Testing Strategy
- **Unit Tests**: Test individual functions with mocked data
- **Integration Tests**: Test API integration and data parsing
- **E2E Tests**: Test complete workflow with Docker deployment
- **Live Verification**: Manual testing with real backend and sample audio files

## Changelog
| Date | Author | Summary | Sections Affected | Reason |
|------|--------|---------|------------------|--------|
| 2025-01-30 15:30:00 | Solution Architect | Initial implementation plan creation | All sections | Created comprehensive task breakdown with 100% FR/TR/AC coverage and 4-level test coverage for all acceptance criteria |
