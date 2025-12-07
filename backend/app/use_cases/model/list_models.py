"""List models use case."""


from app.domain.model.entities.model_info import ModelInfo
from app.domain.model.repositories.model_repository import ModelRepository


class ListModelsUseCase:
    """Use case for listing available models.

    This use case retrieves information about all available model versions.

    This follows clean architecture:
    - Depends on domain abstractions (ModelRepository)
    - Implements business logic (listing models)
    - Returns domain entities (List[ModelInfo])
    """

    def __init__(self, model_repository: ModelRepository):
        """Initialize ListModelsUseCase.

        Args:
            model_repository: Model repository for accessing models
        """
        self.model_repository = model_repository

    def execute(self) -> list[ModelInfo]:
        """List all available models.

        Returns:
            List of ModelInfo for all available models, sorted newest to oldest
        """
        versions = self.model_repository.list_available_versions()

        # Get ModelInfo for each version
        models = []
        for version in versions:
            model_info = self.model_repository.get_model_info(version)
            if model_info:
                models.append(model_info)

        return models
