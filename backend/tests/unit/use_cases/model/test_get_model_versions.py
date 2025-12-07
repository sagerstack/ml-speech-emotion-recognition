"""Unit tests for GetModelVersionsUseCase."""

from unittest.mock import Mock

import pytest

from app.domain.model.value_objects.model_version import ModelVersion
from app.use_cases.model.get_model_versions import GetModelVersionsUseCase


class TestGetModelVersionsUseCase:
    """Test suite for GetModelVersionsUseCase."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock model repository."""
        repository = Mock()
        # Mock list_available_versions to return sorted versions
        repository.list_available_versions = Mock(
            return_value=[
                ModelVersion.from_string("v4"),
                ModelVersion.from_string("v3"),
                ModelVersion.from_string("v2"),
                ModelVersion.from_string("v1"),
            ]
        )
        # Mock get_latest_version
        repository.get_latest_version = Mock(return_value=ModelVersion.from_string("v4"))
        return repository

    @pytest.fixture
    def use_case(self, mock_repository):
        """Create GetModelVersionsUseCase instance."""
        return GetModelVersionsUseCase(mock_repository)

    def test_execute_returns_all_versions(self, use_case: GetModelVersionsUseCase):
        """Test that execute returns list of all model versions."""
        result = use_case.execute()

        assert result is not None
        assert "versions" in result
        assert "latest" in result
        assert "count" in result

    def test_execute_calls_repository(
        self, use_case: GetModelVersionsUseCase, mock_repository: Mock
    ):
        """Test that execute calls repository methods."""
        use_case.execute()

        mock_repository.list_available_versions.assert_called_once()
        mock_repository.get_latest_version.assert_called_once()

    def test_execute_returns_correct_version_list(
        self, use_case: GetModelVersionsUseCase, mock_repository: Mock
    ):
        """Test that execute returns versions as strings in correct order."""
        result = use_case.execute()

        assert result["versions"] == ["v4", "v3", "v2", "v1"]
        assert result["latest"] == "v4"
        assert result["count"] == 4

    def test_execute_returns_empty_list_when_no_models(
        self, use_case: GetModelVersionsUseCase, mock_repository: Mock
    ):
        """Test that execute returns empty list when no models exist."""
        mock_repository.list_available_versions.return_value = []
        mock_repository.get_latest_version.return_value = None

        result = use_case.execute()

        assert result["versions"] == []
        assert result["latest"] is None
        assert result["count"] == 0

    def test_execute_handles_single_version(
        self, use_case: GetModelVersionsUseCase, mock_repository: Mock
    ):
        """Test that execute handles single version correctly."""
        mock_repository.list_available_versions.return_value = [
            ModelVersion.from_string("v1")
        ]
        mock_repository.get_latest_version.return_value = ModelVersion.from_string("v1")

        result = use_case.execute()

        assert result["versions"] == ["v1"]
        assert result["latest"] == "v1"
        assert result["count"] == 1

    def test_execute_preserves_version_order(
        self, use_case: GetModelVersionsUseCase, mock_repository: Mock
    ):
        """Test that execute preserves the order returned by repository."""
        # Repository returns in descending order (newest first)
        expected_versions = [
            ModelVersion.from_string("v10"),
            ModelVersion.from_string("v5"),
            ModelVersion.from_string("v3"),
        ]
        mock_repository.list_available_versions.return_value = expected_versions
        mock_repository.get_latest_version.return_value = expected_versions[0]

        result = use_case.execute()

        assert result["versions"] == ["v10", "v5", "v3"]
        assert result["latest"] == "v10"
        assert result["count"] == 3
