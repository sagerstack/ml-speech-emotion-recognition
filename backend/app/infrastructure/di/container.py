"""Dependency injection container for clean architecture wiring.

This module provides a simple DI container that wires together:
- Infrastructure implementations (LibrosaAudioProcessor, FileSystemModelRepository, SageMakerModelRepository)
- Use cases with their dependencies
- Domain services and repositories

The container follows clean architecture principles:
- Domain layer defines interfaces (AudioProcessor, ModelRepository)
- Infrastructure layer provides implementations
- Use cases depend on abstractions, not concrete implementations

Environment-based repository selection:
- USE_SAGEMAKER=false: Uses FileSystemModelRepository (local development)
- USE_SAGEMAKER=true: Uses SageMakerModelRepository (production deployment)
"""


from app.domain.model.repositories.model_repository import ModelRepository
from app.domain.model.services.audio_processor import AudioProcessor
from app.infrastructure.config.settings import get_settings
from app.infrastructure.model.file_system_model_repository import FileSystemModelRepository
from app.infrastructure.model.librosa_audio_processor import LibrosaAudioProcessor
from app.infrastructure.model.sagemaker_model_repository import SageMakerModelRepository
from app.infrastructure.observability.logging import get_logger
from app.use_cases.model.get_model_info import GetModelInfoUseCase
from app.use_cases.model.list_models import ListModelsUseCase
from app.use_cases.model.run_inference import RunInferenceUseCase


class DIContainer:
    """Simple dependency injection container.

    This container manages the lifecycle of dependencies and wires
    together the application's components according to clean architecture.

    Usage:
        container = DIContainer()
        use_case = container.get_run_inference_use_case()
        result = use_case.execute(audio_bytes, filename)
    """

    def __init__(self, models_dir: str | None = None):
        """Initialize DI container.

        Args:
            models_dir: Path to models directory. If None, uses default location.
                       Only used for FileSystemModelRepository (local mode).
        """
        self._models_dir = models_dir
        self._logger = get_logger(__name__)

        # Singletons - created once and reused
        self._audio_processor: AudioProcessor | None = None
        self._model_repository: ModelRepository | None = None

    def get_audio_processor(self) -> AudioProcessor:
        """Get audio processor instance (singleton).

        Returns:
            LibrosaAudioProcessor instance
        """
        if self._audio_processor is None:
            self._audio_processor = LibrosaAudioProcessor()
        return self._audio_processor

    def get_model_repository(self) -> ModelRepository:
        """Get model repository instance (singleton).

        Environment-based selection:
        - USE_SAGEMAKER=false: Returns FileSystemModelRepository (local development)
        - USE_SAGEMAKER=true: Returns SageMakerModelRepository (production)

        Returns:
            ModelRepository implementation based on settings
        """
        if self._model_repository is None:
            self._model_repository = self._create_model_repository()
        return self._model_repository

    def _create_model_repository(self) -> ModelRepository:
        """Create model repository based on environment settings.

        This factory method implements the environment-based strategy pattern
        for selecting between local and production model repositories.

        Returns:
            ModelRepository implementation (FileSystemModelRepository or SageMakerModelRepository)
        """
        settings = get_settings()

        if settings.use_sagemaker:
            # Production mode: Use SageMaker endpoint
            self._logger.info(
                "Using SageMakerModelRepository (production mode)",
                endpoint_name=settings.sagemaker_endpoint_name,
                region=settings.aws_region,
            )

            return SageMakerModelRepository(
                endpoint_name=settings.sagemaker_endpoint_name,
                region=settings.aws_region,
                timeout_seconds=settings.sagemaker_timeout_seconds,
                max_retries=settings.sagemaker_max_retries,
            )
        else:
            # Local development mode: Use file system
            self._logger.info("Using FileSystemModelRepository (local mode)")

            if self._models_dir:
                return FileSystemModelRepository(models_dir=self._models_dir)
            else:
                # Use default location (backend/models)
                return FileSystemModelRepository()

    def get_run_inference_use_case(self) -> RunInferenceUseCase:
        """Get run inference use case with dependencies.

        Returns:
            RunInferenceUseCase with wired dependencies
        """
        return RunInferenceUseCase(
            audio_processor=self.get_audio_processor(),
            model_repository=self.get_model_repository(),
            logger=self._logger,
        )

    def get_model_info_use_case(self) -> GetModelInfoUseCase:
        """Get model info use case with dependencies.

        Returns:
            GetModelInfoUseCase with wired dependencies
        """
        return GetModelInfoUseCase(model_repository=self.get_model_repository())

    def get_list_models_use_case(self) -> ListModelsUseCase:
        """Get list models use case with dependencies.

        Returns:
            ListModelsUseCase with wired dependencies
        """
        return ListModelsUseCase(model_repository=self.get_model_repository())


# Global container instance (singleton)
_container: DIContainer | None = None


def get_container(models_dir: str | None = None) -> DIContainer:
    """Get or create the global DI container.

    Args:
        models_dir: Path to models directory (only used on first call)

    Returns:
        Global DIContainer instance
    """
    global _container
    if _container is None:
        _container = DIContainer(models_dir=models_dir)
    return _container


def reset_container() -> None:
    """Reset the global container (mainly for testing).

    This allows tests to create fresh containers with different configurations.
    """
    global _container
    _container = None
