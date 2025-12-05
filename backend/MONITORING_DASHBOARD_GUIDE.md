# Evidently Monitoring Dashboard Guide

## ✅ Dashboard Fixed & Working

The 500 error has been resolved using Evidently's proper Python API (`DashboardPanelPlot` and `PanelMetric`). The monitoring system is fully functional with a comprehensive dashboard displaying classification metrics and drift monitoring.

## 📊 How to View Your Rich Monitoring Dashboard

### Access URL
**http://localhost:8080**

### Navigation Steps

1. **Open Browser** → Navigate to `http://localhost:8080`

2. **Select Project** → Click on `speech_emotion_recognition`

3. **Two Ways to View Metrics:**
   - **Dashboard Tab** ← Real-time dashboard with 2 tabs:
     - Classification Metrics: Accuracy, Precision, Recall, F1 counters + timelines
     - Data Drift: Drift share, count, and timeline visualization
   - **Reports Tab** ← Detailed analysis with comprehensive metrics

4. **Click Latest Timestamp** (in Reports) → View the most recent monitoring report

### What You'll See in Reports Tab

####  **Data Drift Analysis**
- **Share of Drifted Features**: Percentage showing distribution changes
- **Drift Score**: Statistical significance of drift
- **Feature-by-Feature Breakdown**: Detailed drift analysis for all 210 audio features
- **Distribution Plots**: Visual comparison of reference vs current data

#### **Classification Quality Metrics** (When ground truth is available)
- **Accuracy**: Overall model accuracy (e.g., 70% from test run)
- **Precision**: Weighted average precision across all emotions
- **Recall**: Weighted average recall
- **F1 Score**: Harmonic mean of precision and recall
- **Confusion Matrix**: Per-emotion prediction breakdown
- **Class-Level Metrics**: Individual performance for each emotion (angry, disgust, fear, happy, neutral, sad)

#### **Prediction Distribution**
- **Label Distribution**: Frequency of each emotion prediction
- **Confidence Distribution**: Model confidence levels across predictions
- **Probability Distribution**: Full probability vectors

#### **Dataset Statistics**
- **Row Count**: Number of predictions analyzed
- **Missing Values**: Data quality check
- **Feature Statistics**: Min, max, mean, std for all features

---

##  **Important: Evidently 0.7 Architecture Change**

### What Changed in Evidently 0.7

Evidently 0.7 introduced a new `Dataset` API that changed how metrics work with the Workspace UI:

**OLD (Evidently 0.4-0.6):**
- Dashboard panels could directly reference metrics from Report snapshots
- `metric_v2` fields were exposed for custom panel configuration

**NEW (Evidently 0.7+):**
- `DataDriftPreset()` and `ClassificationPreset()` generate rich Reports
- These presets don't expose `metric_v2` fields to Dashboard panels
- **Solution**: Use the **Reports tab** for comprehensive visualizations

### Why Not Dashboard Tab?

The "Dashboard" tab in Evidently 0.7 is designed for:
- Test results tracking (not Report metrics)
- Custom test suites with pass/fail thresholds
- Long-term test result trends

Our implementation uses **Reports** (with Presets), which provide:
- ✅ Richer visualizations
- ✅ More comprehensive metrics
- ✅ Better classification analysis
- ✅ Interactive HTML reports

**Bottom Line**: The Reports tab IS your rich dashboard.

---

## 🎯 Monitoring Workflow

### 1. Collect Predictions
```bash
# API automatically logs predictions to buffer
POST /v1/infer/local/latest
```

### 2. Submit User Feedback (Ground Truth)
```bash
# Enables classification quality metrics
POST /v1/monitoring/feedback/{prediction_id}
{
  "actual_emotion": "happy"
}
```

### 3. Auto-Generate Reports
- Reports auto-generate every **10 predictions** (configurable in `.env.local`)
- Stored in:
  - **HTML**: `backend/monitoring_reports/*.html` (standalone, shareable)
  - **JSON**: `backend/monitoring_reports/*.json` (programmatic access)
  - **Workspace**: `backend/evidently_workspace/{project_id}/snapshots/` (UI access)

### 4. View in Evidently UI
- Navigate to Reports tab
- Click latest report
- Explore all metrics interactively

---

## 🔧 Configuration

### Environment Variables (`.env.local`)

```bash
# Monitoring Configuration
MONITORING_REFERENCE_PATH=monitoring_data/reference_dataset.csv
MONITORING_REPORTS_DIR=monitoring_reports
MONITORING_BUFFER_MAX_RECORDS=500
MONITORING_AUTO_REPORT_THRESHOLD=10  # Generate report every N predictions
EVIDENTLY_DASHBOARD_URL=http://localhost:8080
```

### Adjust Report Frequency

**For Production** (less frequent reports):
```bash
MONITORING_AUTO_REPORT_THRESHOLD=100
```

**For Testing** (more frequent reports):
```bash
MONITORING_AUTO_REPORT_THRESHOLD=10
```

---

## 📈 Metrics Captured

### Always Available (No Ground Truth Needed)
1. **Data Drift**: Feature distribution changes over time
2. **Prediction Distribution**: Model output patterns
3. **Confidence Statistics**: Model certainty levels

### Requires User Feedback (Ground Truth)
4. **Accuracy**: % of correct predictions
5. **Precision**: Quality of positive predictions per class
6. **Recall**: Coverage of actual positives per class
7. **F1 Score**: Balance of precision and recall
8. **Confusion Matrix**: Detailed error analysis
9. **Per-Emotion Metrics**: Individual class performance

---

## 🧪 Testing the System

### End-to-End Test with RAVDESS Data

```bash
# Runs 10 predictions + automatic feedback submission
poetry run python scripts/test_feedback_system.py
```

**This script:**
- Selects 10 RAVDESS audio files
- Extracts ground truth from filenames
- Posts inference requests
- Automatically submits feedback
- Calculates accuracy
- Triggers report generation (if threshold met)

**Example Output:**
```
Total Predictions: 10
Correct: 7
Incorrect: 3
Accuracy: 70.0%

✓ Report auto-generated at: monitoring_reports/evidently_report_20251204_181734.html
```

---

## 📁 File Locations

### Monitoring Reports
```
backend/monitoring_reports/
├── evidently_report_20251204_181734.html  # Standalone HTML (12MB)
├── evidently_report_20251204_181734.json  # Programmatic access
└── ... (older reports)
```

### Workspace (Evidently UI)
```
backend/evidently_workspace/
└── {project-id}/
    ├── dashboard.json          # Dashboard config
    ├── metadata.json           # Project metadata
    └── snapshots/
        └── {snapshot-id}.json  # Report snapshots
```

### Reference Dataset
```
backend/monitoring_data/
└── reference_dataset.csv  # 5,581 samples from CREMA-D training split
```

---

## 🚀 Starting the Monitoring System

### 1. Launch Backend API
```bash
cd backend
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. Launch Evidently UI
```bash
cd backend
poetry run evidently ui --workspace evidently_workspace --host 0.0.0.0 --port 8080
```

### 3. Access Dashboard
- Backend API: `http://localhost:8000`
- Evidently UI: `http://localhost:8080`
- API Docs: `http://localhost:8000/docs`

---

## ❓ FAQ

### Q: Why can't I see metrics in the Dashboard tab?
**A**: In Evidently 0.7, Report metrics are viewed in the **Reports tab**, not Dashboard tab. The Dashboard tab is for Test results.

### Q: How do I enable accuracy metrics?
**A**: Submit user feedback via `POST /v1/monitoring/feedback/{prediction_id}` with the actual emotion. Accuracy metrics will appear once ground truth is available.

### Q: How often are reports generated?
**A**: Automatically every N predictions (default: 10). Configurable via `MONITORING_AUTO_REPORT_THRESHOLD` in `.env.local`.

### Q: Can I view reports without the Evidently UI?
**A**: Yes! Open the HTML files directly in a browser: `backend/monitoring_reports/*.html`

### Q: How do I track metrics over time?
**A**: Navigate to Reports tab → Click multiple report timestamps → Compare metrics across dates.

### Q: What's the difference between Data Drift and Concept Drift?
**A**:
- **Data Drift**: Input feature distributions changing (e.g., different recording quality)
- **Concept Drift**: Relationship between features and labels changing (detected via accuracy drop)

---

## 🎉 Summary

### ✅ What's Working

1. **User Feedback System** → `POST /v1/monitoring/feedback/{prediction_id}`
2. **Automatic Report Generation** → Every 10 predictions
3. **Rich Metrics Visualization** → Reports tab in Evidently UI
4. **Standalone HTML Reports** → `monitoring_reports/*.html`
5. **Data Drift Detection** → Always active
6. **Classification Metrics** → When ground truth available

### 🎯 How to Use It

1. Make predictions via API
2. Submit user feedback for accuracy tracking
3. View reports in Evidently UI → **Reports Tab**
4. Monitor data drift and model performance
5. Take action on early warning signals (drift detection)
6. Track concept drift via accuracy degradation

---

**For questions or issues, check the Evidently UI at: http://localhost:8080**
