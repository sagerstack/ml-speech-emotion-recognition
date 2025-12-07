"""End-to-end flow test for the monitoring endpoints."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import monitoring as monitoring_module
from app.domain.monitoring.prediction_buffer import PredictionBuffer, PredictionRecord
from app.infrastructure.monitoring.evidently_service import EvidentlyService
from app.main import app


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


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture()
def monitoring_service(tmp_path_factory, monkeypatch):
    tmp_dir = tmp_path_factory.mktemp("monitoring_e2e")
    reference_csv = tmp_dir / "reference.csv"
    pd.DataFrame(
        [
            {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "f1": 0.1},
            {"timestamp": datetime.utcnow(), "actual_emotion": "sad", "f1": 0.2},
        ]
    ).to_csv(reference_csv, index=False)

    buffer = PredictionBuffer(max_records=10)
    buffer.add(
        PredictionRecord(
            timestamp=datetime.utcnow(),
            model_version="1",
            predicted_emotion="happy",
            confidence=0.9,
            probabilities={"happy": 0.9, "sad": 0.1},
            features={"f1": 0.3},
            actual_emotion="happy",
            filename="sample.wav",
        )
    )

    monkeypatch.setattr("app.infrastructure.monitoring.evidently_service.Report", DummyReport)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=str(reference_csv),
        reports_dir=str(tmp_dir / "reports"),
        dashboard_url="http://dashboard.local",
    )

    monkeypatch.setattr(monitoring_module, "get_monitoring_service", lambda: service)

    return service


@pytest.mark.e2e
def test_monitoring_report_generation_and_retrieval(client: TestClient, monitoring_service):
    response = client.post("/v1/monitoring/generate")
    assert response.status_code == 200
    report_name = response.json()["report"]["name"]

    list_response = client.get("/v1/monitoring/reports")
    assert list_response.status_code == 200
    assert any(r["name"] == report_name for r in list_response.json()["reports"])

    summary_response = client.get("/v1/monitoring/summary")
    assert summary_response.status_code == 200
    assert summary_response.json()["last_report"]["name"] == report_name

    file_response = client.get(f"/v1/monitoring/reports/{report_name}")
    assert file_response.status_code == 200
    assert b"dummy" in file_response.content
