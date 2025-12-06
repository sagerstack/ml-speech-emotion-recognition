"""Unit tests for the Evidently monitoring service."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from app.domain.monitoring.prediction_buffer import PredictionBuffer, PredictionRecord
from app.infrastructure.monitoring.evidently_service import (
    EvidentlyMonitoringService,
    MonitoringReportInfo,
)


class DummyReport:
    """Lightweight stand-in for Evidently's Report to avoid heavy computations."""

    def __init__(self, metrics):
        self.metrics = metrics
        self._current_columns: list[str] = []

    def run(self, current_data, reference_data=None):
        """Match Evidently 0.7 API signature which accepts Dataset objects."""
        # Extract DataFrame from Dataset-like object for testing
        if hasattr(current_data, 'data'):
            self._current_columns = list(current_data.data.columns)
        elif isinstance(current_data, pd.DataFrame):
            self._current_columns = list(current_data.columns)
        return self

    def save_html(self, path: Path) -> None:
        Path(path).write_text("<html>dummy</html>")

    def save_json(self, path: Path) -> None:
        Path(path).write_text('{"metrics": []}')

    def dump_dict(self) -> dict:
        """Return snapshot dict for Evidently 0.7 compatibility."""
        return {
            "metric_results": {
                "drift_metric": {
                    "metric_value_location": {
                        "metric": {
                            "params": {
                                "type": "DriftedColumnsCount"
                            }
                        }
                    },
                    "count": {"value": 0},
                    "share": {"value": 0.0}
                }
            }
        }

    def as_dict(self) -> dict:
        return {
            "metrics": [
                {
                    "metric": "DataDriftPreset",
                    "result": {
                        "dataset_drift": False,
                        "share_of_drifted_columns": 0.0,
                        "number_of_columns": len(self._current_columns),
                    },
                }
            ]
        }


def _prediction_record() -> PredictionRecord:
    return PredictionRecord(
        timestamp=datetime.utcnow(),
        model_version="1",
        predicted_emotion="happy",
        confidence=0.95,
        probabilities={"happy": 0.95, "sad": 0.05},
        features={"f1": 0.3, "f2": 0.7},
        actual_emotion="happy",
        filename="sample.wav",
    )


@pytest.mark.unit
def test_generate_report_writes_files_and_summary(tmp_path, monkeypatch):
    reference_csv = tmp_path / "reference.csv"
    pd.DataFrame(
        [
            {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "f1": 0.1, "f2": 0.2},
            {"timestamp": datetime.utcnow(), "actual_emotion": "sad", "f1": 0.4, "f2": 0.5},
        ]
    ).to_csv(reference_csv, index=False)

    buffer = PredictionBuffer(max_records=10)
    buffer.add(_prediction_record())

    monkeypatch.setattr(
        "app.infrastructure.monitoring.evidently_service.Report",
        DummyReport,
    )

    reports_dir = tmp_path / "reports"
    service = EvidentlyMonitoringService(
        buffer=buffer,
        reference_data_path=str(reference_csv),
        reports_dir=str(reports_dir),
        dashboard_url="http://dashboard.local",
    )

    info = service.generate_report()

    assert isinstance(info, MonitoringReportInfo)
    assert info.html_path.exists()
    assert info.json_path.exists()
    # Check that metrics_summary contains expected drift metrics
    assert "drifted_columns_count" in info.metrics_summary
    assert "drifted_columns_share" in info.metrics_summary
    assert info.metrics_summary["drifted_columns_count"] == 0
    assert info.metrics_summary["drifted_columns_share"] == 0.0

    summary = service.summary()
    assert summary["buffer"]["total_records"] == 1
    assert summary["last_report"]["name"] == info.name
    assert summary["dashboard_url"] == "http://dashboard.local"


@pytest.mark.unit
def test_list_and_lookup_reports(tmp_path, monkeypatch):
    reference_csv = tmp_path / "reference.csv"
    pd.DataFrame(
        [
            {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "f1": 0.1},
            {"timestamp": datetime.utcnow(), "actual_emotion": "sad", "f1": 0.4},
        ]
    ).to_csv(reference_csv, index=False)

    buffer = PredictionBuffer(max_records=5)
    buffer.add(_prediction_record())

    monkeypatch.setattr("app.infrastructure.monitoring.evidently_service.Report", DummyReport)

    service = EvidentlyMonitoringService(
        buffer=buffer,
        reference_data_path=str(reference_csv),
        reports_dir=str(tmp_path / "reports"),
    )

    report_info = service.generate_report()

    reports = service.list_reports()
    assert reports == [report_info.to_dict()]

    assert service.get_report_path(report_info.name) == report_info.html_path
    assert service.get_report_path("missing") is None


@pytest.mark.unit
def test_get_report_path_prevents_traversal(tmp_path: Path, monkeypatch):
    reference_csv = tmp_path / "reference.csv"
    pd.DataFrame([{"timestamp": datetime.utcnow(), "actual_emotion": "happy"}]).to_csv(
        reference_csv, index=False
    )

    external_dir = tmp_path / "outside"
    external_dir.mkdir()
    outside_report = external_dir / "escape.html"
    outside_report.write_text("<html>escape</html>")

    buffer = PredictionBuffer(max_records=1)
    buffer.add(_prediction_record())

    service = EvidentlyMonitoringService(
        buffer=buffer,
        reference_data_path=str(reference_csv),
        reports_dir=str(tmp_path / "reports"),
    )

    assert service.get_report_path("../outside/escape") is None
