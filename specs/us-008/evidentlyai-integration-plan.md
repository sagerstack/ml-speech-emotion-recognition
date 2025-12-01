# EvidentlyAI Integration Plan - Local Model Monitoring

## Overview

Integrate EvidentlyAI into the local model inference pipeline (inference_local.py) to provide comprehensive ML monitoring including confusion matrices, performance metrics, data drift, concept drift, and label drift detection.

**Constraints:**
- In-memory storage only (no PostgreSQL)
- User has reference dataset ready
- Focus on local model inference (no SageMaker)
- Streamlit dashboard for visualization

---

## Architecture

### Data Flow

```
Audio Upload → inference_local.py
    ↓
Extract Features (MFCC, chroma, spectral)
    ↓
Model Prediction
    ↓
Log to In-Memory Buffer (with features + prediction + actual label)
    ↓
Every N predictions → Trigger EvidentlyAI Report Generation
    ↓
Compare Current Buffer vs Reference Dataset
    ↓
Generate Reports (Performance, Data Drift, Target Drift)
    ↓
Save Reports to monitoring_reports/ directory
    ↓
Export Key Metrics to Prometheus
    ↓
Streamlit Dashboard fetches reports via API
```

### Component Separation

**Backend (FastAPI):**
- Prediction logging service (in-memory buffer)
- EvidentlyAI monitoring service
- Report generation logic
- Monitoring API endpoints
- Prometheus metrics export

**Frontend (Streamlit):**
- New monitoring page
- Fetch data from backend API
- Display confusion matrix
- Show drift alerts
- Render performance charts
- Embed HTML reports (optional)

---

## Implementation Phases

### Phase 1: Backend Foundation

**1.1 Install Dependencies**
- Add to backend/pyproject.toml:
  - `evidently = "^0.4.22"`
  - No database dependencies needed (in-memory only)

**1.2 Create Monitoring Service**
- New file: `backend/app/services/evidently_monitoring.py`
- Responsibilities:
  - Load reference dataset (CSV/parquet)
  - Define column mapping for audio features
  - Generate performance reports (confusion matrix, accuracy, precision, recall, F1)
  - Generate data drift reports
  - Generate target drift reports
  - Save reports to `backend/monitoring_reports/` directory

**1.3 Create Prediction Buffer**
- New file: `backend/app/services/prediction_buffer.py`
- In-memory circular buffer (collections.deque with maxlen)
- Store: timestamp, features, predicted_emotion, confidence, actual_emotion (if available)
- Thread-safe operations
- Convert to pandas DataFrame for EvidentlyAI

**1.4 Column Mapping Strategy**
- Define feature columns based on model version:
  - v1: 162 features (zcr, chroma_0-11, mfcc_0-19, rms, mel_0-127)
  - v2: 78 features (mfcc_mean_0-12, mfcc_std_0-12, delta_mean_0-12, delta_std_0-12, delta2_mean_0-12, delta2_std_0-12)
- Target column: "emotion"
- Prediction column: "predicted_emotion"

### Phase 2: Integration with Inference Endpoints

**2.1 Modify inference_local.py**
- Import prediction buffer service
- After each successful prediction:
  - Extract features from the prediction flow
  - Log to buffer: features + prediction + metadata
  - Check buffer size threshold
  - If threshold met (e.g., every 100 predictions) → trigger background monitoring task

**2.2 Background Monitoring Task**
- Use FastAPI BackgroundTasks
- Create task function: `generate_monitoring_reports()`
- Runs EvidentlyAI monitoring service
- Non-blocking (doesn't impact prediction latency)

**2.3 Reference Dataset Integration**
- Load reference dataset on service initialization
- Expected format: CSV with feature columns + "emotion" label column
- Store in monitoring service singleton

### Phase 3: Monitoring API Endpoints

**3.1 Create New Router**
- New file: `backend/app/api/v1/endpoints/monitoring.py`
- Endpoints to create:
  - `GET /v1/monitoring/summary` - Latest metrics summary (JSON)
  - `GET /v1/monitoring/reports` - List all generated reports
  - `GET /v1/monitoring/reports/{report_name}` - Serve HTML/JSON report
  - `POST /v1/monitoring/generate` - Manually trigger report generation
  - `GET /v1/monitoring/buffer/stats` - Current buffer statistics

**3.2 Register Router**
- Add to `backend/app/api/v1/__init__.py`
- Include monitoring router in API routes

### Phase 4: Prometheus Metrics Export

**4.1 EvidentlyAI → Prometheus Bridge**
- New file: `backend/app/services/evidently_prometheus.py`
- Parse Evidently JSON reports
- Update Prometheus gauges:
  - `model_accuracy`
  - `model_precision`
  - `model_recall`
  - `model_f1_score`
  - `drift_detected` (boolean: 0 or 1)
  - `drifted_features_count`
  - `data_drift_score` (per feature)

**4.2 Integration**
- Call after report generation
- Metrics exposed via existing `/metrics` endpoint
- Visible in Grafana dashboards

### Phase 5: Streamlit Dashboard

**5.1 Create Monitoring Page**
- New file: `frontend/streamlit_app/pages/monitoring.py`
- Page title: "🔍 ML Model Monitoring"

**5.2 Dashboard Layout**
- **Header Metrics Row:**
  - Model Health status
  - Drift detection alert
  - Last check timestamp

- **Tabs:**
  - Tab 1: Performance Metrics
    - Confusion matrix heatmap
    - Per-emotion metrics table
    - Accuracy/Precision/Recall/F1 gauges

  - Tab 2: Data Drift
    - Drift detection status
    - List of drifted features
    - Feature drift scores chart

  - Tab 3: Concept Drift
    - Prediction distribution comparison
    - Confidence score distribution

  - Tab 4: Reports
    - List of generated reports
    - Download/view buttons

**5.3 Data Fetching**
- Use `requests` library to call backend API
- Fetch monitoring summary on page load
- Auto-refresh option (every N seconds)
- Error handling for API failures

**5.4 Visualizations**
- Confusion matrix: plotly heatmap
- Drift scores: plotly bar chart
- Performance metrics: streamlit_shadcn_ui metric cards
- Alerts: streamlit_shadcn_ui alert components

### Phase 6: Report Generation Strategy

**6.1 Triggering Mechanism**
- **Automatic**: Every 100 predictions (configurable)
- **Manual**: Via Streamlit button → API call
- **Scheduled**: Optional CronJob (for production)

**6.2 Report Types**
- **Performance Report**:
  - Metrics: ClassificationQualityMetric, ClassificationConfusionMatrix
  - Saved as: `performance_YYYYMMDD_HHMMSS.html/json`

- **Data Drift Report**:
  - Metrics: DataDriftPreset, DataDriftTable, DatasetDriftMetric
  - Saved as: `data_drift_YYYYMMDD_HHMMSS.html/json`

- **Target Drift Report**:
  - Metrics: TargetDriftPreset
  - Saved as: `target_drift_YYYYMMDD_HHMMSS.html/json`

**6.3 Report Storage**
- Directory: `backend/monitoring_reports/`
- File retention: Keep last 50 reports (configurable)
- Old reports auto-deleted on new generation

---

## File Structure

### New Files to Create

```
backend/
├── app/
│   ├── services/
│   │   ├── evidently_monitoring.py       # Core EvidentlyAI service
│   │   ├── prediction_buffer.py          # In-memory buffer
│   │   └── evidently_prometheus.py       # Prometheus metrics bridge
│   └── api/v1/endpoints/
│       └── monitoring.py                 # Monitoring API endpoints
├── monitoring_reports/                   # Generated reports directory
│   └── .gitkeep
└── data/
    └── reference_dataset.csv             # User-provided reference data

frontend/
└── streamlit_app/
    └── pages/
        └── monitoring.py                 # Streamlit monitoring page
```

### Files to Modify

```
backend/
├── app/
│   ├── api/v1/
│   │   └── __init__.py                   # Register monitoring router
│   └── api/v1/endpoints/
│       └── inference_local.py            # Add prediction logging
└── pyproject.toml                        # Add evidently dependency

frontend/
└── streamlit_app/
    └── app.py (or main file)             # Add monitoring page to navigation
```

---

## Critical Integration Points

### 1. Feature Extraction Integration
- Current: Features extracted in `model_registry.py` → `feature_extractor(audio_bytes)`
- Integration: Capture extracted features BEFORE prediction
- Store in buffer alongside prediction result
- Challenge: Feature extractors differ per model version
- Solution: Store features with model version metadata

### 2. Reference Dataset Format
- Must match feature structure from inference
- Columns: All feature columns + "emotion" (ground truth)
- Model v1: 162 feature columns + 1 emotion column
- Model v2: 78 feature columns + 1 emotion column
- Recommendation: Create separate reference datasets per model version

### 3. Buffer Size Management
- Max buffer size: 1000 predictions (configurable)
- Memory usage: ~1000 rows × 162 features × 8 bytes = ~1.3 MB (acceptable)
- Circular buffer with automatic eviction

### 4. Actual Labels (Ground Truth)
- Initial deployment: No actual labels available
- Prediction buffer stores: predicted_emotion, confidence
- Future: Add feedback mechanism for users to correct predictions
- EvidentlyAI: Can work without actual labels (drift detection only)
- With labels: Enables confusion matrix and performance metrics

### 5. Thread Safety
- FastAPI is async but runs in single process
- Buffer operations must be thread-safe (use threading.Lock)
- Background tasks run in thread pool
- Recommendation: Use `asyncio.Lock` for async safety

---

## Configuration

### Environment Variables (Optional)
```
MONITORING_BUFFER_SIZE=1000
MONITORING_REPORT_TRIGGER=100
MONITORING_REPORTS_DIR=monitoring_reports
MONITORING_MAX_REPORTS=50
REFERENCE_DATASET_PATH=data/reference_dataset.csv
```

### Monitoring Service Config
- Drift detection threshold: 0.15 (15% for data drift)
- Minimum predictions for report: 50
- Report generation frequency: Every 100 predictions

---

## Testing Strategy

### Unit Tests
- Test prediction buffer operations (add, get, clear)
- Test monitoring service initialization
- Test report generation with sample data
- Test Prometheus metrics export

### Integration Tests
- End-to-end: Upload audio → prediction → buffer logging
- API endpoints: Test monitoring endpoints return valid data
- Report generation: Test with sample prediction data

### Manual Testing
- Upload 100+ audio files through Streamlit
- Verify buffer fills correctly
- Check report generation triggers
- Validate Streamlit dashboard displays data
- Confirm Prometheus metrics updated

---

## Deployment Considerations

### Docker
- No changes to Dockerfile needed (poetry install handles dependencies)
- Mount `monitoring_reports/` as volume for report persistence
- Reference dataset should be in Docker image or mounted volume

### Kubernetes
- ConfigMap for reference dataset
- Persistent volume for monitoring_reports (optional)
- No database needed (in-memory only)

### Performance Impact
- Prediction logging: < 1ms overhead
- Background report generation: Non-blocking
- Memory usage: ~1-2 MB for buffer
- CPU impact: Minimal (reports generated async)

---

## Migration Path

### Step 1: Backend Setup (Week 1)
1. Install evidently dependency
2. Create monitoring service
3. Create prediction buffer
4. Test with sample data

### Step 2: Inference Integration (Week 1-2)
1. Modify inference_local.py
2. Add prediction logging
3. Add background task trigger
4. Test prediction flow

### Step 3: API Endpoints (Week 2)
1. Create monitoring router
2. Implement endpoints
3. Test API responses

### Step 4: Prometheus Export (Week 2)
1. Create metrics bridge
2. Export to Prometheus
3. Update Grafana dashboards

### Step 5: Streamlit Dashboard (Week 3)
1. Create monitoring page
2. Implement visualizations
3. Connect to backend API
4. User acceptance testing

---

## Critical Files Reference

**Must Read Before Implementation:**
1. `backend/app/services/model_registry.py` - Understand feature extraction flow
2. `backend/app/api/v1/endpoints/inference_local.py` - Current inference endpoints
3. `backend/app/main.py` - Prometheus middleware setup
4. `frontend/streamlit_app/pages/` - Existing page structure

**Dependencies:**
- Model v1 feature extractor: `backend/models/v1/feature_extractor.py`
- Model v2 feature extractor: `backend/models/v2/feature_extractor.py`
- Audio service: `backend/app/services/audio_service.py`

---

## Key Decisions & Rationale

### Why In-Memory Buffer?
- Minimal overhead (no database setup)
- Fast access for recent predictions
- Suitable for monitoring use case (don't need full history)
- Easy to implement and maintain

### Why Background Tasks?
- Don't block prediction requests
- Report generation can be slow (statistical computations)
- User gets instant prediction response

### Why Separate Monitoring Router?
- Clean separation of concerns
- Easy to secure/disable monitoring endpoints
- Clear API structure

### Why Streamlit Page vs Standalone HTML?
- User preference: integrated monitoring experience
- Easier navigation (single app)
- Can add interactive controls
- Consistent with existing app architecture

---

## Success Criteria

✅ **Backend:**
- Predictions logged to buffer successfully
- Reports generated every 100 predictions
- API endpoints return valid monitoring data
- Prometheus metrics exported correctly

✅ **Frontend:**
- Monitoring page accessible in Streamlit
- Confusion matrix displayed correctly
- Drift alerts shown when detected
- Performance metrics updated in real-time

✅ **Monitoring Quality:**
- Confusion matrix matches actual model performance
- Data drift detected when feature distributions change
- No false positive drift alerts
- Reports provide actionable insights

---

## Risks & Mitigations

**Risk 1: Buffer Memory Growth**
- Mitigation: Use circular buffer with maxlen
- Monitor: Add buffer size metric to Prometheus

**Risk 2: Reference Dataset Mismatch**
- Mitigation: Validate reference dataset on service init
- Check: Feature columns match model expectations

**Risk 3: Report Generation Blocking**
- Mitigation: Use BackgroundTasks for async execution
- Monitor: Track report generation time metric

**Risk 4: Model Version Switching**
- Mitigation: Store model version with each prediction
- Solution: Separate buffers per model version (if needed)

---

## Future Enhancements

1. **User Feedback Loop**: Allow users to correct predictions → update actual labels
2. **Alert System**: Email/Slack notifications on drift detection
3. **Historical Analysis**: Export buffer to CSV periodically
4. **Multi-Model Comparison**: Compare drift across model versions
5. **Custom Drift Thresholds**: Per-feature drift sensitivity configuration
