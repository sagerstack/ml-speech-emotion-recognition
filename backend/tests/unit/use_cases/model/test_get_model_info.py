"""Unit tests for GetModelInfoUseCase."""

from unittest.mock import Mock

import pytest

from app.domain.model.entities.model_info import ModelInfo
from app.use_cases.model.get_model_info import GetModelInfoUseCase


class TestGetModelInfoUseCase:
    """Test suite for GetModelInfoUseCase."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock model repository."""
        repository = Mock()
        # Mock get_model_info to return a ModelInfo
        mock_info = ModelInfo.v4_model()
        repository.get_model_info = Mock(return_value=mock_info)
        return repository

    @pytest.fixture
    def use_case(self, mock_repository):
        """Create GetModelInfoUseCase instance."""
        return GetModelInfoUseCase(mock_repository)

    def test_execute_returns_model_info(self, use_case: GetModelInfoUseCase):
        """Test that execute returns ModelInfo."""
        result = use_case.execute("v4")

        assert result is not None
        assert isinstance(result, ModelInfo)

    def test_execute_calls_repository(self, use_case: GetModelInfoUseCase, mock_repository: Mock):
        """Test that execute calls repository with correct version."""
        use_case.execute("v4")

        mock_repository.get_model_info.assert_called_once()
        version = mock_repository.get_model_info.call_args[0][0]
        assert str(version) == "v4"

    def test_execute_returns_none_for_nonexistent_model(
        self, use_case: GetModelInfoUseCase, mock_repository: Mock
    ):
        """Test that execute returns None for nonexistent model."""
        mock_repository.get_model_info.return_value = None

        result = use_case.execute("v999")

        assert result is None

    def test_execute_handles_version_without_v_prefix(
        self, use_case: GetModelInfoUseCase, mock_repository: Mock
    ):
        """Test that execute handles version strings without 'v' prefix."""
        use_case.execute("4")

        mock_repository.get_model_info.assert_called_once()
        version = mock_repository.get_model_info.call_args[0][0]
        assert str(version) == "v4"
