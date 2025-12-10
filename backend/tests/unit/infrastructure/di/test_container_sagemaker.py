"""Unit tests for DI container SageMaker integration."""

from unittest.mock import patch

import pytest

from app.infrastructure.di.container import DIContainer
from app.infrastructure.model.file_system_model_repository import FileSystemModelRepository
from app.infrastructure.model.sagemaker_model_repository import SageMakerModelRepository


class TestDIContainerSageMaker:
    """Test suite for DI container SageMaker repository selection."""

    @pytest.fixture
    def mock_settings_local(self):
        """Mock settings for local development mode."""
        with patch("app.infrastructure.di.container.get_settings") as mock_get_settings:
            mock_settings = mock_get_settings.return_value
            mock_settings.use_sagemaker = False
            yield mock_settings

    @pytest.fixture
    def mock_settings_production(self):
        """Mock settings for production mode with SageMaker."""
        with patch("app.infrastructure.di.container.get_settings") as mock_get_settings:
            mock_settings = mock_get_settings.return_value
            mock_settings.use_sagemaker = True
            mock_settings.sagemaker_endpoint_name = "ml-ser-endpoint4"
            mock_settings.aws_region = "us-east-1"
            mock_settings.sagemaker_timeout_seconds = 30
            mock_settings.sagemaker_max_retries = 3
            yield mock_settings

    @pytest.fixture
    def mock_boto3_client(self):
        """Mock boto3 client for SageMaker."""
        with patch("app.infrastructure.model.sagemaker_model_repository.boto3") as mock_boto3:
            mock_client = mock_boto3.client.return_value
            yield mock_client

    def test_get_model_repository_local_mode(self, mock_settings_local):
        """Test repository factory returns FileSystemModelRepository in local mode."""
        container = DIContainer()
        repository = container.get_model_repository()

        assert isinstance(repository, FileSystemModelRepository)
        assert not isinstance(repository, SageMakerModelRepository)

    def test_get_model_repository_production_mode(
        self, mock_settings_production, mock_boto3_client
    ):
        """Test repository factory returns SageMakerModelRepository in production mode."""
        container = DIContainer()
        repository = container.get_model_repository()

        assert isinstance(repository, SageMakerModelRepository)
        assert repository.endpoint_name == "ml-ser-endpoint4"
        assert repository.region == "us-east-1"
        assert repository.timeout_seconds == 30
        assert repository.max_retries == 3

    def test_get_model_repository_caching(self, mock_settings_local):
        """Test repository is cached after first call."""
        container = DIContainer()

        repo1 = container.get_model_repository()
        repo2 = container.get_model_repository()

        # Should return same instance
        assert repo1 is repo2

    def test_get_model_repository_local_with_custom_dir(self, mock_settings_local):
        """Test local repository with custom models directory."""
        container = DIContainer(models_dir="/custom/models")
        repository = container.get_model_repository()

        assert isinstance(repository, FileSystemModelRepository)
        # Note: Can't easily test internal _models_dir, but we verified it's FileSystem

    def test_run_inference_use_case_gets_correct_repository(
        self, mock_settings_production, mock_boto3_client
    ):
        """Test RunInferenceUseCase gets SageMaker repository in production mode."""
        container = DIContainer()
        use_case = container.get_run_inference_use_case()

        # Verify use case is wired with correct repository
        assert isinstance(use_case.model_repository, SageMakerModelRepository)
        assert use_case.audio_processor is not None
        assert use_case.logger is not None

    def test_get_model_info_use_case(self, mock_settings_local):
        """Test GetModelInfoUseCase is wired with correct repository."""
        container = DIContainer()
        use_case = container.get_model_info_use_case()

        assert use_case.model_repository is not None
        assert isinstance(use_case.model_repository, FileSystemModelRepository)

    def test_get_list_models_use_case(self, mock_settings_local):
        """Test ListModelsUseCase is wired with correct repository."""
        container = DIContainer()
        use_case = container.get_list_models_use_case()

        assert use_case.model_repository is not None
        assert isinstance(use_case.model_repository, FileSystemModelRepository)


class TestContainerGlobalFunctions:
    """Test global container functions."""

    @pytest.fixture(autouse=True)
    def reset_global_container(self):
        """Reset global container before and after each test."""
        from app.infrastructure.di.container import reset_container
        reset_container()
        yield
        reset_container()

    @pytest.fixture
    def mock_settings_local(self):
        """Mock settings for local development mode."""
        with patch("app.infrastructure.di.container.get_settings") as mock_get_settings:
            mock_settings = mock_get_settings.return_value
            mock_settings.use_sagemaker = False
            yield mock_settings

    def test_get_container_creates_singleton(self, mock_settings_local):
        """Test get_container creates and returns singleton."""
        from app.infrastructure.di.container import get_container

        container1 = get_container()
        container2 = get_container()

        assert container1 is container2
        assert isinstance(container1, DIContainer)

    def test_get_container_with_models_dir(self, mock_settings_local):
        """Test get_container accepts models_dir on first call."""
        from app.infrastructure.di.container import get_container

        container = get_container(models_dir="/custom/path")

        assert container._models_dir == "/custom/path"

    def test_reset_container_clears_singleton(self, mock_settings_local):
        """Test reset_container clears the global singleton."""
        from app.infrastructure.di.container import get_container, reset_container

        container1 = get_container()
        reset_container()
        container2 = get_container()

        # After reset, should be a new instance
        assert container1 is not container2
