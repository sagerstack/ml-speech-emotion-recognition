"""Unit tests for the Evidently monitoring service."""

from pathlib import Path
from datetime import datetime

import pandas as pd

from app.services.evidently_monitoring import EvidentlyMonitoringService, MonitoringReportInfo
from app.services.prediction_buffer import PredictionBuffer, PredictionRecord


class DummyReport:
    """Lightweight stand-in for Evidently's Report to avoid heavy computations."""

    def __init__(self, metrics):
        self.metrics = metrics
        self._current_columns: list[str] = []

    def run(self, reference_data: pd.DataFrame, current_data: pd.DataFrame, column_mapping):
        self._current_columns = list(current_data.columns)

    def save_html(self, path: Path) -> None:
        Path(path).write_text("<html>dummy</html>")

    def save_json(self, path: Path) -> None:
        Path(path).write_text("{\"metrics\": []}")

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
        "app.services.evidently_monitoring.Report",
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
    assert info.metrics_summary == {
        "dataset_drift": False,
        "share_drifted_features": 0.0,
        "total_features": len(buffer.to_dataframe().columns),
    }

    summary = service.summary()
    assert summary["buffer"]["total_records"] == 1
    assert summary["last_report"]["name"] == info.name
    assert summary["dashboard_url"] == "http://dashboard.local"


def test_list_and_lookup_reports(tmp_path, monkeypatch):
    reference_csv = tmp_path / "reference.csv"
    pd.DataFrame([
        {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "f1": 0.1},
        {"timestamp": datetime.utcnow(), "actual_emotion": "sad", "f1": 0.4},
    ]).to_csv(reference_csv, index=False)

    buffer = PredictionBuffer(max_records=5)
    buffer.add(_prediction_record())

    monkeypatch.setattr("app.services.evidently_monitoring.Report", DummyReport)

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
