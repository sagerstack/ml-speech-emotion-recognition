"""Use case for logging predictions to monitoring service."""

import uuid
from datetime import datetime
from typing import Any

from app.domain.model.value_objects.emotion import Emotion
from app.domain.monitoring.prediction_buffer import PredictionRecord
from app.infrastructure.monitoring.evidently_service import EvidentlyService


class LogPredictionForMonitoringUseCase:
    """Use case for logging prediction data to monitoring service.

    This use case handles:
    1. Generating a unique prediction ID
    2. Creating a PredictionRecord from inference data
    3. Logging to EvidentlyService
    4. Graceful error handling (monitoring should not break inference)

    Following clean architecture:
    - Depends on domain abstractions (EvidentlyService)
    - Returns simple types (prediction_id as string)
    - Handles errors gracefully without propagating exceptions
    """

    def __init__(self, monitoring_service: EvidentlyService | None, logger: Any):
        """Initialize LogPredictionForMonitoringUseCase.

        Args:
            monitoring_service: Evidently monitoring service for logging predictions (None if disabled)
            logger: Structlog logger instance for structured logging
        """
        self.monitoring_service = monitoring_service
        self.logger = logger

    def execute(
        self,
        emotion: Emotion,
        confidence: float,
        probabilities: dict[Emotion, float],
        features: dict[str, float],
        audio_bytes: bytes,
        filename: str,
        model_version: str,
        api_version: str = "v1",
    ) -> str:
        """Execute monitoring logging for a prediction.

        Args:
            emotion: Predicted emotion
            confidence: Confidence score (0.0 to 1.0)
            probabilities: Probability distribution over all emotions
            features: Extracted audio features
            audio_bytes: Raw audio data (for future use)
            filename: Original filename
            model_version: Model version used for prediction
            api_version: API endpoint version (v1 or v2)

        Returns:
            prediction_id: Unique identifier for this prediction (UUID)
                          Returns empty string if logging fails or monitoring is disabled
        """
        # If monitoring is disabled, return empty prediction_id
        if self.monitoring_service is None:
            return ""

        try:
            # Generate unique prediction ID
            prediction_id = str(uuid.uuid4())

            # Convert Emotion enums to strings for monitoring
            probabilities_str = {e.value: p for e, p in probabilities.items()}

            # Create prediction record
            record = PredictionRecord(
                timestamp=datetime.utcnow(),
                model_version=model_version,
                api_version=api_version,
                predicted_emotion=emotion.value,
                confidence=confidence,
                probabilities=probabilities_str,
                features=features,
                filename=filename,
                prediction_id=prediction_id,
            )

            # Log to monitoring service
            buffer_length = self.monitoring_service.log_prediction(record)

            self.logger.info(
                "Prediction logged to monitoring service",
                prediction_id=prediction_id,
                emotion=emotion.value,
                confidence=confidence,
                buffer_length=buffer_length,
                api_version=api_version,
            )

            return prediction_id

        except Exception as exc:
            # Monitoring errors should not break inference
            # Log warning and return empty string
            self.logger.warning(
                "Monitoring logging failed",
                error=str(exc),
                filename=filename,
                model_version=model_version,
            )
            return ""

    def _trigger_auto_report(self, buffer_length: int) -> None:
        """Trigger automatic report generation in background.

        This method generates Evidently reports when the buffer reaches
        the configured threshold. Report generation errors are logged
        but do not affect inference.

        Args:
            buffer_length: Current number of predictions in buffer
        """
        try:
            self.logger.info(
                "Auto-generating Evidently report",
                buffer_length=buffer_length,
            )
            report_info = self.monitoring_service.generate_report()
            self.logger.info(
                "Auto-generated Evidently report successfully",
                report_name=report_info.name,
                html_path=str(report_info.html_path),
                buffer_length=buffer_length,
            )
        except Exception as exc:
            # Report generation errors should not break inference
            self.logger.warning(
                "Auto-report generation failed",
                error=str(exc),
                buffer_length=buffer_length,
            )
