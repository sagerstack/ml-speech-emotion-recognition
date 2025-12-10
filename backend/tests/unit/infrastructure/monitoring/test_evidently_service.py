"""Comprehensive unit tests for the Evidently monitoring service."""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pandas as pd
import pytest
from botocore.exceptions import ClientError

from app.domain.monitoring.prediction_buffer import PredictionBuffer, PredictionRecord
from app.infrastructure.monitoring.evidently_service import (
    EvidentlyService,
    MonitoringReportInfo,
    get_monitoring_service,
)


class DummyDataset:
    """Lightweight stand-in for Evidently's Dataset."""

    def __init__(self, data, data_definition=None):
        self.data = data
        self.data_definition = data_definition

    @staticmethod
    def from_pandas(df, data_definition=None):
        """Create DummyDataset from pandas DataFrame."""
        return DummyDataset(df, data_definition)


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
                },
                "prediction_drift": {
                    "metric_value_location": {
                        "metric": {
                            "params": {
                                "type": "ValueDrift",
                                "column": "predicted_emotion"
                            }
                        }
                    },
                    "value": 0.05
                },
                "label_drift": {
                    "metric_value_location": {
                        "metric": {
                            "params": {
                                "type": "ValueDrift",
                                "column": "actual_emotion"
                            }
                        }
                    },
                    "value": 0.03
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
        features={"feature_1": 0.3, "feature_2": 0.7},
        actual_emotion="happy",
        filename="sample.wav",
    )


@pytest.mark.unit
def test_generate_report_writes_files_and_summary(tmp_path, monkeypatch):
    """Test that generate_report creates HTML and JSON files with metrics summary."""
    reference_csv = tmp_path / "reference.csv"
    pd.DataFrame(
        [
            {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "feature_1": 0.1, "feature_2": 0.2},
            {"timestamp": datetime.utcnow(), "actual_emotion": "sad", "feature_1": 0.4, "feature_2": 0.5},
        ]
    ).to_csv(reference_csv, index=False)

    buffer = PredictionBuffer(max_records=10)
    buffer.add(_prediction_record())

    monkeypatch.setattr(
        "app.infrastructure.monitoring.evidently_service.Report",
        DummyReport,
    )
    monkeypatch.setattr(
        "app.infrastructure.monitoring.evidently_service.Dataset",
        DummyDataset,
    )

    reports_dir = tmp_path / "reports"
    service = EvidentlyService(
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
    assert info.metrics_summary["prediction_drift_pvalue"] == 0.05
    assert info.metrics_summary["label_drift_pvalue"] == 0.03

    summary = service.summary()
    assert summary["buffer"]["total_records"] == 1
    assert summary["last_report"]["name"] == info.name
    assert summary["dashboard_url"] == "http://dashboard.local"


@pytest.mark.unit
def test_list_and_lookup_reports(tmp_path, monkeypatch):
    """Test listing reports and looking up report paths."""
    reference_csv = tmp_path / "reference.csv"
    pd.DataFrame(
        [
            {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "feature_1": 0.1},
            {"timestamp": datetime.utcnow(), "actual_emotion": "sad", "feature_1": 0.4},
        ]
    ).to_csv(reference_csv, index=False)

    buffer = PredictionBuffer(max_records=5)
    buffer.add(_prediction_record())

    monkeypatch.setattr("app.infrastructure.monitoring.evidently_service.Report", DummyReport)
    monkeypatch.setattr("app.infrastructure.monitoring.evidently_service.Dataset", DummyDataset)

    service = EvidentlyService(
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
def test_get_report_path_prevents_traversal(tmp_path: Path):
    """Test that get_report_path prevents directory traversal attacks."""
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

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=str(reference_csv),
        reports_dir=str(tmp_path / "reports"),
    )

    assert service.get_report_path("../outside/escape") is None


@pytest.mark.unit
def test_initialization_with_s3_config(tmp_path):
    """Test EvidentlyService initialization with S3 configuration."""
    buffer = PredictionBuffer(max_records=10)
    reports_dir = tmp_path / "reports"

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(reports_dir),
        dashboard_url="http://dashboard.local",
        workspace_path=None,
        project_name="test_project",
        s3_bucket="my-bucket",
        s3_key="reference/data.csv",
        use_s3=True,
    )

    assert service.s3_bucket == "my-bucket"
    assert service.s3_key == "reference/data.csv"
    assert service.use_s3 is True
    assert service._reference_data_loaded is False
    assert service._reference_data is None
    assert service.project_name == "test_project"


@pytest.mark.unit
def test_initialization_without_reference_data(tmp_path):
    """Test EvidentlyService initialization without reference data."""
    buffer = PredictionBuffer(max_records=10)
    reports_dir = tmp_path / "reports"

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(reports_dir),
    )

    assert service._reference_data is None
    assert service._reference_data_loaded is True


@pytest.mark.unit
def test_load_reference_data_local_file_not_found(tmp_path):
    """Test _load_reference_data_local when file doesn't exist."""
    buffer = PredictionBuffer(max_records=10)
    reports_dir = tmp_path / "reports"

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=str(tmp_path / "nonexistent.csv"),
        reports_dir=str(reports_dir),
    )

    assert service._reference_data is None


@pytest.mark.unit
def test_load_reference_data_local_success(tmp_path):
    """Test _load_reference_data_local successfully loads CSV."""
    reference_csv = tmp_path / "reference.csv"
    df = pd.DataFrame([
        {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "feature_1": 0.1},
        {"timestamp": datetime.utcnow(), "actual_emotion": "sad", "feature_1": 0.4},
    ])
    df.to_csv(reference_csv, index=False)

    buffer = PredictionBuffer(max_records=10)
    reports_dir = tmp_path / "reports"

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=str(reference_csv),
        reports_dir=str(reports_dir),
    )

    assert service._reference_data is not None
    assert len(service._reference_data) == 2


@pytest.mark.unit
def test_lazy_loading_reference_data_from_s3(tmp_path):
    """Test lazy loading of reference data from S3."""
    buffer = PredictionBuffer(max_records=10)
    reports_dir = tmp_path / "reports"

    # Create service with S3 config
    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(reports_dir),
        s3_bucket="my-bucket",
        s3_key="reference/data.csv",
        use_s3=True,
    )

    # Reference data should not be loaded yet
    assert service._reference_data_loaded is False

    # Create mock DataFrame
    mock_df = pd.DataFrame([
        {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "feature_1": 0.1},
    ])

    # Mock the S3 loading
    with patch.object(service, '_load_reference_data_s3', return_value=mock_df) as mock_load:
        # Access reference_data property to trigger lazy loading
        result = service.reference_data

        # Verify lazy loading happened
        mock_load.assert_called_once()
        assert service._reference_data_loaded is True
        assert result is not None
        assert len(result) == 1


@pytest.mark.unit
def test_load_reference_data_s3_success(tmp_path):
    """Test _load_reference_data_s3 successfully downloads and loads CSV."""
    buffer = PredictionBuffer(max_records=10)
    reports_dir = tmp_path / "reports"

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(reports_dir),
        s3_bucket="my-bucket",
        s3_key="reference/data.csv",
        use_s3=True,
    )

    # Create mock DataFrame
    mock_df = pd.DataFrame([
        {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "feature_1": 0.1},
        {"timestamp": datetime.utcnow(), "actual_emotion": "sad", "feature_1": 0.4},
    ])

    # Create a cache file to test cache loading
    cache_path = Path("/tmp/reference_dataset_cache.csv")
    mock_df.to_csv(cache_path, index=False)

    try:
        # Call _load_reference_data_s3 which should load from cache
        result = service._load_reference_data_s3()

        assert result is not None
        assert len(result) == 2
    finally:
        # Cleanup
        if cache_path.exists():
            cache_path.unlink()


@pytest.mark.unit
def test_load_reference_data_s3_download_from_s3(tmp_path):
    """Test _load_reference_data_s3 downloads from S3 when cache doesn't exist."""
    buffer = PredictionBuffer(max_records=10)
    reports_dir = tmp_path / "reports"

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(reports_dir),
        s3_bucket="my-bucket",
        s3_key="reference/data.csv",
        use_s3=True,
    )

    # Ensure cache doesn't exist
    cache_path = Path("/tmp/reference_dataset_cache.csv")
    if cache_path.exists():
        cache_path.unlink()

    # Create mock DataFrame
    mock_df = pd.DataFrame([
        {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "feature_1": 0.1},
    ])

    # Mock boto3 S3 client
    with patch('app.infrastructure.monitoring.evidently_service.boto3.client') as mock_boto:
        mock_s3_client = MagicMock()
        mock_boto.return_value = mock_s3_client

        # Mock download_file to create the cache file
        def mock_download(bucket, key, path):
            mock_df.to_csv(path, index=False)

        mock_s3_client.download_file.side_effect = mock_download

        # Call _load_reference_data_s3
        result = service._load_reference_data_s3()

        # Verify S3 download was called
        mock_s3_client.download_file.assert_called_once_with("my-bucket", "reference/data.csv", str(cache_path))
        assert result is not None
        assert len(result) == 1

    # Cleanup
    if cache_path.exists():
        cache_path.unlink()


@pytest.mark.unit
def test_load_reference_data_s3_client_error():
    """Test _load_reference_data_s3 handles S3 ClientError."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir="/tmp/reports",
        s3_bucket="my-bucket",
        s3_key="reference/data.csv",
        use_s3=True,
    )

    # Ensure cache doesn't exist
    cache_path = Path("/tmp/reference_dataset_cache.csv")
    if cache_path.exists():
        cache_path.unlink()

    # Mock boto3 to raise ClientError
    with patch('app.infrastructure.monitoring.evidently_service.boto3.client') as mock_boto:
        mock_s3_client = MagicMock()
        mock_boto.return_value = mock_s3_client

        error_response = {'Error': {'Code': 'NoSuchKey'}}
        mock_s3_client.download_file.side_effect = ClientError(error_response, 'GetObject')

        result = service._load_reference_data_s3()

        assert result is None


@pytest.mark.unit
def test_load_reference_data_s3_no_config():
    """Test _load_reference_data_s3 returns None when S3 config is missing."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir="/tmp/reports",
        s3_bucket=None,
        s3_key=None,
        use_s3=True,
    )

    result = service._load_reference_data_s3()
    assert result is None


@pytest.mark.unit
def test_reference_data_property_setter(tmp_path):
    """Test setting reference_data property directly."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
    )

    mock_df = pd.DataFrame([
        {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "feature_1": 0.1},
    ])

    service.reference_data = mock_df

    assert service._reference_data is mock_df
    assert service._reference_data_loaded is True


@pytest.mark.unit
def test_init_workspace_success(tmp_path):
    """Test workspace initialization succeeds."""
    buffer = PredictionBuffer(max_records=10)
    workspace_path = str(tmp_path / "workspace")

    with patch('app.infrastructure.monitoring.evidently_service.Workspace') as mock_workspace:
        mock_ws = MagicMock()
        mock_workspace.create.return_value = mock_ws

        service = EvidentlyService(
            buffer=buffer,
            reference_data_path=None,
            reports_dir=str(tmp_path / "reports"),
            workspace_path=workspace_path,
        )

        mock_workspace.create.assert_called_once_with(workspace_path)
        assert service.workspace is mock_ws


@pytest.mark.unit
def test_init_workspace_failure(tmp_path):
    """Test workspace initialization handles failure gracefully."""
    buffer = PredictionBuffer(max_records=10)
    workspace_path = str(tmp_path / "workspace")

    with patch('app.infrastructure.monitoring.evidently_service.Workspace') as mock_workspace:
        mock_workspace.create.side_effect = Exception("Workspace creation failed")

        service = EvidentlyService(
            buffer=buffer,
            reference_data_path=None,
            reports_dir=str(tmp_path / "reports"),
            workspace_path=workspace_path,
        )

        assert service.workspace is None


@pytest.mark.unit
def test_get_or_create_project_existing_project(tmp_path):
    """Test getting an existing project from workspace."""
    buffer = PredictionBuffer(max_records=10)

    with patch('app.infrastructure.monitoring.evidently_service.Workspace') as mock_workspace:
        mock_ws = MagicMock()
        mock_workspace.create.return_value = mock_ws

        # Mock existing project
        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_project.name = "speech_emotion_recognition"

        mock_ws.list_projects.return_value = [mock_project]
        mock_ws.get_project.return_value = mock_project

        service = EvidentlyService(
            buffer=buffer,
            reference_data_path=None,
            reports_dir=str(tmp_path / "reports"),
            workspace_path=str(tmp_path / "workspace"),
            project_name="speech_emotion_recognition",
        )

        assert service.project is mock_project
        mock_ws.get_project.assert_called_once_with("project-123")


@pytest.mark.unit
def test_get_or_create_project_create_new_project(tmp_path):
    """Test creating a new project when none exists."""
    buffer = PredictionBuffer(max_records=10)

    with patch('app.infrastructure.monitoring.evidently_service.Workspace') as mock_workspace:
        mock_ws = MagicMock()
        mock_workspace.create.return_value = mock_ws

        # No existing projects
        mock_ws.list_projects.return_value = []

        # Mock new project
        mock_project = MagicMock()
        mock_project.id = "project-456"
        mock_ws.create_project.return_value = mock_project

        with patch.object(EvidentlyService, '_configure_dashboard_panels'):
            service = EvidentlyService(
                buffer=buffer,
                reference_data_path=None,
                reports_dir=str(tmp_path / "reports"),
                workspace_path=str(tmp_path / "workspace"),
                project_name="new_project",
            )

        assert service.project is mock_project
        mock_ws.create_project.assert_called_once_with("new_project")
        mock_project.save.assert_called_once()


@pytest.mark.unit
def test_get_or_create_project_failure(tmp_path):
    """Test project creation failure is handled gracefully."""
    buffer = PredictionBuffer(max_records=10)

    with patch('app.infrastructure.monitoring.evidently_service.Workspace') as mock_workspace:
        mock_ws = MagicMock()
        mock_workspace.create.return_value = mock_ws
        mock_ws.list_projects.side_effect = Exception("Failed to list projects")

        service = EvidentlyService(
            buffer=buffer,
            reference_data_path=None,
            reports_dir=str(tmp_path / "reports"),
            workspace_path=str(tmp_path / "workspace"),
        )

        assert service.project is None


@pytest.mark.unit
def test_configure_dashboard_panels(tmp_path):
    """Test dashboard panel configuration."""
    buffer = PredictionBuffer(max_records=10)

    with patch('app.infrastructure.monitoring.evidently_service.Workspace') as mock_workspace:
        mock_ws = MagicMock()
        mock_workspace.create.return_value = mock_ws
        mock_ws.list_projects.return_value = []

        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_project.dashboard = MagicMock()
        mock_ws.create_project.return_value = mock_project

        # Mock the import of DashboardPanelPlot and PanelMetric from evidently.sdk.models
        with patch.dict('sys.modules', {'evidently.sdk.models': MagicMock()}):
            service = EvidentlyService(
                buffer=buffer,
                reference_data_path=None,
                reports_dir=str(tmp_path / "reports"),
                workspace_path=str(tmp_path / "workspace"),
            )

        # Verify dashboard panels were added
        assert mock_project.dashboard.add_panel.call_count > 0


@pytest.mark.unit
@pytest.mark.skipci
def test_configure_dashboard_panels_failure(tmp_path):
    """Test dashboard panel configuration handles import errors."""
    buffer = PredictionBuffer(max_records=10)

    with patch('app.infrastructure.monitoring.evidently_service.Workspace') as mock_workspace:
        mock_ws = MagicMock()
        mock_workspace.create.return_value = mock_ws
        mock_ws.list_projects.return_value = []

        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_ws.create_project.return_value = mock_project

        # Simulate import error for DashboardPanelPlot
        with patch('builtins.__import__', side_effect=ImportError("No module named 'evidently.sdk.models'")):
            service = EvidentlyService(
                buffer=buffer,
                reference_data_path=None,
                reports_dir=str(tmp_path / "reports"),
                workspace_path=str(tmp_path / "workspace"),
            )

        # Service should still be created despite dashboard panel configuration failure
        assert service.workspace is mock_ws


@pytest.mark.unit
def test_trigger_dashboard_reload_success(tmp_path):
    """Test triggering dashboard reload succeeds."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
        dashboard_url="http://dashboard.local",
    )

    with patch('app.infrastructure.monitoring.evidently_service.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response

        service._trigger_dashboard_reload("project-123")

        mock_get.assert_called_once_with(
            "http://dashboard.local/api/projects/project-123/reload",
            timeout=5
        )


@pytest.mark.unit
def test_trigger_dashboard_reload_no_url(tmp_path):
    """Test triggering dashboard reload when no URL is configured."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
        dashboard_url=None,
    )

    with patch('app.infrastructure.monitoring.evidently_service.requests.get') as mock_get:
        service._trigger_dashboard_reload("project-123")

        # Should not call requests.get
        mock_get.assert_not_called()


@pytest.mark.unit
def test_trigger_dashboard_reload_non_200_status(tmp_path):
    """Test triggering dashboard reload handles non-200 status."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
        dashboard_url="http://dashboard.local",
    )

    with patch('app.infrastructure.monitoring.evidently_service.requests.get') as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        # Should not raise exception
        service._trigger_dashboard_reload("project-123")


@pytest.mark.unit
def test_trigger_dashboard_reload_request_exception(tmp_path):
    """Test triggering dashboard reload handles request exceptions."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
        dashboard_url="http://dashboard.local",
    )

    with patch('app.infrastructure.monitoring.evidently_service.requests.get') as mock_get:
        import requests
        mock_get.side_effect = requests.RequestException("Connection failed")

        # Should not raise exception
        service._trigger_dashboard_reload("project-123")


@pytest.mark.unit
def test_log_prediction(tmp_path):
    """Test logging a prediction record."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
    )

    record = _prediction_record()
    count = service.log_prediction(record)

    assert count == 1
    assert len(buffer) == 1


@pytest.mark.unit
def test_feature_columns_extraction(tmp_path):
    """Test _feature_columns extracts feature columns correctly."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
    )

    df = pd.DataFrame({
        "feature_1": [0.1, 0.2],
        "feature_2": [0.3, 0.4],
        "predicted_emotion": ["happy", "sad"],
        "actual_emotion": ["happy", "sad"],
        "confidence": [0.95, 0.88],
        "proba_happy": [0.95, 0.12],
        "proba_sad": [0.05, 0.88],
    })

    features = service._feature_columns(df)

    assert "feature_1" in features
    assert "feature_2" in features
    assert "predicted_emotion" not in features
    assert "actual_emotion" not in features
    assert "confidence" not in features
    assert "proba_happy" not in features
    assert "proba_sad" not in features


@pytest.mark.unit
def test_align_datasets(tmp_path):
    """Test _align_datasets aligns reference and current datasets."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
    )

    reference_df = pd.DataFrame({
        "feature_1": [0.1, 0.2],
        "feature_2": [0.3, 0.4],
        "actual_emotion": ["happy", "sad"],
    })

    current_df = pd.DataFrame({
        "feature_1": [0.5, 0.6],
        "feature_2": [0.7, 0.8],
        "predicted_emotion": ["happy", "angry"],
        "actual_emotion": ["happy", "angry"],
    })

    aligned_ref, aligned_curr, features = service._align_datasets(reference_df, current_df)

    assert "predicted_emotion" in aligned_ref.columns
    assert "predicted_emotion" in aligned_curr.columns
    assert len(features) >= 2


@pytest.mark.unit
def test_align_datasets_adds_predicted_emotion_to_reference(tmp_path):
    """Test _align_datasets adds predicted_emotion to reference if missing."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
    )

    reference_df = pd.DataFrame({
        "feature_1": [0.1, 0.2],
        "actual_emotion": ["happy", "sad"],
    })

    current_df = pd.DataFrame({
        "feature_1": [0.5, 0.6],
        "predicted_emotion": ["happy", "angry"],
    })

    aligned_ref, aligned_curr, features = service._align_datasets(reference_df, current_df)

    # Reference should have predicted_emotion added (using actual_emotion as baseline)
    assert "predicted_emotion" in aligned_ref.columns
    assert aligned_ref["predicted_emotion"].tolist() == ["happy", "sad"]


@pytest.mark.unit
def test_build_data_definition_with_targets(tmp_path):
    """Test _build_data_definition with target labels."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
    )

    feature_columns = ["feature_1", "feature_2"]
    data_def = service._build_data_definition(feature_columns, has_targets=True)

    assert data_def is not None


@pytest.mark.unit
def test_build_data_definition_without_targets(tmp_path):
    """Test _build_data_definition without target labels."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
    )

    feature_columns = ["feature_1", "feature_2"]
    data_def = service._build_data_definition(feature_columns, has_targets=False)

    assert data_def is not None


@pytest.mark.unit
def test_generate_report_no_predictions_raises_error(tmp_path):
    """Test generate_report raises error when no predictions are available."""
    reference_csv = tmp_path / "reference.csv"
    pd.DataFrame([
        {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "feature_1": 0.1},
    ]).to_csv(reference_csv, index=False)

    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=str(reference_csv),
        reports_dir=str(tmp_path / "reports"),
    )

    with pytest.raises(ValueError, match="No predictions available for monitoring"):
        service.generate_report()


@pytest.mark.unit
def test_generate_report_no_reference_data_raises_error(tmp_path):
    """Test generate_report raises error when reference data is not loaded."""
    buffer = PredictionBuffer(max_records=10)
    buffer.add(_prediction_record())

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
    )

    with pytest.raises(ValueError, match="Reference dataset is not loaded"):
        service.generate_report()


@pytest.mark.unit
def test_generate_report_without_actual_emotions(tmp_path, monkeypatch):
    """Test generate_report works when actual_emotion is missing."""
    reference_csv = tmp_path / "reference.csv"
    pd.DataFrame([
        {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "feature_1": 0.1},
    ]).to_csv(reference_csv, index=False)

    buffer = PredictionBuffer(max_records=10)
    record = PredictionRecord(
        timestamp=datetime.utcnow(),
        model_version="1",
        predicted_emotion="happy",
        confidence=0.95,
        probabilities={"happy": 0.95},
        features={"feature_1": 0.3},
        actual_emotion=None,  # No actual emotion
    )
    buffer.add(record)

    monkeypatch.setattr("app.infrastructure.monitoring.evidently_service.Report", DummyReport)
    monkeypatch.setattr("app.infrastructure.monitoring.evidently_service.Dataset", DummyDataset)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=str(reference_csv),
        reports_dir=str(tmp_path / "reports"),
    )

    info = service.generate_report()

    assert isinstance(info, MonitoringReportInfo)


@pytest.mark.unit
def test_generate_report_with_workspace(tmp_path, monkeypatch):
    """Test generate_report adds snapshot to workspace."""
    reference_csv = tmp_path / "reference.csv"
    pd.DataFrame([
        {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "feature_1": 0.1},
    ]).to_csv(reference_csv, index=False)

    buffer = PredictionBuffer(max_records=10)
    buffer.add(_prediction_record())

    monkeypatch.setattr("app.infrastructure.monitoring.evidently_service.Report", DummyReport)
    monkeypatch.setattr("app.infrastructure.monitoring.evidently_service.Dataset", DummyDataset)

    with patch('app.infrastructure.monitoring.evidently_service.Workspace') as mock_workspace:
        mock_ws = MagicMock()
        mock_workspace.create.return_value = mock_ws
        mock_ws.list_projects.return_value = []

        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_ws.create_project.return_value = mock_project

        with patch.object(EvidentlyService, '_configure_dashboard_panels'):
            service = EvidentlyService(
                buffer=buffer,
                reference_data_path=str(reference_csv),
                reports_dir=str(tmp_path / "reports"),
                workspace_path=str(tmp_path / "workspace"),
            )

        with patch.object(service, '_trigger_dashboard_reload') as mock_reload:
            info = service.generate_report()

        # Verify workspace.add_run was called
        mock_ws.add_run.assert_called_once()
        mock_reload.assert_called_once_with("project-123")


@pytest.mark.unit
def test_generate_report_workspace_add_run_failure(tmp_path, monkeypatch):
    """Test generate_report handles workspace.add_run failure."""
    reference_csv = tmp_path / "reference.csv"
    pd.DataFrame([
        {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "feature_1": 0.1},
    ]).to_csv(reference_csv, index=False)

    buffer = PredictionBuffer(max_records=10)
    buffer.add(_prediction_record())

    monkeypatch.setattr("app.infrastructure.monitoring.evidently_service.Report", DummyReport)
    monkeypatch.setattr("app.infrastructure.monitoring.evidently_service.Dataset", DummyDataset)

    with patch('app.infrastructure.monitoring.evidently_service.Workspace') as mock_workspace:
        mock_ws = MagicMock()
        mock_workspace.create.return_value = mock_ws
        mock_ws.list_projects.return_value = []

        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_ws.create_project.return_value = mock_project
        mock_ws.add_run.side_effect = Exception("Add run failed")

        with patch.object(EvidentlyService, '_configure_dashboard_panels'):
            service = EvidentlyService(
                buffer=buffer,
                reference_data_path=str(reference_csv),
                reports_dir=str(tmp_path / "reports"),
                workspace_path=str(tmp_path / "workspace"),
            )

        # Should not raise exception
        info = service.generate_report()
        assert isinstance(info, MonitoringReportInfo)


@pytest.mark.unit
def test_should_generate_report(tmp_path):
    """Test should_generate_report logic."""
    buffer = PredictionBuffer(max_records=10)

    with patch('app.infrastructure.monitoring.evidently_service.get_settings') as mock_settings:
        mock_settings.return_value.monitoring_auto_report_threshold = 5

        service = EvidentlyService(
            buffer=buffer,
            reference_data_path=None,
            reports_dir=str(tmp_path / "reports"),
        )

        assert service.should_generate_report(0) is False
        assert service.should_generate_report(3) is False
        assert service.should_generate_report(5) is True
        assert service.should_generate_report(10) is True


@pytest.mark.unit
def test_summary_no_reports(tmp_path):
    """Test summary when no reports have been generated."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
        dashboard_url="http://dashboard.local",
    )

    summary = service.summary()

    assert summary["buffer"]["total_records"] == 0
    assert summary["last_report"] is None
    assert summary["reports_dir"] == str(tmp_path / "reports")
    assert summary["reference_data_loaded"] is False
    assert summary["dashboard_url"] == "http://dashboard.local"


@pytest.mark.unit
def test_get_metrics_history_no_workspace(tmp_path):
    """Test get_metrics_history when no workspace is configured."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
    )

    result = service.get_metrics_history()

    assert result == {"snapshots": [], "latest": None, "summary": {}}


@pytest.mark.unit
def test_get_metrics_history_with_snapshots(tmp_path):
    """Test get_metrics_history with snapshot files."""
    buffer = PredictionBuffer(max_records=10)

    # Create mock workspace and project
    with patch('app.infrastructure.monitoring.evidently_service.Workspace') as mock_workspace:
        mock_ws = MagicMock()
        mock_workspace.create.return_value = mock_ws
        mock_ws.list_projects.return_value = []
        mock_ws.path = str(tmp_path / "workspace")

        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_ws.create_project.return_value = mock_project

        with patch.object(EvidentlyService, '_configure_dashboard_panels'):
            service = EvidentlyService(
                buffer=buffer,
                reference_data_path=None,
                reports_dir=str(tmp_path / "reports"),
                workspace_path=str(tmp_path / "workspace"),
            )

        # Create snapshots directory and files
        snapshots_dir = tmp_path / "workspace" / "project-123" / "snapshots"
        snapshots_dir.mkdir(parents=True)

        snapshot_data = {
            "timestamp": "2024-01-01T00:00:00",
            "metric_results": {
                "accuracy": {
                    "metric_value_location": {
                        "metric": {"params": {"type": "evidently:metric_v2:Accuracy"}}
                    },
                    "value": 0.95,
                    "display_name": "Accuracy"
                },
                "drift": {
                    "metric_value_location": {
                        "metric": {"params": {"type": "evidently:metric_v2:DriftedColumnsCount"}}
                    },
                    "count": {"value": 2},
                    "share": {"value": 0.25}
                }
            }
        }

        snapshot_file = snapshots_dir / "snapshot_1.json"
        with open(snapshot_file, 'w') as f:
            json.dump(snapshot_data, f)

        result = service.get_metrics_history()

        assert len(result["snapshots"]) == 1
        assert result["latest"] is not None
        assert result["count"] == 1


@pytest.mark.unit
def test_extract_dashboard_metrics_no_timestamp():
    """Test _extract_dashboard_metrics returns None when no timestamp."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir="/tmp/reports",
    )

    snapshot = {"metric_results": {}}

    result = service._extract_dashboard_metrics(snapshot)
    assert result is None


@pytest.mark.unit
def test_extract_dashboard_metrics_with_all_metrics():
    """Test _extract_dashboard_metrics extracts all metrics correctly."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir="/tmp/reports",
    )

    snapshot = {
        "timestamp": "2024-01-01T00:00:00",
        "metric_results": {
            "accuracy": {
                "metric_value_location": {
                    "metric": {"params": {"type": "evidently:metric_v2:Accuracy"}}
                },
                "value": 0.95,
                "display_name": "Accuracy"
            },
            "precision": {
                "metric_value_location": {
                    "metric": {"params": {"type": "evidently:metric_v2:Precision"}}
                },
                "value": 0.92,
                "display_name": "Precision"
            },
            "recall": {
                "metric_value_location": {
                    "metric": {"params": {"type": "evidently:metric_v2:Recall"}}
                },
                "value": 0.91,
                "display_name": "Recall"
            },
            "f1": {
                "metric_value_location": {
                    "metric": {"params": {"type": "evidently:metric_v2:F1Score"}}
                },
                "value": 0.915,
                "display_name": "F1 Score"
            },
            "drift": {
                "metric_value_location": {
                    "metric": {"params": {"type": "evidently:metric_v2:DriftedColumnsCount"}}
                },
                "count": {"value": 2},
                "share": {"value": 0.25}
            },
            "pred_drift": {
                "metric_value_location": {
                    "metric": {"params": {"type": "evidently:metric_v2:ValueDrift", "column": "predicted_emotion"}}
                },
                "value": 0.05
            },
            "label_drift": {
                "metric_value_location": {
                    "metric": {"params": {"type": "evidently:metric_v2:ValueDrift", "column": "actual_emotion"}}
                },
                "value": 0.03
            }
        }
    }

    result = service._extract_dashboard_metrics(snapshot)

    assert result["timestamp"] == "2024-01-01T00:00:00"
    assert result["accuracy"] == 0.95
    assert result["precision"] == 0.92
    assert result["recall"] == 0.91
    assert result["f1"] == 0.915
    assert result["drifted_features_count"] == 2
    assert result["drifted_features_share"] == 0.25
    assert result["prediction_drift"] == 0.05
    assert result["label_drift"] == 0.03


@pytest.mark.unit
def test_extract_dashboard_metrics_skips_by_label_metrics():
    """Test _extract_dashboard_metrics skips 'by Label' metrics."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir="/tmp/reports",
    )

    snapshot = {
        "timestamp": "2024-01-01T00:00:00",
        "metric_results": {
            "precision": {
                "metric_value_location": {
                    "metric": {"params": {"type": "evidently:metric_v2:Precision"}}
                },
                "value": 0.92,
                "display_name": "Precision by Label: happy"
            }
        }
    }

    result = service._extract_dashboard_metrics(snapshot)

    # Should not extract metrics with "by Label" in display_name
    assert result["precision"] is None


@pytest.mark.unit
def test_get_monitoring_service_disabled():
    """Test get_monitoring_service returns None when monitoring is disabled."""
    with patch('app.infrastructure.monitoring.evidently_service.get_settings') as mock_settings:
        mock_settings.return_value.enable_model_monitoring = False

        result = get_monitoring_service()

        assert result is None


@pytest.mark.unit
def test_get_monitoring_service_enabled():
    """Test get_monitoring_service returns EvidentlyService when enabled."""
    with patch('app.infrastructure.monitoring.evidently_service.get_settings') as mock_settings:
        mock_config = MagicMock()
        mock_config.enable_model_monitoring = True
        mock_config.monitoring_reference_path = None
        mock_config.monitoring_reports_dir = "/tmp/reports"
        mock_config.evidently_dashboard_url = None
        mock_config.evidently_workspace_path = None
        mock_config.evidently_project_name = "test_project"
        mock_config.monitoring_reference_s3_bucket = None
        mock_config.s3_bucket_name = "default-bucket"
        mock_config.monitoring_reference_s3_key = None
        mock_config.use_sagemaker = False
        mock_settings.return_value = mock_config

        with patch('app.infrastructure.monitoring.evidently_service.get_prediction_buffer') as mock_buffer:
            mock_buffer.return_value = PredictionBuffer(max_records=10)

            # Reset global singleton
            import app.infrastructure.monitoring.evidently_service as module
            module._monitoring_service = None

            result = get_monitoring_service()

            assert result is not None
            assert isinstance(result, EvidentlyService)

            # Cleanup
            module._monitoring_service = None


@pytest.mark.unit
def test_monitoring_report_info_to_dict():
    """Test MonitoringReportInfo.to_dict serialization."""
    timestamp = datetime(2024, 1, 1, 12, 0, 0)
    info = MonitoringReportInfo(
        name="test_report",
        created_at=timestamp,
        html_path=Path("/tmp/report.html"),
        json_path=Path("/tmp/report.json"),
        metrics_summary={"accuracy": 0.95}
    )

    result = info.to_dict()

    assert result["name"] == "test_report"
    assert result["created_at"] == timestamp.isoformat()
    assert result["html_path"] == "/tmp/report.html"
    assert result["json_path"] == "/tmp/report.json"
    assert result["metrics_summary"] == {"accuracy": 0.95}


@pytest.mark.unit
def test_get_metrics_history_snapshots_dir_not_found(tmp_path):
    """Test get_metrics_history when snapshots directory doesn't exist."""
    buffer = PredictionBuffer(max_records=10)

    with patch('app.infrastructure.monitoring.evidently_service.Workspace') as mock_workspace:
        mock_ws = MagicMock()
        mock_workspace.create.return_value = mock_ws
        mock_ws.list_projects.return_value = []
        mock_ws.path = str(tmp_path / "workspace")

        mock_project = MagicMock()
        mock_project.id = "project-456"
        mock_ws.create_project.return_value = mock_project

        with patch.object(EvidentlyService, '_configure_dashboard_panels'):
            service = EvidentlyService(
                buffer=buffer,
                reference_data_path=None,
                reports_dir=str(tmp_path / "reports"),
                workspace_path=str(tmp_path / "workspace"),
            )

        # Snapshots directory doesn't exist
        result = service.get_metrics_history()

        assert result == {"snapshots": [], "latest": None, "summary": {}}


@pytest.mark.unit
def test_get_metrics_history_invalid_snapshot_file(tmp_path):
    """Test get_metrics_history handles invalid snapshot files."""
    buffer = PredictionBuffer(max_records=10)

    with patch('app.infrastructure.monitoring.evidently_service.Workspace') as mock_workspace:
        mock_ws = MagicMock()
        mock_workspace.create.return_value = mock_ws
        mock_ws.list_projects.return_value = []
        mock_ws.path = str(tmp_path / "workspace")

        mock_project = MagicMock()
        mock_project.id = "project-123"
        mock_ws.create_project.return_value = mock_project

        with patch.object(EvidentlyService, '_configure_dashboard_panels'):
            service = EvidentlyService(
                buffer=buffer,
                reference_data_path=None,
                reports_dir=str(tmp_path / "reports"),
                workspace_path=str(tmp_path / "workspace"),
            )

        # Create snapshots directory with invalid file
        snapshots_dir = tmp_path / "workspace" / "project-123" / "snapshots"
        snapshots_dir.mkdir(parents=True)

        invalid_file = snapshots_dir / "invalid.json"
        invalid_file.write_text("not valid json{")

        result = service.get_metrics_history()

        # Should handle invalid file gracefully
        assert result["snapshots"] == []


@pytest.mark.unit
def test_load_reference_data_s3_cached_file_corrupt(tmp_path):
    """Test _load_reference_data_s3 handles corrupt cached file."""
    buffer = PredictionBuffer(max_records=10)

    service = EvidentlyService(
        buffer=buffer,
        reference_data_path=None,
        reports_dir=str(tmp_path / "reports"),
        s3_bucket="my-bucket",
        s3_key="reference/data.csv",
        use_s3=True,
    )

    # Create corrupt cache file
    cache_path = Path("/tmp/reference_dataset_cache.csv")
    cache_path.write_text("invalid,csv\ndata")

    # Mock boto3 to provide valid data
    mock_df = pd.DataFrame([
        {"timestamp": datetime.utcnow(), "actual_emotion": "happy", "feature_1": 0.1},
    ])

    try:
        with patch('app.infrastructure.monitoring.evidently_service.boto3.client') as mock_boto:
            mock_s3_client = MagicMock()
            mock_boto.return_value = mock_s3_client

            def mock_download(bucket, key, path):
                mock_df.to_csv(path, index=False)

            mock_s3_client.download_file.side_effect = mock_download

            result = service._load_reference_data_s3()

            # Should re-download from S3 after cache load failure
            assert result is not None
            assert len(result) == 1
    finally:
        if cache_path.exists():
            cache_path.unlink()
