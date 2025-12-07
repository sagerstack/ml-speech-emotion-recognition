"""Use case for saving predictions."""

from app.domain.monitoring.entities.prediction import Prediction
from app.domain.monitoring.repositories.prediction_repository import (
    PredictionRepository,
)


class SavePredictionUseCase:
    """Save prediction after inference."""

    def __init__(self, prediction_repository: PredictionRepository):
        """Initialize use case.

        Args:
            prediction_repository: Repository for managing predictions
        """
        self._repository = prediction_repository

    def execute(self, prediction: Prediction) -> Prediction:
        """Execute use case to save prediction.

        Args:
            prediction: Prediction to save

        Returns:
            Saved prediction
        """
        return self._repository.save(prediction)
