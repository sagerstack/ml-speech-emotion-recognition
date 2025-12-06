"""Prediction repository interface."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.monitoring.entities.prediction import Prediction


class PredictionRepository(ABC):
    """Abstract repository for managing predictions."""

    @abstractmethod
    def save(self, prediction: Prediction) -> Prediction:
        """Save a prediction.

        Args:
            prediction: Prediction to save

        Returns:
            Saved prediction
        """
        pass

    @abstractmethod
    def get_by_id(self, prediction_id: UUID) -> Prediction | None:
        """Get prediction by ID.

        Args:
            prediction_id: UUID of prediction

        Returns:
            Prediction if found, None otherwise
        """
        pass

    @abstractmethod
    def update_actual_emotion(
        self, prediction_id: UUID, actual_emotion: str
    ) -> Prediction | None:
        """Update actual emotion for a prediction.

        Args:
            prediction_id: UUID of prediction
            actual_emotion: Actual emotion label

        Returns:
            Updated prediction if found, None otherwise
        """
        pass

    @abstractmethod
    def get_all(self) -> list[Prediction]:
        """Get all predictions.

        Returns:
            List of all predictions
        """
        pass
