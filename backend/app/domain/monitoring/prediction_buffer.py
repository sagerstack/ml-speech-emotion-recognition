"""In-memory prediction buffer for Evidently monitoring."""

import uuid
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime
from threading import Lock

import pandas as pd

from app.utils.config import get_settings
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class PredictionRecord:
    """Structured prediction record for monitoring."""

    timestamp: datetime
    model_version: str
    predicted_emotion: str
    confidence: float
    probabilities: dict[str, float]
    features: dict[str, float]
    actual_emotion: str | None = None
    filename: str | None = None
    prediction_id: str = None  # Unique identifier for feedback tracking
    api_version: str = "v1"  # API endpoint version (v1 or v2)

    def __post_init__(self):
        """Generate prediction ID if not provided."""
        if self.prediction_id is None:
            self.prediction_id = str(uuid.uuid4())

    def to_row(self) -> dict[str, object]:
        """Convert record to a flat dictionary for DataFrame creation."""

        row: dict[str, object] = {
            "prediction_id": self.prediction_id,
            "timestamp": self.timestamp,
            "model_version": self.model_version,
            "api_version": self.api_version,
            "predicted_emotion": self.predicted_emotion,
            "actual_emotion": self.actual_emotion,
            "confidence": self.confidence,
            "filename": self.filename,
        }

        row.update(self.features)
        row.update({f"proba_{label}": prob for label, prob in self.probabilities.items()})
        return row


class PredictionBuffer:
    """Thread-safe in-memory buffer for recent predictions."""

    def __init__(self, max_records: int):
        self._buffer: deque[PredictionRecord] = deque(maxlen=max_records)
        self._lock = Lock()
        self.max_records = max_records

    def add(self, record: PredictionRecord) -> int:
        """Add a prediction record to the buffer.

        Returns the current buffer length after insertion.
        """

        with self._lock:
            self._buffer.append(record)
            return len(self._buffer)

    def update_feedback(self, prediction_id: str, actual_emotion: str) -> bool:
        """Update the actual_emotion field for a given prediction ID.

        Returns True if the prediction was found and updated, False otherwise.
        """

        with self._lock:
            for record in self._buffer:
                if record.prediction_id == prediction_id:
                    record.actual_emotion = actual_emotion
                    logger.info(
                        "Updated feedback for prediction",
                        prediction_id=prediction_id,
                        actual_emotion=actual_emotion,
                    )
                    return True

        logger.warning("Prediction not found for feedback", prediction_id=prediction_id)
        return False

    def to_dataframe(self) -> pd.DataFrame:
        """Export buffered records to a pandas DataFrame."""

        with self._lock:
            rows = [record.to_row() for record in list(self._buffer)]

        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows)

    def stats(self) -> dict[str, object]:
        """Return high-level buffer statistics."""

        with self._lock:
            total = len(self._buffer)
            versions = Counter(record.model_version for record in self._buffer)
            api_versions = Counter(record.api_version for record in self._buffer)
            latest_ts = self._buffer[-1].timestamp if self._buffer else None

        return {
            "total_records": total,
            "by_version": dict(versions),
            "by_api_version": dict(api_versions),
            "max_records": self.max_records,
            "latest_timestamp": latest_ts.isoformat() if latest_ts else None,
        }

    def __len__(self) -> int:  # pragma: no cover - trivial
        return len(self._buffer)


_buffer: PredictionBuffer | None = None


def get_prediction_buffer() -> PredictionBuffer:
    """Get the global prediction buffer instance."""

    global _buffer
    if _buffer is None:
        settings = get_settings()
        _buffer = PredictionBuffer(max_records=settings.monitoring_buffer_max_records)
        logger.info(
            "Initialized prediction buffer", max_records=settings.monitoring_buffer_max_records
        )
    return _buffer
