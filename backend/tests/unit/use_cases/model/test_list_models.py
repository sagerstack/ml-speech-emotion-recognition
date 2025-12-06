"""Unit tests for ListModelsUseCase."""

from unittest.mock import Mock

import pytest

from app.domain.model.entities.model_info import ModelInfo
from app.domain.model.value_objects.model_version import ModelVersion
from app.use_cases.model.list_models import ListModelsUseCase


class TestListModelsUseCase:
    """Test suite for ListModelsUseCase."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock model repository."""
        repository = Mock()

        # Mock list_available_versions to return versions
        v3 = ModelVersion.from_string("v3")
        v4 = ModelVersion.from_string("v4")
        repository.list_available_versions = Mock(return_value=[v4, v3])

        # Mock get_model_info to return ModelInfo
        def get_info(version):
            return ModelInfo(version=version, model_type="Test Model", feature_dimension=210)

        repository.get_model_info = Mock(side_effect=get_info)
        return repository

    @pytest.fixture
    def use_case(self, mock_repository):
        """Create ListModelsUseCase instance."""
        return ListModelsUseCase(mock_repository)

    def test_execute_returns_list_of_model_info(self, use_case: ListModelsUseCase):
        """Test that execute returns list of ModelInfo."""
        result = use_case.execute()

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(info, ModelInfo) for info in result)

    def test_execute_calls_repository(self, use_case: ListModelsUseCase, mock_repository: Mock):
        """Test that execute calls repository methods."""
        use_case.execute()

        mock_repository.list_available_versions.assert_called_once()
        # Should call get_model_info for each version
        assert mock_repository.get_model_info.call_count == 2

    def test_execute_returns_empty_list_when_no_models(
        self, use_case: ListModelsUseCase, mock_repository: Mock
    ):
        """Test that execute returns empty list when no models available."""
        mock_repository.list_available_versions.return_value = []

        result = use_case.execute()

        assert result == []

    def test_execute_filters_out_none_results(
        self, use_case: ListModelsUseCase, mock_repository: Mock
    ):
        """Test that execute filters out None results from get_model_info."""
        v3 = ModelVersion.from_string("v3")
        v4 = ModelVersion.from_string("v4")
        mock_repository.list_available_versions.return_value = [v4, v3]

        # Make one return None
        def get_info(version):
            if str(version) == "v3":
                return None
            return ModelInfo(version=version, model_type="Test Model", feature_dimension=210)

        mock_repository.get_model_info = Mock(side_effect=get_info)

        result = use_case.execute()

        assert len(result) == 1
        assert str(result[0].version) == "v4"
