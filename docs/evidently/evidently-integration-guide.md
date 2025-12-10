# EvidentlyAI Integration Guide

## Executive Summary

This document provides a comprehensive review of EvidentlyAI and detailed integration strategies for the ML Speech Emotion Recognition application. EvidentlyAI will complement the existing Prometheus/Grafana monitoring stack by adding ML-specific monitoring capabilities.

**Key Integration Points:**
- Confusion matrix visualization
- Model performance monitoring (accuracy, precision, recall, F1-score)
- Data drift detection (input feature drift)
- Concept drift detection (prediction distribution changes)
- Label drift monitoring (ground truth changes over time)

---

## 1. EvidentlyAI Overview

### What is EvidentlyAI?

EvidentlyAI is an open-source Python library designed specifically for ML model monitoring and observability. It provides 100+ built-in metrics and tests for evaluating, testing, and monitoring ML systems from development to production.

### Core Capabilities

#### 1.1 Model Performance Monitoring
- **Classification Metrics**: Accuracy, precision, recall, F1-score, ROC-AUC
- **Confusion Matrix**: Detailed classification performance breakdown
- **Class-level Performance**: Per-emotion metrics (Happy, Sad, Angry, etc.)
- **Performance Degradation**: Track model quality over time

#### 1.2 Data Drift Detection
- **Feature Drift**: Detect changes in audio feature distributions (MFCCs, spectrograms, etc.)
- **Statistical Tests**: Multiple drift detection algorithms (Kolmogorov-Smirnov, Jensen-Shannon, etc.)
- **Drift Scores**: Quantitative drift measurements
- **Visual Reports**: Rich visualizations for drift analysis

#### 1.3 Concept Drift Detection
- **Prediction Drift**: Monitor changes in prediction distributions
- **Model Confidence**: Track prediction confidence over time
- **Behavioral Changes**: Detect when model behavior changes unexpectedly

#### 1.4 Label Drift Detection
- **Target Distribution**: Monitor ground truth label changes
- **Class Imbalance**: Track emotion class distribution shifts
- **Feedback Loop**: Monitor user corrections and annotations

#### 1.5 Data Quality Monitoring
- **Missing Values**: Track nulls and incomplete audio features
- **Range Violations**: Detect out-of-range feature values
- **Duplicates**: Identify duplicate predictions
- **Special Values**: Monitor NaN, infinity, and other edge cases

### Key Features for Audio Emotion Recognition

1. **Tabular Data Support**: Perfect for monitoring extracted audio features (MFCCs, chroma, spectral features)
2. **Classification Focus**: Built-in support for multi-class classification (6 emotions in CREMA-D)
3. **Production Ready**: Designed for continuous monitoring in production environments
4. **Integration Friendly**: Works with FastAPI, Prometheus, and existing MLOps tools
5. **Real-time & Batch**: Supports both streaming and batch monitoring

---

## 2. Architecture Integration

### 2.1 Current Architecture

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│  Streamlit  │─────▶│    FastAPI   │─────▶│  SageMaker   │
│   Frontend  │      │    Backend   │      │    Model     │
└─────────────┘      └──────────────┘      └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Prometheus  │
                     │   Metrics    │
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Grafana    │
                     │  Dashboards  │
                     └──────────────┘
```

### 2.2 Enhanced Architecture with EvidentlyAI

```
┌─────────────┐      ┌──────────────┐      ┌──────────────┐
│  Streamlit  │─────▶│    FastAPI   │─────▶│  SageMaker   │
│   Frontend  │      │    Backend   │      │    Model     │
└─────────────┘      └──────────────┘      └──────────────┘
                            │
                            ├─────────────┐
                            │             │
                            ▼             ▼
                     ┌──────────────┐   ┌──────────────┐
                     │  Prometheus  │   │ EvidentlyAI  │
                     │   Metrics    │   │  Monitoring  │
                     └──────────────┘   └──────────────┘
                            │             │
                            │             ├──▶ PostgreSQL
                            │             │    (Metrics DB)
                            │             │
                            │             ├──▶ HTML Reports
                            │             │
                            │             └──▶ JSON Reports
                            │
                            ▼
                     ┌──────────────┐
                     │   Grafana    │
                     │  Dashboards  │
                     └──────────────┘
```

### 2.3 Data Flow

1. **Prediction Request** → FastAPI receives audio file
2. **Feature Extraction** → Extract audio features (MFCCs, chroma, spectral)
3. **Model Prediction** → SageMaker returns emotion prediction
4. **Dual Logging**:
   - **Prometheus**: System metrics (latency, requests, errors)
   - **EvidentlyAI**: ML metrics (predictions, features, confidence)
5. **Periodic Analysis**:
   - **Reference Dataset**: Initial validation data
   - **Current Dataset**: Recent production predictions
   - **Drift Detection**: Compare distributions
   - **Report Generation**: Create monitoring reports

---

## 3. Implementation Strategy

### 3.1 Phase 1: Foundation Setup

#### Install Dependencies

Add to `backend/pyproject.toml`:

```toml
[tool.poetry.dependencies]
# Existing dependencies...
evidently = "^0.4.22"  # Latest stable version
psycopg2-binary = "^2.9.9"  # For PostgreSQL storage (optional)
```

#### Database Schema (Optional but Recommended)

For production-grade monitoring with historical tracking:

```sql
-- Create monitoring database
CREATE DATABASE ml_monitoring;

-- Create tables for Evidently data
CREATE TABLE prediction_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    audio_filename VARCHAR(255),
    predicted_emotion VARCHAR(50),
    confidence FLOAT,
    features JSONB,  -- Store MFCC, chroma, etc.
    model_version VARCHAR(50),
    inference_time_ms FLOAT,
    actual_emotion VARCHAR(50),  -- For labeled feedback
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE drift_reports (
    id SERIAL PRIMARY KEY,
    report_timestamp TIMESTAMP NOT NULL,
    report_type VARCHAR(50),  -- 'data_drift', 'model_performance', etc.
    metrics JSONB,
    drift_detected BOOLEAN,
    report_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_prediction_logs_timestamp ON prediction_logs(timestamp);
CREATE INDEX idx_prediction_logs_emotion ON prediction_logs(predicted_emotion);
CREATE INDEX idx_drift_reports_timestamp ON drift_reports(report_timestamp);
```

### 3.2 Phase 2: Monitoring Service

Create `backend/app/services/monitoring.py`:

```python
"""
EvidentlyAI Monitoring Service for ML Model Observability
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd
from evidently import ColumnMapping
from evidently.metric_preset import (
    ClassificationPreset,
    DataDriftPreset,
    TargetDriftPreset,
)
from evidently.report import Report
from evidently.test_suite import TestSuite
from evidently.tests import (
    TestAccuracyScore,
    TestPrecisionScore,
    TestRecallScore,
    TestF1Score,
    TestNumberOfDriftedColumns,
)
from evidently.metrics import (
    ClassificationQualityMetric,
    ClassificationConfusionMatrix,
    ClassificationClassBalance,
    DataDriftTable,
    DatasetDriftMetric,
)

from app.utils.logging import get_logger

logger = get_logger(__name__)


class MonitoringService:
    """Service for ML model monitoring using EvidentlyAI"""

    def __init__(
        self,
        reference_data_path: Optional[str] = None,
        reports_dir: str = "monitoring_reports",
    ):
        """
        Initialize monitoring service

        Args:
            reference_data_path: Path to reference dataset (validation data)
            reports_dir: Directory to save monitoring reports
        """
        self.reference_data_path = reference_data_path
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Load reference data if provided
        self.reference_data: Optional[pd.DataFrame] = None
        if reference_data_path:
            self.reference_data = self._load_reference_data(reference_data_path)

        # Define column mapping for CREMA-D emotion classification
        self.column_mapping = ColumnMapping(
            target="emotion",
            prediction="predicted_emotion",
            numerical_features=[
                # MFCC features (20 coefficients)
                *[f"mfcc_{i}" for i in range(20)],
                # Chroma features (12 coefficients)
                *[f"chroma_{i}" for i in range(12)],
                # Spectral features
                "spectral_centroid",
                "spectral_rolloff",
                "zero_crossing_rate",
                "rms_energy",
            ],
            categorical_features=["series_code"],  # DFA, IEO, ITS, etc.
        )

        # Emotion classes from CREMA-D
        self.emotion_classes = ["ANG", "DIS", "FEA", "HAP", "NEU", "SAD"]

    def _load_reference_data(self, path: str) -> pd.DataFrame:
        """Load reference dataset for drift comparison"""
        try:
            df = pd.read_csv(path)
            logger.info(f"Loaded reference data: {len(df)} samples")
            return df
        except Exception as e:
            logger.error(f"Failed to load reference data: {e}")
            raise

    def generate_model_performance_report(
        self,
        current_data: pd.DataFrame,
        report_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive model performance report with confusion matrix

        Args:
            current_data: DataFrame with predictions and actual labels
            report_name: Optional custom report name

        Returns:
            Dictionary with report metrics and file path
        """
        if report_name is None:
            report_name = f"performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            # Create performance report
            report = Report(
                metrics=[
                    ClassificationQualityMetric(),
                    ClassificationConfusionMatrix(),
                    ClassificationClassBalance(),
                ]
            )

            # Generate report
            report.run(
                reference_data=self.reference_data,
                current_data=current_data,
                column_mapping=self.column_mapping,
            )

            # Save HTML report
            html_path = self.reports_dir / f"{report_name}.html"
            report.save_html(str(html_path))

            # Extract metrics as JSON
            json_path = self.reports_dir / f"{report_name}.json"
            report.save_json(str(json_path))

            # Parse metrics
            with open(json_path, "r") as f:
                metrics_data = json.load(f)

            logger.info(f"Generated performance report: {html_path}")

            return {
                "report_name": report_name,
                "html_path": str(html_path),
                "json_path": str(json_path),
                "metrics": metrics_data,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}")
            raise

    def generate_data_drift_report(
        self,
        current_data: pd.DataFrame,
        report_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect data drift in audio features

        Args:
            current_data: DataFrame with recent predictions
            report_name: Optional custom report name

        Returns:
            Dictionary with drift detection results
        """
        if self.reference_data is None:
            raise ValueError("Reference data not loaded. Cannot detect drift.")

        if report_name is None:
            report_name = f"data_drift_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            # Create drift report
            report = Report(
                metrics=[
                    DataDriftPreset(),
                    DataDriftTable(),
                    DatasetDriftMetric(),
                ]
            )

            # Generate report
            report.run(
                reference_data=self.reference_data,
                current_data=current_data,
                column_mapping=self.column_mapping,
            )

            # Save reports
            html_path = self.reports_dir / f"{report_name}.html"
            report.save_html(str(html_path))

            json_path = self.reports_dir / f"{report_name}.json"
            report.save_json(str(json_path))

            # Parse drift metrics
            with open(json_path, "r") as f:
                drift_data = json.load(f)

            logger.info(f"Generated data drift report: {html_path}")

            return {
                "report_name": report_name,
                "html_path": str(html_path),
                "json_path": str(json_path),
                "drift_detected": drift_data.get("metrics", [{}])[0].get(
                    "result", {}
                ).get("dataset_drift", False),
                "drifted_features": self._extract_drifted_features(drift_data),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to generate drift report: {e}")
            raise

    def generate_target_drift_report(
        self,
        current_data: pd.DataFrame,
        report_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect concept drift and label drift

        Args:
            current_data: DataFrame with predictions
            report_name: Optional custom report name

        Returns:
            Dictionary with target drift results
        """
        if self.reference_data is None:
            raise ValueError("Reference data not loaded. Cannot detect drift.")

        if report_name is None:
            report_name = f"target_drift_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            # Create target drift report
            report = Report(metrics=[TargetDriftPreset()])

            # Generate report
            report.run(
                reference_data=self.reference_data,
                current_data=current_data,
                column_mapping=self.column_mapping,
            )

            # Save reports
            html_path = self.reports_dir / f"{report_name}.html"
            report.save_html(str(html_path))

            json_path = self.reports_dir / f"{report_name}.json"
            report.save_json(str(json_path))

            logger.info(f"Generated target drift report: {html_path}")

            return {
                "report_name": report_name,
                "html_path": str(html_path),
                "json_path": str(json_path),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to generate target drift report: {e}")
            raise

    def run_model_tests(
        self,
        current_data: pd.DataFrame,
        min_accuracy: float = 0.85,
        min_precision: float = 0.80,
        min_recall: float = 0.80,
        min_f1: float = 0.80,
        max_drifted_features: int = 5,
    ) -> Dict[str, Any]:
        """
        Run test suite to validate model performance and data quality

        Args:
            current_data: DataFrame with predictions and labels
            min_accuracy: Minimum acceptable accuracy
            min_precision: Minimum acceptable precision
            min_recall: Minimum acceptable recall
            min_f1: Minimum acceptable F1-score
            max_drifted_features: Maximum acceptable drifted features

        Returns:
            Dictionary with test results
        """
        try:
            # Create test suite
            test_suite = TestSuite(
                tests=[
                    TestAccuracyScore(gte=min_accuracy),
                    TestPrecisionScore(gte=min_precision),
                    TestRecallScore(gte=min_recall),
                    TestF1Score(gte=min_f1),
                    TestNumberOfDriftedColumns(lte=max_drifted_features),
                ]
            )

            # Run tests
            test_suite.run(
                reference_data=self.reference_data,
                current_data=current_data,
                column_mapping=self.column_mapping,
            )

            # Save test results
            test_name = f"tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            html_path = self.reports_dir / f"{test_name}.html"
            test_suite.save_html(str(html_path))

            json_path = self.reports_dir / f"{test_name}.json"
            test_suite.save_json(str(json_path))

            # Parse test results
            with open(json_path, "r") as f:
                test_data = json.load(f)

            all_tests_passed = all(
                test["status"] == "SUCCESS"
                for test in test_data.get("tests", [])
            )

            logger.info(f"Test suite completed. All passed: {all_tests_passed}")

            return {
                "test_name": test_name,
                "html_path": str(html_path),
                "json_path": str(json_path),
                "all_passed": all_tests_passed,
                "test_results": test_data.get("tests", []),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to run model tests: {e}")
            raise

    def _extract_drifted_features(self, drift_data: Dict[str, Any]) -> List[str]:
        """Extract list of features that have drifted"""
        drifted = []
        try:
            metrics = drift_data.get("metrics", [])
            for metric in metrics:
                if "result" in metric and "drift_by_columns" in metric["result"]:
                    drift_by_columns = metric["result"]["drift_by_columns"]
                    for col, drift_info in drift_by_columns.items():
                        if drift_info.get("drift_detected", False):
                            drifted.append(col)
        except Exception as e:
            logger.warning(f"Could not extract drifted features: {e}")

        return drifted

    def create_monitoring_dashboard_data(
        self, current_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Create comprehensive monitoring data for dashboard display

        Args:
            current_data: Recent predictions DataFrame

        Returns:
            Dictionary with all monitoring metrics
        """
        results = {}

        try:
            # Generate all reports
            results["performance"] = self.generate_model_performance_report(
                current_data
            )
            results["data_drift"] = self.generate_data_drift_report(current_data)
            results["target_drift"] = self.generate_target_drift_report(current_data)
            results["tests"] = self.run_model_tests(current_data)

            # Add summary
            results["summary"] = {
                "total_predictions": len(current_data),
                "drift_detected": results["data_drift"]["drift_detected"],
                "tests_passed": results["tests"]["all_passed"],
                "timestamp": datetime.now().isoformat(),
            }

            logger.info("Created comprehensive monitoring dashboard data")

        except Exception as e:
            logger.error(f"Failed to create dashboard data: {e}")
            raise

        return results
```

### 3.3 Phase 3: FastAPI Integration

Update `backend/app/api/v1/endpoints/inference.py` to log predictions:

```python
# Add to existing inference endpoint

from app.services.monitoring import MonitoringService
from app.models.prediction_log import PredictionLog
import pandas as pd

# Initialize monitoring service
monitoring_service = MonitoringService(
    reference_data_path="data/reference_dataset.csv",
    reports_dir="monitoring_reports"
)

# In-memory storage for recent predictions (use Redis in production)
recent_predictions = []
MAX_PREDICTIONS_BUFFER = 1000


@router.post("/predict", response_model=PredictionResponse)
async def predict_emotion(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """Predict emotion from audio file with monitoring"""

    # ... existing prediction logic ...

    # Log prediction for monitoring
    prediction_log = {
        "timestamp": datetime.now(),
        "audio_filename": file.filename,
        "predicted_emotion": prediction_result["emotion"],
        "confidence": prediction_result["confidence"],
        "features": extracted_features,  # MFCC, chroma, etc.
        "model_version": "v1.0.0",
        "inference_time_ms": inference_time,
    }

    # Add to buffer
    recent_predictions.append(prediction_log)
    if len(recent_predictions) > MAX_PREDICTIONS_BUFFER:
        recent_predictions.pop(0)

    # Schedule background monitoring (every 100 predictions)
    if len(recent_predictions) % 100 == 0:
        background_tasks.add_task(run_monitoring_checks)

    return prediction_result


async def run_monitoring_checks():
    """Background task to run monitoring checks"""
    try:
        # Convert recent predictions to DataFrame
        df = pd.DataFrame(recent_predictions)

        # Run monitoring
        monitoring_results = monitoring_service.create_monitoring_dashboard_data(df)

        # Log results
        logger.info(f"Monitoring check completed: {monitoring_results['summary']}")

        # Alert if drift detected
        if monitoring_results["summary"]["drift_detected"]:
            logger.warning("⚠️ DATA DRIFT DETECTED - Review monitoring reports")
            # Send alert (email, Slack, PagerDuty, etc.)

    except Exception as e:
        logger.error(f"Monitoring check failed: {e}")
```

### 3.4 Phase 4: Add Monitoring Endpoints

Create `backend/app/api/v1/endpoints/monitoring.py`:

```python
"""
Monitoring endpoints for EvidentlyAI reports
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
from typing import Optional
import json

from app.services.monitoring import MonitoringService
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

monitoring_service = MonitoringService(
    reference_data_path="data/reference_dataset.csv",
    reports_dir="monitoring_reports"
)


@router.get("/reports")
async def list_reports():
    """List all available monitoring reports"""
    try:
        reports_dir = Path("monitoring_reports")
        html_reports = list(reports_dir.glob("*.html"))
        json_reports = list(reports_dir.glob("*.json"))

        reports = []
        for html_file in html_reports:
            report_name = html_file.stem
            json_file = reports_dir / f"{report_name}.json"

            if json_file.exists():
                with open(json_file, "r") as f:
                    metadata = json.load(f)

                reports.append({
                    "name": report_name,
                    "html_path": str(html_file),
                    "json_path": str(json_file),
                    "created_at": html_file.stat().st_mtime,
                    "type": report_name.split("_")[0],  # performance, drift, etc.
                })

        return {"reports": sorted(reports, key=lambda x: x["created_at"], reverse=True)}

    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_name}")
async def get_report(
    report_name: str,
    format: str = Query("html", regex="^(html|json)$")
):
    """Get specific monitoring report"""
    try:
        reports_dir = Path("monitoring_reports")

        if format == "html":
            file_path = reports_dir / f"{report_name}.html"
            return FileResponse(file_path, media_type="text/html")
        else:
            file_path = reports_dir / f"{report_name}.json"
            with open(file_path, "r") as f:
                data = json.load(f)
            return JSONResponse(data)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Report not found")
    except Exception as e:
        logger.error(f"Failed to get report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/summary")
async def get_monitoring_summary():
    """Get latest monitoring summary"""
    try:
        # Get latest reports
        reports_dir = Path("monitoring_reports")

        # Find latest performance report
        performance_reports = sorted(
            reports_dir.glob("performance_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        drift_reports = sorted(
            reports_dir.glob("data_drift_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        summary = {
            "latest_performance_report": None,
            "latest_drift_report": None,
            "drift_detected": False,
            "model_health": "unknown",
        }

        if performance_reports:
            with open(performance_reports[0], "r") as f:
                perf_data = json.load(f)
                summary["latest_performance_report"] = perf_data

        if drift_reports:
            with open(drift_reports[0], "r") as f:
                drift_data = json.load(f)
                summary["latest_drift_report"] = drift_data

                # Extract drift status
                metrics = drift_data.get("metrics", [])
                if metrics:
                    summary["drift_detected"] = metrics[0].get("result", {}).get(
                        "dataset_drift", False
                    )

        # Determine model health
        if summary["drift_detected"]:
            summary["model_health"] = "warning"
        else:
            summary["model_health"] = "healthy"

        return summary

    except Exception as e:
        logger.error(f"Failed to get monitoring summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitoring/generate")
async def generate_monitoring_reports():
    """Manually trigger monitoring report generation"""
    try:
        # This would use recent predictions from database
        # For now, return success
        return {
            "status": "triggered",
            "message": "Monitoring reports generation started in background"
        }

    except Exception as e:
        logger.error(f"Failed to trigger monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 4. Integration with Existing Prometheus Stack

### 4.1 Export Evidently Metrics to Prometheus

Create `backend/app/services/evidently_prometheus.py`:

```python
"""
Export EvidentlyAI metrics to Prometheus
"""
from prometheus_client import Gauge, Info
import json
from pathlib import Path

# Define Prometheus metrics for Evidently data
MODEL_ACCURACY = Gauge(
    'model_accuracy',
    'Current model accuracy score'
)

MODEL_PRECISION = Gauge(
    'model_precision',
    'Current model precision score'
)

MODEL_RECALL = Gauge(
    'model_recall',
    'Current model recall score'
)

MODEL_F1_SCORE = Gauge(
    'model_f1_score',
    'Current model F1 score'
)

DATA_DRIFT_SCORE = Gauge(
    'data_drift_score',
    'Data drift score (0-1)',
    ['feature']
)

DRIFT_DETECTED = Gauge(
    'drift_detected',
    'Boolean indicator if drift is detected (0 or 1)'
)

DRIFTED_FEATURES_COUNT = Gauge(
    'drifted_features_count',
    'Number of features with detected drift'
)


def update_prometheus_from_evidently(json_report_path: str):
    """
    Parse Evidently JSON report and update Prometheus metrics

    Args:
        json_report_path: Path to Evidently JSON report
    """
    try:
        with open(json_report_path, 'r') as f:
            report_data = json.load(f)

        # Extract metrics based on report type
        metrics = report_data.get('metrics', [])

        for metric in metrics:
            metric_type = metric.get('metric')
            result = metric.get('result', {})

            # Update model performance metrics
            if metric_type == 'ClassificationQualityMetric':
                if 'accuracy' in result:
                    MODEL_ACCURACY.set(result['accuracy'])
                if 'precision' in result:
                    MODEL_PRECISION.set(result['precision'])
                if 'recall' in result:
                    MODEL_RECALL.set(result['recall'])
                if 'f1' in result:
                    MODEL_F1_SCORE.set(result['f1'])

            # Update drift metrics
            elif metric_type == 'DatasetDriftMetric':
                drift_detected = result.get('dataset_drift', False)
                DRIFT_DETECTED.set(1 if drift_detected else 0)

                drift_by_columns = result.get('drift_by_columns', {})
                drifted_count = sum(
                    1 for col_drift in drift_by_columns.values()
                    if col_drift.get('drift_detected', False)
                )
                DRIFTED_FEATURES_COUNT.set(drifted_count)

                # Set drift score per feature
                for feature, drift_info in drift_by_columns.items():
                    drift_score = drift_info.get('drift_score', 0)
                    DATA_DRIFT_SCORE.labels(feature=feature).set(drift_score)

    except Exception as e:
        logger.error(f"Failed to update Prometheus from Evidently: {e}")
```

### 4.2 Grafana Dashboard Configuration

Add Evidently metrics to Grafana dashboards. Create `deployment/monitoring/grafana-evidently-dashboard.json`:

```json
{
  "dashboard": {
    "title": "ML Model Monitoring - EvidentlyAI",
    "panels": [
      {
        "title": "Model Accuracy Over Time",
        "targets": [
          {
            "expr": "model_accuracy",
            "legendFormat": "Accuracy"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Model Performance Metrics",
        "targets": [
          {
            "expr": "model_precision",
            "legendFormat": "Precision"
          },
          {
            "expr": "model_recall",
            "legendFormat": "Recall"
          },
          {
            "expr": "model_f1_score",
            "legendFormat": "F1-Score"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Data Drift Detection",
        "targets": [
          {
            "expr": "drift_detected",
            "legendFormat": "Drift Detected"
          }
        ],
        "type": "stat",
        "thresholds": {
          "mode": "absolute",
          "steps": [
            {"value": 0, "color": "green"},
            {"value": 1, "color": "red"}
          ]
        }
      },
      {
        "title": "Drifted Features Count",
        "targets": [
          {
            "expr": "drifted_features_count",
            "legendFormat": "Drifted Features"
          }
        ],
        "type": "gauge"
      },
      {
        "title": "Feature Drift Scores",
        "targets": [
          {
            "expr": "data_drift_score",
            "legendFormat": "{{feature}}"
          }
        ],
        "type": "heatmap"
      }
    ]
  }
}
```

---

## 5. Streamlit Dashboard Integration

### 5.1 Add Monitoring Tab to Streamlit

Create `frontend/streamlit_app/pages/monitoring.py`:

```python
"""
ML Model Monitoring Dashboard
"""
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import streamlit_shadcn_ui as ui

# Backend API URL
BACKEND_URL = "http://localhost:8000/api/v1"


def fetch_monitoring_summary():
    """Fetch monitoring summary from backend"""
    try:
        response = requests.get(f"{BACKEND_URL}/monitoring/summary")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch monitoring data: {e}")
        return None


def fetch_reports_list():
    """Fetch list of available reports"""
    try:
        response = requests.get(f"{BACKEND_URL}/monitoring/reports")
        response.raise_for_status()
        return response.json()["reports"]
    except Exception as e:
        st.error(f"Failed to fetch reports: {e}")
        return []


def main():
    st.title("🔍 ML Model Monitoring Dashboard")

    # Fetch data
    summary = fetch_monitoring_summary()

    if not summary:
        st.warning("No monitoring data available yet")
        return

    # Health status
    col1, col2, col3 = st.columns(3)

    with col1:
        health_status = summary.get("model_health", "unknown")
        health_emoji = "✅" if health_status == "healthy" else "⚠️"
        ui.metric_card(
            title="Model Health",
            value=f"{health_emoji} {health_status.upper()}",
            key="health_metric"
        )

    with col2:
        drift_detected = summary.get("drift_detected", False)
        drift_status = "🔴 DETECTED" if drift_detected else "🟢 NONE"
        ui.metric_card(
            title="Data Drift",
            value=drift_status,
            key="drift_metric"
        )

    with col3:
        ui.metric_card(
            title="Last Check",
            value="2 hours ago",
            key="last_check_metric"
        )

    # Tabs for different monitoring aspects
    tab_items = [
        {"label": "Performance", "content": "performance"},
        {"label": "Data Drift", "content": "drift"},
        {"label": "Reports", "content": "reports"},
        {"label": "Confusion Matrix", "content": "confusion"},
    ]

    selected_tab = ui.tabs(items=tab_items, default_value="Performance", key="monitoring_tabs")

    if selected_tab == "performance":
        render_performance_tab(summary)
    elif selected_tab == "drift":
        render_drift_tab(summary)
    elif selected_tab == "reports":
        render_reports_tab()
    elif selected_tab == "confusion":
        render_confusion_matrix_tab(summary)


def render_performance_tab(summary):
    """Render model performance metrics"""
    st.subheader("Model Performance Metrics")

    perf_report = summary.get("latest_performance_report")
    if not perf_report:
        st.info("No performance data available")
        return

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)

    metrics = perf_report.get("metrics", [{}])[0].get("result", {})

    with col1:
        accuracy = metrics.get("accuracy", 0)
        st.metric("Accuracy", f"{accuracy:.2%}")

    with col2:
        precision = metrics.get("precision", 0)
        st.metric("Precision", f"{precision:.2%}")

    with col3:
        recall = metrics.get("recall", 0)
        st.metric("Recall", f"{recall:.2%}")

    with col4:
        f1_score = metrics.get("f1", 0)
        st.metric("F1-Score", f"{f1_score:.2%}")

    # Per-class metrics
    st.subheader("Per-Emotion Performance")

    # Create sample data (replace with actual data from report)
    emotions = ["Happy", "Sad", "Angry", "Fear", "Disgust", "Neutral"]
    precision_scores = [0.92, 0.88, 0.85, 0.90, 0.87, 0.94]
    recall_scores = [0.90, 0.86, 0.88, 0.85, 0.89, 0.92]

    df = pd.DataFrame({
        "Emotion": emotions,
        "Precision": precision_scores,
        "Recall": recall_scores,
    })

    fig = px.bar(df, x="Emotion", y=["Precision", "Recall"], barmode="group")
    st.plotly_chart(fig, use_container_width=True)


def render_drift_tab(summary):
    """Render data drift information"""
    st.subheader("Data Drift Analysis")

    drift_report = summary.get("latest_drift_report")
    if not drift_report:
        st.info("No drift data available")
        return

    # Drift status
    drift_detected = summary.get("drift_detected", False)

    if drift_detected:
        ui.alert(
            title="⚠️ Data Drift Detected",
            description="Statistical drift detected in input features. Review the detailed report.",
            variant="warning"
        )
    else:
        ui.alert(
            title="✅ No Drift Detected",
            description="Input data distributions are stable.",
            variant="success"
        )

    # Drifted features (if any)
    # Display drift visualization here


def render_reports_tab():
    """Render list of available reports"""
    st.subheader("Monitoring Reports")

    reports = fetch_reports_list()

    if not reports:
        st.info("No reports available")
        return

    for report in reports:
        with st.expander(f"{report['name']} ({report['type']})"):
            col1, col2 = st.columns(2)

            with col1:
                if st.button("View HTML", key=f"html_{report['name']}"):
                    # Display HTML report
                    pass

            with col2:
                if st.button("Download JSON", key=f"json_{report['name']}"):
                    # Download JSON
                    pass


def render_confusion_matrix_tab(summary):
    """Render confusion matrix visualization"""
    st.subheader("Confusion Matrix")

    # Sample confusion matrix (replace with actual data)
    emotions = ["Happy", "Sad", "Angry", "Fear", "Disgust", "Neutral"]

    # Create sample confusion matrix
    import numpy as np
    cm = np.array([
        [450, 12, 8, 5, 10, 15],
        [15, 430, 10, 12, 8, 25],
        [10, 8, 440, 15, 12, 15],
        [8, 10, 12, 445, 10, 15],
        [12, 15, 10, 8, 435, 20],
        [10, 20, 12, 15, 18, 425],
    ])

    # Create heatmap
    fig = px.imshow(
        cm,
        labels=dict(x="Predicted", y="Actual", color="Count"),
        x=emotions,
        y=emotions,
        text_auto=True,
        aspect="auto",
    )

    fig.update_layout(title="Confusion Matrix - Emotion Classification")
    st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
```

---

## 6. Deployment Considerations

### 6.1 Docker Integration

Update `docker-compose.yml` to include PostgreSQL for Evidently:

```yaml
services:
  # Existing services...

  monitoring-db:
    image: postgres:15-alpine
    container_name: ml-monitoring-db
    environment:
      POSTGRES_USER: ml_monitor
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ml_monitoring
    volumes:
      - monitoring_db_data:/var/lib/postgresql/data
    ports:
      - "5433:5432"
    networks:
      - ml-network
    profiles:
      - monitoring

volumes:
  monitoring_db_data:
```

### 6.2 Kubernetes Deployment

For EKS deployment, add to `deployment/k8s/prod/monitoring-stack.yaml`:

```yaml
---
# PostgreSQL for Evidently metrics
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: evidently-db-pvc
  namespace: monitoring
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
  storageClassName: gp3
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: evidently-db
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: evidently-db
  template:
    metadata:
      labels:
        app: evidently-db
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_USER
          value: ml_monitor
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: evidently-db-secret
              key: password
        - name: POSTGRES_DB
          value: ml_monitoring
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: data
          mountPath: /var/lib/postgresql/data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: evidently-db-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: evidently-db
  namespace: monitoring
spec:
  selector:
    app: evidently-db
  ports:
  - port: 5432
    targetPort: 5432
```

### 6.3 Scheduled Monitoring Jobs

Create Kubernetes CronJob for periodic monitoring:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: evidently-monitoring-job
  namespace: ml-speech-emotion
spec:
  schedule: "0 */6 * * *"  # Run every 6 hours
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: monitoring-job
            image: your-backend-image:latest
            command:
            - python
            - -m
            - app.jobs.run_monitoring
            env:
            - name: DATABASE_URL
              value: "postgresql://ml_monitor:password@evidently-db:5432/ml_monitoring"
          restartPolicy: OnFailure
```

---

## 7. Best Practices

### 7.1 Reference Data Management

1. **Initial Reference Dataset**: Use validation dataset from CREMA-D training
2. **Update Strategy**: Refresh reference data quarterly or after model retraining
3. **Version Control**: Track reference dataset versions with model versions
4. **Data Quality**: Ensure reference data represents expected production distribution

### 7.2 Drift Thresholds

Recommended thresholds for speech emotion recognition:

```python
DRIFT_THRESHOLDS = {
    "mfcc_features": 0.15,  # 15% drift tolerance for MFCC
    "chroma_features": 0.20,  # 20% for chroma
    "spectral_features": 0.15,
    "prediction_distribution": 0.10,  # Strict for predictions
}
```

### 7.3 Alert Configuration

Set up alerts for critical conditions:

```python
ALERT_CONDITIONS = {
    "accuracy_drop": 0.10,  # Alert if accuracy drops by 10%
    "drift_detected": True,  # Alert on any drift
    "missing_features": 0.05,  # Alert if >5% missing values
    "latency_spike": 2.0,  # Alert if p95 latency >2s
}
```

### 7.4 Report Retention

```python
REPORT_RETENTION = {
    "hourly_reports": 7,  # Keep 7 days
    "daily_reports": 30,  # Keep 30 days
    "weekly_reports": 365,  # Keep 1 year
}
```

---

## 8. Cost Analysis

### 8.1 Storage Costs

**PostgreSQL Database** (AWS RDS):
- Instance: db.t3.micro ($15/month)
- Storage: 20GB ($2/month)
- **Total**: ~$17/month

**Report Storage** (S3):
- HTML reports: ~5MB each, 100 reports/month = 500MB
- JSON reports: ~1MB each, 100 reports/month = 100MB
- **Total**: ~$0.15/month

### 8.2 Compute Costs

**Monitoring Jobs** (EKS):
- CronJob runs 4x/day, 5 minutes each
- Minimal compute overhead
- **Total**: ~$5/month

**Overall EvidentlyAI Cost**: ~$22/month (on top of existing infrastructure)

---

## 9. Migration Roadmap

### Week 1-2: Foundation
- [ ] Install Evidently package
- [ ] Set up PostgreSQL database
- [ ] Create monitoring service
- [ ] Test with sample data

### Week 3-4: Integration
- [ ] Integrate with FastAPI endpoints
- [ ] Add prediction logging
- [ ] Create monitoring endpoints
- [ ] Test end-to-end flow

### Week 5-6: Dashboard
- [ ] Build Streamlit monitoring page
- [ ] Create Grafana dashboards
- [ ] Configure alerts
- [ ] User acceptance testing

### Week 7-8: Production
- [ ] Deploy to EKS
- [ ] Set up scheduled jobs
- [ ] Monitor performance
- [ ] Optimize and tune

---

## 10. Resources

### Official Documentation
- **EvidentlyAI Docs**: https://docs.evidentlyai.com/
- **GitHub Repository**: https://github.com/evidentlyai/evidently
- **Community Forum**: https://discord.gg/xZjKRaNp8b

### Integration Guides
- **FastAPI Integration**: https://www.evidentlyai.com/blog/fastapi-tutorial
- **ML Monitoring Guide**: https://www.evidentlyai.com/ml-in-production/model-monitoring
- **Real-time Dashboards**: https://www.evidentlyai.com/blog/evidently-and-grafana-ml-monitoring-live-dashboards

### Learning Resources
- **Complete Guide**: https://www.analyticsvidhya.com/blog/2024/03/complete-guide-to-effortless-ml-monitoring-with-evidently-ai/
- **MLOps Community**: https://mlops.community/monitoring-ml-models-with-fastapi-and-evidently-ai/

---

## 11. Conclusion

EvidentlyAI provides comprehensive ML-specific monitoring that complements your existing Prometheus/Grafana infrastructure. The integration is straightforward and non-intrusive, adding valuable observability for:

✅ **Confusion Matrix**: Detailed classification performance
✅ **Model Performance**: Accuracy, precision, recall, F1-score tracking
✅ **Data Drift**: Statistical drift detection in audio features
✅ **Concept Drift**: Prediction distribution monitoring
✅ **Label Drift**: Ground truth distribution changes

**Next Steps**:
1. Review this guide with your team
2. Decide on deployment timeline
3. Start with Phase 1 (Foundation Setup)
4. Iterate based on production needs

---

**Document Version**: 1.0
**Last Updated**: 2025-12-01
**Maintained by**: ML Speech Emotion Recognition Team
