"""EvidentlyAI monitoring service for local inference."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

try:  # pragma: no cover - optional dependency shim for offline test environments
    from evidently import ColumnMapping
    from evidently.metric_preset import ClassificationPreset, DataDriftPreset, TargetDriftPreset
    from evidently.report import Report
except ImportError:  # pragma: no cover - fallback minimal types
    class ColumnMapping:  # type: ignore[too-many-instance-attributes]
        def __init__(self, **_: object) -> None:
            self.target = None
            self.prediction = None
            self.datetime = None
            self.numerical_features = None
            self.categorical_features = None

    class ClassificationPreset:  # type: ignore[too-few-public-methods]
        def __init__(self, *args: object, **kwargs: object) -> None:  # noqa: D401
            """Placeholder metric preset."""

    class DataDriftPreset(ClassificationPreset):
        pass

    class TargetDriftPreset(ClassificationPreset):
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

from app.services.prediction_buffer import PredictionBuffer, PredictionRecord, get_prediction_buffer
from app.utils.config import get_settings
from app.utils.logging import get_logger

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


class EvidentlyMonitoringService:
    """Coordinates prediction buffering and Evidently report generation."""

    def __init__(
        self,
        buffer: PredictionBuffer,
        reference_data_path: Optional[str],
        reports_dir: str,
        dashboard_url: Optional[str] = None,
    ):
        self.buffer = buffer
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.dashboard_url = dashboard_url
        self.report_history: List[MonitoringReportInfo] = []
        self.reference_data = self._load_reference_data(reference_data_path)

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

        for col in feature_columns:
            if col not in aligned_current:
                aligned_current[col] = pd.NA
            if col not in aligned_reference:
                aligned_reference[col] = pd.NA

        if "predicted_emotion" not in aligned_reference:
            aligned_reference["predicted_emotion"] = aligned_reference.get(
                "actual_emotion"
            )

        if "actual_emotion" in aligned_current and "actual_emotion" not in aligned_reference:
            aligned_reference["actual_emotion"] = pd.NA

        return aligned_reference, aligned_current, feature_columns

    def _build_column_mapping(self, features: List[str], has_targets: bool) -> ColumnMapping:
        return ColumnMapping(
            target="actual_emotion" if has_targets else None,
            prediction="predicted_emotion",
            numerical_features=features,
        )

    def _extract_metrics_summary(self, report: Report) -> Dict[str, object]:
        try:
            report_dict = report.as_dict()
            metrics = report_dict.get("metrics", [])
            data_drift = next(
                (
                    metric
                    for metric in metrics
                    if metric.get("metric") == "DataDriftPreset"
                ),
                {},
            )
            drift_result = data_drift.get("result", {})
            return {
                "dataset_drift": drift_result.get("dataset_drift"),
                "share_drifted_features": drift_result.get("share_of_drifted_columns"),
                "total_features": drift_result.get("number_of_columns"),
            }
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
        column_mapping = self._build_column_mapping(feature_columns, has_targets)

        metrics = [DataDriftPreset()]
        if has_targets:
            metrics.extend([ClassificationPreset(), TargetDriftPreset()])

        report = Report(metrics=metrics)
        report.run(
            reference_data=reference_df,
            current_data=aligned_current,
            column_mapping=column_mapping,
        )

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        base_name = f"evidently_report_{timestamp}"
        html_path = self.reports_dir / f"{base_name}.html"
        json_path = self.reports_dir / f"{base_name}.json"

        report.save_html(html_path)
        report.save_json(json_path)

        info = MonitoringReportInfo(
            name=base_name,
            created_at=datetime.utcnow(),
            html_path=html_path,
            json_path=json_path,
            metrics_summary=self._extract_metrics_summary(report),
        )
        self.report_history.append(info)
        logger.info(
            "Generated Evidently report",
            name=info.name,
            html_path=str(html_path),
            json_path=str(json_path),
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

    def get_report_path(self, report_name: str) -> Optional[Path]:
        for report in self.report_history:
            if report.name == report_name:
                return report.html_path
        candidate = Path(self.reports_dir) / f"{report_name}.html"
        if candidate.exists():
            return candidate
        return None


_monitoring_service: Optional[EvidentlyMonitoringService] = None


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
        )
    return _monitoring_service
