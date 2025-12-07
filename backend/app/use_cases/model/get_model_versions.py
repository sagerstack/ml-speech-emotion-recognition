"""Get model versions use case."""


from app.domain.model.repositories.model_repository import ModelRepository


class GetModelVersionsUseCase:
    """Use case for getting all available model versions.

    This use case retrieves a list of all available model versions
    along with the latest version and total count.

    This follows clean architecture:
    - Depends on domain abstractions (ModelRepository)
    - Implements business logic (listing versions)
    - Returns data in a structured format
    """

    def __init__(self, model_repository: ModelRepository):
        """Initialize GetModelVersionsUseCase.

        Args:
            model_repository: Model repository for accessing model versions
        """
        self.model_repository = model_repository

    def execute(self) -> dict[str, list[str] | str | int | None]:
        """Get all available model versions.

        Returns:
            Dictionary containing:
            - versions: List of version strings (e.g., ["v4", "v3", "v2", "v1"])
            - latest: Latest version string (e.g., "v4") or None
            - count: Total number of versions
        """
        # Get all available versions from repository
        version_objects = self.model_repository.list_available_versions()

        # Get latest version
        latest_version_obj = self.model_repository.get_latest_version()

        # Convert ModelVersion objects to strings
        version_strings = [str(version) for version in version_objects]
        latest_string = str(latest_version_obj) if latest_version_obj else None

        return {
            "versions": version_strings,
            "latest": latest_string,
            "count": len(version_strings),
        }
