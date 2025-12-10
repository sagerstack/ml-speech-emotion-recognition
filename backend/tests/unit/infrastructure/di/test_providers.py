"""
Unit tests for FastAPI dependency providers.

Tests the dependency injection providers including:
- Audio processor provider
- Model repository provider
- Use case providers
"""

from unittest.mock import Mock, patch

import pytest

from app.infrastructure.di.providers import (
    get_audio_processor,
    get_log_prediction_for_monitoring_use_case,
    get_list_models_use_case,
    get_model_info_use_case,
    get_model_repository,
    get_model_versions_use_case,
    get_run_inference_use_case,
)
from app.use_cases.model.get_model_info import GetModelInfoUseCase
from app.use_cases.model.get_model_versions import GetModelVersionsUseCase
from app.use_cases.model.list_models import ListModelsUseCase
from app.use_cases.model.run_inference import RunInferenceUseCase
from app.use_cases.monitoring.log_prediction_for_monitoring import LogPredictionForMonitoringUseCase


class TestGetAudioProcessor:
    """Test get_audio_processor provider."""

    @patch("app.infrastructure.di.providers.get_container")
    def test_get_audio_processor(self, mock_get_container):
        """Test getting audio processor from container."""
        mock_container = Mock()
        mock_audio_processor = Mock()
        mock_container.get_audio_processor.return_value = mock_audio_processor
        mock_get_container.return_value = mock_container

        result = get_audio_processor()

        assert result == mock_audio_processor
        mock_container.get_audio_processor.assert_called_once()


class TestGetModelRepository:
    """Test get_model_repository provider."""

    @patch("app.infrastructure.di.providers.get_container")
    def test_get_model_repository(self, mock_get_container):
        """Test getting model repository from container."""
        mock_container = Mock()
        mock_model_repository = Mock()
        mock_container.get_model_repository.return_value = mock_model_repository
        mock_get_container.return_value = mock_container

        result = get_model_repository()

        assert result == mock_model_repository
        mock_container.get_model_repository.assert_called_once()


class TestGetLogPredictionForMonitoringUseCase:
    """Test get_log_prediction_for_monitoring_use_case provider."""

    @patch("app.infrastructure.di.providers.get_logger")
    def test_get_log_prediction_for_monitoring_use_case(self, mock_get_logger):
        """Test creating LogPredictionForMonitoringUseCase."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        mock_monitoring_service = Mock()

        result = get_log_prediction_for_monitoring_use_case(
            monitoring_service=mock_monitoring_service
        )

        assert isinstance(result, LogPredictionForMonitoringUseCase)
        mock_get_logger.assert_called_once_with(
            "app.use_cases.monitoring.log_prediction_for_monitoring"
        )

    @patch("app.infrastructure.di.providers.get_logger")
    def test_get_log_prediction_for_monitoring_use_case_without_service(self, mock_get_logger):
        """Test creating use case without monitoring service."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        result = get_log_prediction_for_monitoring_use_case(monitoring_service=None)

        assert isinstance(result, LogPredictionForMonitoringUseCase)


class TestGetRunInferenceUseCase:
    """Test get_run_inference_use_case provider."""

    @patch("app.infrastructure.di.providers.get_logger")
    def test_get_run_inference_use_case(self, mock_get_logger):
        """Test creating RunInferenceUseCase."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        mock_audio_processor = Mock()
        mock_model_repository = Mock()
        mock_log_prediction_use_case = Mock()

        result = get_run_inference_use_case(
            audio_processor=mock_audio_processor,
            model_repository=mock_model_repository,
            log_prediction_use_case=mock_log_prediction_use_case,
        )

        assert isinstance(result, RunInferenceUseCase)
        mock_get_logger.assert_called_once_with("app.use_cases.model.run_inference")


class TestGetModelInfoUseCase:
    """Test get_model_info_use_case provider."""

    def test_get_model_info_use_case(self):
        """Test creating GetModelInfoUseCase."""
        mock_model_repository = Mock()

        result = get_model_info_use_case(model_repository=mock_model_repository)

        assert isinstance(result, GetModelInfoUseCase)


class TestGetListModelsUseCase:
    """Test get_list_models_use_case provider."""

    def test_get_list_models_use_case(self):
        """Test creating ListModelsUseCase."""
        mock_model_repository = Mock()

        result = get_list_models_use_case(model_repository=mock_model_repository)

        assert isinstance(result, ListModelsUseCase)


class TestGetModelVersionsUseCase:
    """Test get_model_versions_use_case provider."""

    def test_get_model_versions_use_case(self):
        """Test creating GetModelVersionsUseCase."""
        mock_model_repository = Mock()

        result = get_model_versions_use_case(model_repository=mock_model_repository)

        assert isinstance(result, GetModelVersionsUseCase)
