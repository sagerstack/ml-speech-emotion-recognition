"""EvidentlyAI monitoring service for local inference."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

import pandas as pd

try:  # pragma: no cover - optional dependency shim for offline test environments
    from evidently import MulticlassClassification, Dataset
    from evidently.presets.classification import ClassificationPreset
    from evidently.presets.drift import DataDriftPreset
    from evidently import Report
    from evidently.ui.workspace import Workspace
    from evidently.core.datasets import DataDefinition, MulticlassClassification as MulticlassConfig
except ImportError:  # pragma: no cover - fallback minimal types
    class MulticlassClassification:  # type: ignore[too-few-public-methods]
        def __init__(self, **_: object) -> None:
            pass

    class ClassificationPreset:  # type: ignore[too-few-public-methods]
        def __init__(self, *args: object, **kwargs: object) -> None:  # noqa: D401
            """Placeholder metric preset."""

    class DataDriftPreset(ClassificationPreset):
        pass

    class Report:  # type: ignore[too-few-public-methods]
        def __init__(self, *args: object, **kwargs: object) -> None:  # noqa: D401
            """Placeholder report implementation."""

        def run(self, *args: object, **kwargs: object) -> None:
            return None

        def save_html(self, path: Path) -> None:  # pragma: no cover - placeholder
            Path(path).write_text("")

        def save_json(self, path: Path) -> None:  # pragma: no cover - placeholder
            Path(path).write_text("{}")

        def as_dict(self) -> Dict[str, object]:
            return {"metrics": []}

    class Workspace:  # type: ignore[too-few-public-methods]
        """Placeholder Workspace for testing without Evidently."""

        @staticmethod
        def create(path: str) -> "Workspace":
            """Create a placeholder workspace instance."""
            return Workspace()

    class Dataset:  # type: ignore[too-few-public-methods]
        """Placeholder Dataset for testing without Evidently."""

        @staticmethod
        def from_pandas(df: object, data_definition: object = None) -> "Dataset":
            """Create a placeholder dataset from pandas DataFrame."""
            return Dataset()

    class DataDefinition:  # type: ignore[too-few-public-methods]
        """Placeholder DataDefinition for testing without Evidently."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            """Initialize placeholder data definition."""
            pass

    class MulticlassConfig:  # type: ignore[too-few-public-methods]
        """Placeholder MulticlassConfig for testing without Evidently."""

        def __init__(self, *args: object, **kwargs: object) -> None:
            """Initialize placeholder multiclass config."""
            pass

from app.domain.monitoring.prediction_buffer import PredictionBuffer, PredictionRecord, get_prediction_buffer
from app.infrastructure.config import get_settings
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

META_COLUMNS = {
    "timestamp",
    "model_version",
    "predicted_emotion",
    "actual_emotion",
    "confidence",
    "filename",
}


@dataclass
class MonitoringReportInfo:
    """Metadata for a generated monitoring report."""

    name: str
    created_at: datetime
    html_path: Path
    json_path: Path
    metrics_summary: Dict[str, object]

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "html_path": str(self.html_path),
            "json_path": str(self.json_path),
            "metrics_summary": self.metrics_summary,
        }


class EvidentlyService:
    """Coordinates prediction buffering and Evidently report generation."""

    def __init__(
        self,
        buffer: PredictionBuffer,
        reference_data_path: Optional[str],
        reports_dir: str,
        dashboard_url: Optional[str] = None,
        workspace_path: Optional[str] = None,
        project_name: str = "speech_emotion_recognition",
    ):
        self.buffer = buffer
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.dashboard_url = dashboard_url
        self.project_name = project_name
        self.report_history: List[MonitoringReportInfo] = []
        self.reference_data = self._load_reference_data(reference_data_path)
        self.workspace = self._init_workspace(workspace_path) if workspace_path else None
        self.project = self._get_or_create_project() if self.workspace else None

    def _init_workspace(self, workspace_path: str) -> Optional[Workspace]:
        """Initialize Evidently workspace."""
        try:
            ws = Workspace.create(workspace_path)
            logger.info("Initialized Evidently workspace", path=workspace_path)
            return ws
        except Exception as exc:
            logger.warning("Failed to initialize workspace", error=str(exc))
            return None

    def _configure_dashboard_panels(self, project):
        """Configure compact 2-column grid dashboard panels for Evidently 0.7.

        Layout:
        - Row 1: Accuracy + Precision (counters)
        - Row 2: Recall + F1 Score (counters)
        - Row 3: Performance Over Time (full width line plot)
        - Row 4: Drifted Features % + # (counters)
        - Row 5: Prediction Drift + Label Drift (counters)
        - Row 6: Drift Trends Over Time (full width line plot)
        - Row 7: Concept Drift Detection (full width line plot)
        """
        try:
            from evidently.sdk.models import DashboardPanelPlot, PanelMetric

            # Row 1: Key Metrics (2 columns)
            project.dashboard.add_panel(
                DashboardPanelPlot(
                    title="Accuracy",
                    size="half",
                    values=[PanelMetric(
                        metric="evidently:metric_v2:Accuracy",
                        metric_labels={"classification_name": "default"},
                        legend="Accuracy",
                    )],
                    plot_params={"plot_type": "counter"},
                )
            )

            project.dashboard.add_panel(
                DashboardPanelPlot(
                    title="Precision",
                    size="half",
                    values=[PanelMetric(
                        metric="evidently:metric_v2:Precision",
                        metric_labels={"classification_name": "default"},
                        legend="Precision",
                    )],
                    plot_params={"plot_type": "counter"},
                )
            )

            # Row 2: More Key Metrics (2 columns)
            project.dashboard.add_panel(
                DashboardPanelPlot(
                    title="Recall",
                    size="half",
                    values=[PanelMetric(
                        metric="evidently:metric_v2:Recall",
                        metric_labels={"classification_name": "default"},
                        legend="Recall",
                    )],
                    plot_params={"plot_type": "counter"},
                )
            )

            project.dashboard.add_panel(
                DashboardPanelPlot(
                    title="F1 Score",
                    size="half",
                    values=[PanelMetric(
                        metric="evidently:metric_v2:F1Score",
                        metric_labels={"classification_name": "default"},
                        legend="F1",
                    )],
                    plot_params={"plot_type": "counter"},
                )
            )

            # Row 3: Performance Trend (full width)
            project.dashboard.add_panel(
                DashboardPanelPlot(
                    title="Performance Over Time",
                    size="full",
                    values=[
                        PanelMetric(
                            metric="evidently:metric_v2:Accuracy",
                            metric_labels={"classification_name": "default"},
                            legend="Accuracy",
                        ),
                        PanelMetric(
                            metric="evidently:metric_v2:Precision",
                            metric_labels={"classification_name": "default"},
                            legend="Precision",
                        ),
                        PanelMetric(
                            metric="evidently:metric_v2:Recall",
                            metric_labels={"classification_name": "default"},
                            legend="Recall",
                        ),
                        PanelMetric(
                            metric="evidently:metric_v2:F1Score",
                            metric_labels={"classification_name": "default"},
                            legend="F1",
                        ),
                    ],
                    plot_params={"plot_type": "line"},
                )
            )

            # Row 4: Drift Metrics (2 columns)
            project.dashboard.add_panel(
                DashboardPanelPlot(
                    title="Drifted Features (%)",
                    size="half",
                    values=[PanelMetric(
                        metric="evidently:metric_v2:DriftedColumnsCount",
                        metric_labels={"value_type": "share"},
                        legend="Drift %",
                    )],
                    plot_params={"plot_type": "counter"},
                )
            )

            project.dashboard.add_panel(
                DashboardPanelPlot(
                    title="Drifted Features (#)",
                    size="half",
                    values=[PanelMetric(
                        metric="evidently:metric_v2:DriftedColumnsCount",
                        metric_labels={"value_type": "count"},
                        legend="Count",
                    )],
                    plot_params={"plot_type": "counter"},
                )
            )

            # Row 5: Prediction & Label Drift (2 columns)
            project.dashboard.add_panel(
                DashboardPanelPlot(
                    title="Prediction Drift (p-value)",
                    size="half",
                    values=[PanelMetric(
                        metric="evidently:metric_v2:ValueDrift",
                        metric_labels={"column": "predicted_emotion"},
                        legend="Pred Drift",
                    )],
                    plot_params={"plot_type": "counter"},
                )
            )

            project.dashboard.add_panel(
                DashboardPanelPlot(
                    title="Label Drift (p-value)",
                    size="half",
                    values=[PanelMetric(
                        metric="evidently:metric_v2:ValueDrift",
                        metric_labels={"column": "actual_emotion"},
                        legend="Label Drift",
                    )],
                    plot_params={"plot_type": "counter"},
                )
            )

            # Row 6: Drift Trends Over Time (full width)
            project.dashboard.add_panel(
                DashboardPanelPlot(
                    title="Drift Trends Over Time",
                    size="full",
                    values=[
                        PanelMetric(
                            metric="evidently:metric_v2:DriftedColumnsCount",
                            metric_labels={"value_type": "share"},
                            legend="Feature Drift %",
                        ),
                        PanelMetric(
                            metric="evidently:metric_v2:ValueDrift",
                            metric_labels={"column": "predicted_emotion"},
                            legend="Prediction Drift",
                        ),
                        PanelMetric(
                            metric="evidently:metric_v2:ValueDrift",
                            metric_labels={"column": "actual_emotion"},
                            legend="Label Drift",
                        ),
                    ],
                    plot_params={"plot_type": "line"},
                )
            )

            # Row 7: Concept Drift Detection (full width)
            project.dashboard.add_panel(
                DashboardPanelPlot(
                    title="Concept Drift Detection: Performance Degradation",
                    subtitle="Sustained drops indicate concept drift",
                    size="full",
                    values=[
                        PanelMetric(
                            metric="evidently:metric_v2:Accuracy",
                            metric_labels={"classification_name": "default"},
                            legend="Accuracy",
                        ),
                        PanelMetric(
                            metric="evidently:metric_v2:F1Score",
                            metric_labels={"classification_name": "default"},
                            legend="F1",
                        ),
                    ],
                    plot_params={"plot_type": "line"},
                )
            )

            logger.info("Configured compact 2-column grid dashboard with 11 panels")
        except Exception as exc:
            logger.warning("Failed to configure dashboard panels", error=str(exc))

    def _trigger_dashboard_reload(self, project_id: str) -> None:
        """Trigger Evidently UI to reload snapshots from the workspace.

        Calls the /api/projects/{id}/reload endpoint to clear the server-side cache.
        Note: The browser UI is a React SPA and requires a manual page refresh (F5)
        to fetch the updated data after new reports are generated.
        """
        if not self.dashboard_url:
            return

        try:
            reload_url = f"{self.dashboard_url}/api/projects/{project_id}/reload"
            response = requests.get(reload_url, timeout=5)

            if response.status_code == 200:
                logger.info(
                    "Triggered Evidently dashboard reload (refresh browser to see updates)",
                    project_id=project_id,
                    url=reload_url,
                )
            else:
                logger.warning(
                    "Dashboard reload returned non-200 status",
                    project_id=project_id,
                    status_code=response.status_code,
                )
        except requests.RequestException as exc:
            logger.warning(
                "Failed to trigger dashboard reload",
                project_id=project_id,
                error=str(exc),
            )

    def _get_or_create_project(self):
        """Get or create Evidently project in workspace."""
        if not self.workspace:
            return None

        try:
            # Try to find existing project
            projects = self.workspace.list_projects()
            for proj in projects:
                if proj.name == self.project_name:
                    logger.info("Using existing Evidently project", project_id=proj.id, project_name=self.project_name)
                    return self.workspace.get_project(proj.id)

            # Create new project if none exists
            project = self.workspace.create_project(self.project_name)
            project.description = "ML Speech Emotion Recognition Model Monitoring"

            # Configure dashboard panels for monitoring
            self._configure_dashboard_panels(project)

            project.save()
            logger.info("Created new Evidently project with dashboard panels", project_id=project.id)
            return project
        except Exception as exc:
            logger.warning("Failed to get/create project", error=str(exc))
            return None

    def _load_reference_data(self, path: Optional[str]) -> Optional[pd.DataFrame]:
        if not path:
            logger.warning("Reference dataset path not configured; drift reports will be limited")
            return None

        ref_path = Path(path)
        if not ref_path.exists():
            logger.warning("Reference dataset not found", path=str(ref_path))
            return None

        try:
            df = pd.read_csv(ref_path)
            logger.info("Loaded reference dataset", rows=len(df), path=str(ref_path))
            return df
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Failed to load reference dataset", error=str(exc))
            return None

    def log_prediction(self, record: PredictionRecord) -> int:
        """Persist a prediction record into the buffer."""

        return self.buffer.add(record)

    def _feature_columns(self, df: pd.DataFrame) -> List[str]:
        return [
            col
            for col in df.columns
            if col not in META_COLUMNS and not col.startswith("proba_")
        ]

    def _align_datasets(
        self, reference_df: pd.DataFrame, current_df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
        feature_columns = self._feature_columns(reference_df)
        if not feature_columns:
            feature_columns = self._feature_columns(current_df)

        aligned_reference = reference_df.copy()
        aligned_current = current_df.copy()

        # For Evidently 0.7, only keep columns that exist in BOTH datasets
        # This avoids errors with empty columns in drift calculation
        common_columns = set(aligned_reference.columns) & set(aligned_current.columns)

        # Keep prediction columns even if not in reference
        # Add predicted_emotion to reference if missing (use actual_emotion as baseline for drift comparison)
        if "predicted_emotion" not in aligned_reference.columns and "predicted_emotion" in aligned_current.columns:
            if "actual_emotion" in aligned_reference.columns:
                aligned_reference["predicted_emotion"] = aligned_reference["actual_emotion"]
            else:
                aligned_reference["predicted_emotion"] = "unknown"

        # Filter to only common columns plus essential prediction columns
        essential_cols = {"predicted_emotion", "actual_emotion"}
        keep_cols = list(common_columns | (essential_cols & set(aligned_current.columns)))

        aligned_reference = aligned_reference[[ c for c in keep_cols if c in aligned_reference.columns]]
        aligned_current = aligned_current[[c for c in keep_cols if c in aligned_current.columns]]

        return aligned_reference, aligned_current, feature_columns

    def _build_column_mapping(self, features: List[str], has_targets: bool) -> Optional[Dict[str, object]]:
        """Build column mapping for Evidently 0.7.

        Note: Evidently 0.7 auto-detects columns from DataFrame, so this is now optional.
        We keep the method for potential future explicit configuration needs.
        """
        return None  # Evidently 0.7 auto-detects columns from DataFrame

    def _build_data_definition(self, feature_columns: List[str], has_targets: bool) -> DataDefinition:
        """Build DataDefinition for Evidently 0.7 with classification configuration."""
        classification_config = []
        if has_targets:
            classification_config = [
                MulticlassConfig(
                    name="default",
                    target="actual_emotion",
                    prediction_labels="predicted_emotion",
                )
            ]

        # Separate numerical feature columns from categorical emotion columns
        numerical_cols = [col for col in feature_columns if col.startswith('feature_')]
        categorical_cols = ['predicted_emotion']
        if has_targets:
            categorical_cols.append('actual_emotion')

        return DataDefinition(
            numerical_columns=numerical_cols,
            categorical_columns=categorical_cols,
            classification=classification_config,
        )

    def _extract_metrics_summary(self, snapshot) -> Dict[str, object]:
        try:
            # In Evidently 0.7, snapshot.dump_dict() returns the dict representation
            report_dict = snapshot.dump_dict()
            metric_results = report_dict.get("metric_results", {})

            summary: Dict[str, object] = {}

            # Extract DriftedColumnsCount metrics
            for metric_id, metric_data in metric_results.items():
                location = metric_data.get("metric_value_location", {})
                params = location.get("metric", {}).get("params", {})
                metric_type = params.get("type", "")

                if "DriftedColumnsCount" in metric_type:
                    # Get count and share values
                    count_data = metric_data.get("count", {})
                    share_data = metric_data.get("share", {})
                    summary["drifted_columns_count"] = count_data.get("value")
                    summary["drifted_columns_share"] = share_data.get("value")

                elif "ValueDrift" in metric_type:
                    column = params.get("column")
                    value = metric_data.get("value")
                    if column == "predicted_emotion":
                        summary["prediction_drift_pvalue"] = value
                    elif column == "actual_emotion":
                        summary["label_drift_pvalue"] = value

            return summary
        except Exception:  # pragma: no cover - fallback path
            return {}

    def generate_report(self) -> MonitoringReportInfo:
        current_df = self.buffer.to_dataframe()
        if current_df.empty:
            raise ValueError("No predictions available for monitoring")

        if self.reference_data is None:
            raise ValueError("Reference dataset is not loaded")

        reference_df, aligned_current, feature_columns = self._align_datasets(
            self.reference_data, current_df
        )

        has_targets = aligned_current.get("actual_emotion") is not None and aligned_current["actual_emotion"].notna().any()

        # Drop actual_emotion column if it's empty to avoid Evidently errors
        if not has_targets and "actual_emotion" in aligned_current.columns:
            aligned_current = aligned_current.drop(columns=["actual_emotion"])
        if not has_targets and "actual_emotion" in reference_df.columns:
            reference_df = reference_df.drop(columns=["actual_emotion"])

        # Build DataDefinition for proper classification metrics in Evidently 0.7
        data_definition = self._build_data_definition(feature_columns, has_targets)

        # Convert DataFrames to Dataset objects with DataDefinition
        reference_dataset = Dataset.from_pandas(reference_df, data_definition=data_definition)
        current_dataset = Dataset.from_pandas(aligned_current, data_definition=data_definition)

        # Monitor both numerical features and categorical emotion columns for drift
        # Include predicted_emotion for Prediction Drift and actual_emotion for Label Drift
        drift_columns = [col for col in feature_columns if col.startswith('feature_')]
        drift_columns.append('predicted_emotion')  # Prediction Drift
        if has_targets:
            drift_columns.append('actual_emotion')  # Label Drift

        # Use categorical drift tests for emotion columns
        # DataDriftPreset provides comprehensive drift detection including:
        # - ValueDrift for each column (numerical and categorical)
        # - DriftedColumnsCount for dataset-level drift summary
        metrics = [DataDriftPreset(
            columns=drift_columns,
            cat_method='jensenshannon',  # Use Jensen-Shannon divergence for categorical columns
        )]

        if has_targets:
            # Note: TargetDriftPreset removed in 0.7, target drift now included in DataDriftPreset
            # ClassificationPreset provides aggregated metrics: Accuracy, Precision, Recall, F1
            metrics.append(ClassificationPreset())

        report = Report(metrics=metrics)
        # In Evidently 0.7, report.run() with Dataset objects enables proper metrics
        snapshot = report.run(
            current_dataset,
            reference_dataset,
        )

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base_name = f"evidently_report_{timestamp}"
        html_path = self.reports_dir / f"{base_name}.html"
        json_path = self.reports_dir / f"{base_name}.json"

        # Save snapshot to HTML and JSON files
        snapshot.save_html(str(html_path))
        snapshot.save_json(str(json_path))

        # Add snapshot to workspace project for UI dashboard
        if self.workspace and self.project:
            try:
                self.workspace.add_run(
                    project_id=self.project.id,
                    run=snapshot,
                    name=base_name
                )
                logger.info("Added snapshot to Evidently workspace", project_id=self.project.id, run_name=base_name)
                # Trigger dashboard reload to pick up new snapshot
                self._trigger_dashboard_reload(str(self.project.id))
            except Exception as exc:
                logger.warning("Failed to add snapshot to workspace", error=str(exc))

        logger.info(
            "Report generated successfully",
            report_name=base_name,
            metrics_count=len(report.metrics) if hasattr(report, 'metrics') else 0
        )

        info = MonitoringReportInfo(
            name=base_name,
            created_at=datetime.utcnow(),
            html_path=html_path,
            json_path=json_path,
            metrics_summary=self._extract_metrics_summary(snapshot),
        )
        self.report_history.append(info)
        logger.info(
            "Generated Evidently report",
            name=info.name,
            html_path=str(info.html_path),
            json_path=str(info.json_path),
        )
        return info

    def should_generate_report(self, buffer_length: int) -> bool:
        settings = get_settings()
        return buffer_length > 0 and buffer_length % settings.monitoring_auto_report_threshold == 0

    def summary(self) -> Dict[str, object]:
        return {
            "buffer": self.buffer.stats(),
            "last_report": self.report_history[-1].to_dict() if self.report_history else None,
            "reports_dir": str(self.reports_dir),
            "reference_data_loaded": self.reference_data is not None,
            "dashboard_url": self.dashboard_url,
        }

    def list_reports(self) -> List[Dict[str, object]]:
        return [report.to_dict() for report in self.report_history]

    def _safe_report_path(self, report_name: str) -> Optional[Path]:
        """Return a report path only if it resides within the reports directory."""

        sanitized_name = Path(f"{report_name}.html").name
        candidate = (self.reports_dir / sanitized_name).resolve()
        reports_root = self.reports_dir.resolve()

        try:
            candidate.relative_to(reports_root)
        except ValueError:
            logger.warning("Rejected report path traversal attempt", report_name=report_name)
            return None

        return candidate if candidate.exists() else None

    def get_report_path(self, report_name: str) -> Optional[Path]:
        for report in self.report_history:
            if report.name == report_name:
                return report.html_path

        return self._safe_report_path(report_name)

    def get_metrics_history(self) -> Dict[str, object]:
        """Extract metrics history from all snapshots for dashboard visualization.

        Reads all snapshot JSON files and extracts metrics needed for the 11 dashboard panels:
        - Classification: accuracy, precision, recall, f1
        - Drift: drifted_features_share, drifted_features_count, prediction_drift, label_drift

        Returns:
            Dictionary with:
            - snapshots: list of {timestamp, metrics} for each snapshot
            - latest: most recent metrics values
            - summary: aggregated statistics
        """
        import json

        if not self.workspace or not self.project:
            return {"snapshots": [], "latest": None, "summary": {}}

        # Find snapshots directory
        workspace_path = Path(self.workspace.path) if hasattr(self.workspace, 'path') else None
        if not workspace_path:
            # Try to construct path from settings
            settings = get_settings()
            workspace_path = Path(settings.evidently_workspace_path)

        snapshots_dir = workspace_path / str(self.project.id) / "snapshots"

        if not snapshots_dir.exists():
            logger.warning("Snapshots directory not found", path=str(snapshots_dir))
            return {"snapshots": [], "latest": None, "summary": {}}

        snapshots_data = []

        # Read all snapshot files
        for snapshot_file in sorted(snapshots_dir.glob("*.json")):
            try:
                with open(snapshot_file, "r") as f:
                    snapshot = json.load(f)

                metrics = self._extract_dashboard_metrics(snapshot)
                if metrics:
                    snapshots_data.append(metrics)

            except Exception as exc:
                logger.warning("Failed to read snapshot", file=str(snapshot_file), error=str(exc))
                continue

        # Sort by timestamp
        snapshots_data.sort(key=lambda x: x.get("timestamp", ""))

        # Get latest metrics
        latest = snapshots_data[-1] if snapshots_data else None

        return {
            "snapshots": snapshots_data,
            "latest": latest,
            "count": len(snapshots_data),
        }

    def _extract_dashboard_metrics(self, snapshot: Dict) -> Optional[Dict[str, object]]:
        """Extract metrics from a single snapshot for dashboard.

        Args:
            snapshot: Parsed JSON snapshot data

        Returns:
            Dictionary with timestamp and all dashboard metrics
        """
        timestamp = snapshot.get("timestamp")
        if not timestamp:
            return None

        metric_results = snapshot.get("metric_results", {})

        metrics = {
            "timestamp": timestamp,
            "accuracy": None,
            "precision": None,
            "recall": None,
            "f1": None,
            "drifted_features_share": None,
            "drifted_features_count": None,
            "prediction_drift": None,
            "label_drift": None,
        }

        for key, value in metric_results.items():
            params = value.get("metric_value_location", {}).get("metric", {}).get("params", {})
            metric_type = params.get("type", "")
            display_name = value.get("display_name", "")

            # Classification metrics
            if metric_type == "evidently:metric_v2:Accuracy":
                metrics["accuracy"] = value.get("value")
            elif metric_type == "evidently:metric_v2:Precision" and "by Label" not in display_name:
                metrics["precision"] = value.get("value")
            elif metric_type == "evidently:metric_v2:Recall" and "by Label" not in display_name:
                metrics["recall"] = value.get("value")
            elif metric_type == "evidently:metric_v2:F1Score" and "by Label" not in display_name:
                metrics["f1"] = value.get("value")

            # Drift metrics
            elif metric_type == "evidently:metric_v2:DriftedColumnsCount":
                # DriftedColumnsCount has nested count and share objects
                count_obj = value.get("count")
                share_obj = value.get("share")
                if count_obj and isinstance(count_obj, dict):
                    metrics["drifted_features_count"] = count_obj.get("value")
                if share_obj and isinstance(share_obj, dict):
                    metrics["drifted_features_share"] = share_obj.get("value")

            elif metric_type == "evidently:metric_v2:ValueDrift":
                column = params.get("column")
                if column == "predicted_emotion":
                    metrics["prediction_drift"] = value.get("value")
                elif column == "actual_emotion":
                    metrics["label_drift"] = value.get("value")

        return metrics


_monitoring_service: Optional[EvidentlyService] = None


def get_monitoring_service() -> EvidentlyService:
    global _monitoring_service
    if _monitoring_service is None:
        settings = get_settings()
        buffer = get_prediction_buffer()
        _monitoring_service = EvidentlyService(
            buffer=buffer,
            reference_data_path=settings.monitoring_reference_path,
            reports_dir=settings.monitoring_reports_dir,
            dashboard_url=settings.evidently_dashboard_url,
            workspace_path=settings.evidently_workspace_path,
            project_name=settings.evidently_project_name,
        )
    return _monitoring_service
