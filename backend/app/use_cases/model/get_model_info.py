"""Get model info use case."""


from app.domain.model.entities.model_info import ModelInfo
from app.domain.model.repositories.model_repository import ModelRepository
from app.domain.model.value_objects.model_version import ModelVersion


class GetModelInfoUseCase:
    """Use case for getting model metadata.

    This use case retrieves information about a specific model version
    without loading the actual model file.

    This follows clean architecture:
    - Depends on domain abstractions (ModelRepository)
    - Implements business logic (retrieving model info)
    - Returns domain entities (ModelInfo)
    """

    def __init__(self, model_repository: ModelRepository):
        """Initialize GetModelInfoUseCase.

        Args:
            model_repository: Model repository for accessing model info
        """
        self.model_repository = model_repository

    def execute(self, version: str) -> ModelInfo | None:
        """Get model information by version.

        Args:
            version: Model version string (e.g., "v4", "4")

        Returns:
            ModelInfo if model exists, None otherwise
        """
        model_version = ModelVersion.from_string(version)
        return self.model_repository.get_model_info(model_version)
