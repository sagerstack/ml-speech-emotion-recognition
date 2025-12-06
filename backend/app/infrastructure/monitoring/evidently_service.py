"""EvidentlyAI monitoring service for local inference."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

try:  # pragma: no cover - optional dependency shim for offline test environments
    from evidently import Dataset, MulticlassClassification, Report
    from evidently.core.datasets import DataDefinition
    from evidently.core.datasets import MulticlassClassification as MulticlassConfig
    from evidently.presets.classification import ClassificationPreset
    from evidently.presets.drift import DataDriftPreset
    from evidently.ui.workspace import Workspace
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

        def as_dict(self) -> dict[str, object]:
            return {"metrics": []}


from app.domain.monitoring.prediction_buffer import (
    PredictionBuffer,
    PredictionRecord,
    get_prediction_buffer,
)
from app.utils.config import get_settings
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

META_COLUMNS = {
    "timestamp",
    "model_version",
    "api_version",
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
    metrics_summary: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "html_path": str(self.html_path),
            "json_path": str(self.json_path),
            "metrics_summary": self.metrics_summary,
        }


class EvidentlyMonitoringService:
    """Coordinates prediction buffering and Evidently report generation."""

    def __init__(
        self,
        buffer: PredictionBuffer,
        reference_data_path: str | None,
        reports_dir: str,
        dashboard_url: str | None = None,
        workspace_path: str | None = None,
    ):
        self.buffer = buffer
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.dashboard_url = dashboard_url
        self.report_history: list[MonitoringReportInfo] = []
        self.reference_data = self._load_reference_data(reference_data_path)
        self.workspace = self._init_workspace(workspace_path) if workspace_path else None
        self.project = self._get_or_create_project() if self.workspace else None

    def _init_workspace(self, workspace_path: str) -> Workspace | None:
        """Initialize Evidently workspace."""
        try:
            ws = Workspace.create(workspace_path)
            logger.info("Initialized Evidently workspace", path=workspace_path)
            return ws
        except Exception as exc:
            logger.warning("Failed to initialize workspace", error=str(exc))
            return None

    def _configure_dashboard_panels(self, project):
        """Configure monitoring dashboard panels for Evidently 0.7."""
        try:
            from evidently.sdk.models import PanelMetric
            from evidently.sdk.panels import counter_panel, line_plot_panel, text_panel

            # Add title panel
            project.dashboard.add_panel(
                text_panel(title="Speech Emotion Recognition - Model Monitoring Dashboard")
            )

            # === Dataset Drift Summary ===
            project.dashboard.add_panel(
                counter_panel(
                    title="Dataset Drift Score",
                    size="half",
                    values=[
                        PanelMetric(
                            legend="Drifted Columns Share",
                            metric="evidently:metric_v2:DriftedColumnsCount",
                            metric_labels={"value_type": "share"},
                        ),
                    ],
                    aggregation="last",
                )
            )

            project.dashboard.add_panel(
                counter_panel(
                    title="Number of Drifted Columns",
                    size="half",
                    values=[
                        PanelMetric(
                            legend="Drift Count",
                            metric="evidently:metric_v2:DriftedColumnsCount",
                            metric_labels={"value_type": "count"},
                        ),
                    ],
                    aggregation="last",
                )
            )

            # === Prediction Drift (predicted_emotion) ===
            project.dashboard.add_panel(
                counter_panel(
                    title="Prediction Drift (p-value)",
                    size="half",
                    values=[
                        PanelMetric(
                            legend="Predicted Emotion",
                            metric="evidently:metric_v2:ValueDrift",
                            metric_labels={"column": "predicted_emotion"},
                        ),
                    ],
                    aggregation="last",
                )
            )

            # === Label Drift (actual_emotion) ===
            project.dashboard.add_panel(
                counter_panel(
                    title="Label Drift (p-value)",
                    size="half",
                    values=[
                        PanelMetric(
                            legend="Actual Emotion",
                            metric="evidently:metric_v2:ValueDrift",
                            metric_labels={"column": "actual_emotion"},
                        ),
                    ],
                    aggregation="last",
                )
            )

            # === Drift Over Time (Line Plots) ===
            project.dashboard.add_panel(
                line_plot_panel(
                    title="Prediction & Label Drift Over Time",
                    size="full",
                    values=[
                        PanelMetric(
                            legend="Prediction Drift",
                            metric="evidently:metric_v2:ValueDrift",
                            metric_labels={"column": "predicted_emotion"},
                        ),
                        PanelMetric(
                            legend="Label Drift",
                            metric="evidently:metric_v2:ValueDrift",
                            metric_labels={"column": "actual_emotion"},
                        ),
                    ],
                )
            )

            project.dashboard.add_panel(
                line_plot_panel(
                    title="Dataset Drift Score Over Time",
                    size="full",
                    values=[
                        PanelMetric(
                            legend="Drifted Columns Share",
                            metric="evidently:metric_v2:DriftedColumnsCount",
                            metric_labels={"value_type": "share"},
                        ),
                    ],
                )
            )

            logger.info("Configured dashboard panels for project with drift metrics")
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
                if proj.name == "speech_emotion_recognition":
                    logger.info("Using existing Evidently project", project_id=proj.id)
                    return self.workspace.get_project(proj.id)

            # Create new project if none exists
            project = self.workspace.create_project("speech_emotion_recognition")
            project.description = "ML Speech Emotion Recognition Model Monitoring"

            # Configure dashboard panels for monitoring
            self._configure_dashboard_panels(project)

            project.save()
            logger.info(
                "Created new Evidently project with dashboard panels", project_id=project.id
            )
            return project
        except Exception as exc:
            logger.warning("Failed to get/create project", error=str(exc))
            return None

    def _load_reference_data(self, path: str | None) -> pd.DataFrame | None:
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

    def _feature_columns(self, df: pd.DataFrame) -> list[str]:
        return [
            col for col in df.columns if col not in META_COLUMNS and not col.startswith("proba_")
        ]

    def _align_datasets(
        self, reference_df: pd.DataFrame, current_df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
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
        if (
            "predicted_emotion" not in aligned_reference.columns
            and "predicted_emotion" in aligned_current.columns
        ):
            if "actual_emotion" in aligned_reference.columns:
                aligned_reference["predicted_emotion"] = aligned_reference["actual_emotion"]
            else:
                aligned_reference["predicted_emotion"] = "unknown"

        # Filter to only common columns plus essential prediction columns
        essential_cols = {"predicted_emotion", "actual_emotion"}
        keep_cols = list(common_columns | (essential_cols & set(aligned_current.columns)))

        aligned_reference = aligned_reference[
            [c for c in keep_cols if c in aligned_reference.columns]
        ]
        aligned_current = aligned_current[[c for c in keep_cols if c in aligned_current.columns]]

        return aligned_reference, aligned_current, feature_columns

    def _build_column_mapping(
        self, features: list[str], has_targets: bool
    ) -> dict[str, object] | None:
        """Build column mapping for Evidently 0.7.

        Note: Evidently 0.7 auto-detects columns from DataFrame, so this is now optional.
        We keep the method for potential future explicit configuration needs.
        """
        return None  # Evidently 0.7 auto-detects columns from DataFrame

    def _build_data_definition(
        self, feature_columns: list[str], has_targets: bool
    ) -> DataDefinition:
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
        numerical_cols = [col for col in feature_columns if col.startswith("feature_")]
        categorical_cols = ["predicted_emotion"]
        if has_targets:
            categorical_cols.append("actual_emotion")

        return DataDefinition(
            numerical_columns=numerical_cols,
            categorical_columns=categorical_cols,
            classification=classification_config,
        )

    def _extract_metrics_summary(self, snapshot) -> dict[str, object]:
        try:
            # In Evidently 0.7, snapshot.dump_dict() returns the dict representation
            report_dict = snapshot.dump_dict()
            metric_results = report_dict.get("metric_results", {})

            summary: dict[str, object] = {}

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

        has_targets = (
            aligned_current.get("actual_emotion") is not None
            and aligned_current["actual_emotion"].notna().any()
        )

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
        drift_columns = [col for col in feature_columns if col.startswith("feature_")]
        drift_columns.append("predicted_emotion")  # Prediction Drift
        if has_targets:
            drift_columns.append("actual_emotion")  # Label Drift

        # Use categorical drift tests for emotion columns
        # DataDriftPreset provides comprehensive drift detection including:
        # - ValueDrift for each column (numerical and categorical)
        # - DriftedColumnsCount for dataset-level drift summary
        metrics = [
            DataDriftPreset(
                columns=drift_columns,
                cat_method="jensenshannon",  # Use Jensen-Shannon divergence for categorical columns
            )
        ]

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
                self.workspace.add_run(project_id=self.project.id, run=snapshot, name=base_name)
                logger.info(
                    "Added snapshot to Evidently workspace",
                    project_id=self.project.id,
                    run_name=base_name,
                )
                # Trigger dashboard reload to pick up new snapshot
                self._trigger_dashboard_reload(str(self.project.id))
            except Exception as exc:
                logger.warning("Failed to add snapshot to workspace", error=str(exc))

        logger.info(
            "Report generated successfully",
            report_name=base_name,
            metrics_count=len(report.metrics) if hasattr(report, "metrics") else 0,
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

    def summary(self) -> dict[str, object]:
        return {
            "buffer": self.buffer.stats(),
            "last_report": self.report_history[-1].to_dict() if self.report_history else None,
            "reports_dir": str(self.reports_dir),
            "reference_data_loaded": self.reference_data is not None,
            "dashboard_url": self.dashboard_url,
        }

    def list_reports(self) -> list[dict[str, object]]:
        return [report.to_dict() for report in self.report_history]

    def _safe_report_path(self, report_name: str) -> Path | None:
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

    def get_report_path(self, report_name: str) -> Path | None:
        for report in self.report_history:
            if report.name == report_name:
                return report.html_path

        return self._safe_report_path(report_name)


_monitoring_service: EvidentlyMonitoringService | None = None


def get_monitoring_service() -> EvidentlyMonitoringService:
    global _monitoring_service
    if _monitoring_service is None:
        settings = get_settings()
        buffer = get_prediction_buffer()
        _monitoring_service = EvidentlyMonitoringService(
            buffer=buffer,
            reference_data_path=settings.monitoring_reference_path,
            reports_dir=settings.monitoring_reports_dir,
            dashboard_url=settings.evidently_dashboard_url,
            workspace_path="evidently_workspace",
        )
    return _monitoring_service
