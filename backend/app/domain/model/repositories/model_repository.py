"""Model repository interface."""

from abc import ABC, abstractmethod

from app.domain.model.entities.emotion_model import EmotionModel
from app.domain.model.entities.model_info import ModelInfo
from app.domain.model.value_objects.model_version import ModelVersion


class ModelRepository(ABC):
    """Abstract interface for model persistence operations.

    This repository defines the contract for loading and managing
    ML models. The actual implementation (loading from disk, S3, etc.)
    will be in the infrastructure layer.

    The interface follows the Dependency Inversion Principle (DIP) -
    the domain defines what it needs, and infrastructure provides
    the implementation.
    """

    @abstractmethod
    def load_model(self, version: ModelVersion) -> EmotionModel:
        """Load a trained model by version.

        Loads the serialized model from storage (e.g., disk, S3)
        and returns it wrapped in the domain's EmotionModel interface.

        The infrastructure layer is responsible for:
        - Loading the model from storage (pickle, S3, etc.)
        - Wrapping it in an appropriate adapter (e.g., SklearnEmotionModelAdapter)
        - Returning an object that implements EmotionModel interface

        Args:
            version: Model version to load

        Returns:
            EmotionModel: Domain model interface ready for inference.
                         NOT the raw pickle object, but an adapter that implements
                         the domain interface.

        Raises:
            ModelNotFoundError: If model version doesn't exist
            InferenceError: If model loading fails
        """
        pass

    @abstractmethod
    def get_model_info(self, version: ModelVersion) -> ModelInfo | None:
        """Get metadata about a model version.

        Retrieves information about a model without loading the full model.
        Useful for validation and displaying available models.

        Args:
            version: Model version to get info for

        Returns:
            ModelInfo if model exists, None otherwise
        """
        pass

    @abstractmethod
    def list_available_versions(self) -> list[ModelVersion]:
        """List all available model versions.

        Returns:
            List of available model versions, sorted from newest to oldest
        """
        pass

    @abstractmethod
    def model_exists(self, version: ModelVersion) -> bool:
        """Check if a model version exists.

        Args:
            version: Model version to check

        Returns:
            True if model exists and can be loaded
        """
        pass

    @abstractmethod
    def get_latest_version(self) -> ModelVersion | None:
        """Get the latest available model version.

        Returns:
            Latest ModelVersion if any models exist, None otherwise
        """
        pass
