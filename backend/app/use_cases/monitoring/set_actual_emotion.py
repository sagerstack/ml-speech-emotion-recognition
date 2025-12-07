"""Use case for setting actual emotion (feedback)."""

from uuid import UUID

from app.domain.monitoring.entities.prediction import Prediction
from app.domain.monitoring.repositories.prediction_repository import (
    PredictionRepository,
)


class SetActualEmotionUseCase:
    """Update prediction with actual emotion (feedback)."""

    def __init__(self, prediction_repository: PredictionRepository):
        """Initialize use case.

        Args:
            prediction_repository: Repository for managing predictions
        """
        self._repository = prediction_repository

    def execute(self, prediction_id: UUID, actual_emotion: str) -> Prediction | None:
        """Execute use case to set actual emotion.

        Args:
            prediction_id: UUID of prediction
            actual_emotion: Actual emotion label

        Returns:
            Updated prediction if found, None otherwise
        """
        return self._repository.update_actual_emotion(prediction_id, actual_emotion)
