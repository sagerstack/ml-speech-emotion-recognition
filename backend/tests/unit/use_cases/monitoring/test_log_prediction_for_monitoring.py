"""Tests for LogPredictionForMonitoringUseCase."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.domain.model.value_objects.emotion import Emotion
from app.domain.monitoring.prediction_buffer import PredictionRecord
from app.infrastructure.monitoring.evidently_service import EvidentlyService
from app.use_cases.monitoring.log_prediction_for_monitoring import (
    LogPredictionForMonitoringUseCase,
)


class TestLogPredictionForMonitoringUseCase:
    """Test suite for LogPredictionForMonitoringUseCase."""

    @pytest.fixture
    def mock_monitoring_service(self):
        """Create mock EvidentlyService."""
        service = MagicMock(spec=EvidentlyService)
        service.log_prediction.return_value = 10  # Mock buffer length
        return service

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger."""
        return MagicMock()

    @pytest.fixture
    def use_case(self, mock_monitoring_service, mock_logger):
        """Create LogPredictionForMonitoringUseCase instance."""
        return LogPredictionForMonitoringUseCase(
            monitoring_service=mock_monitoring_service,
            logger=mock_logger,
        )

    def test_execute_logs_prediction_successfully(self, use_case, mock_monitoring_service):
        """Test that execute logs prediction and returns prediction_id."""
        # Arrange
        emotion = Emotion.HAPPY
        confidence = 0.92
        probabilities = {
            Emotion.ANGRY: 0.01,
            Emotion.DISGUST: 0.02,
            Emotion.FEAR: 0.03,
            Emotion.HAPPY: 0.92,
            Emotion.NEUTRAL: 0.01,
            Emotion.SAD: 0.01,
        }
        features = {"feature_1": 0.5, "feature_2": 1.2}
        audio_bytes = b"fake_audio_data"
        filename = "test.wav"
        model_version = "v5"

        # Act
        prediction_id = use_case.execute(
            emotion=emotion,
            confidence=confidence,
            probabilities=probabilities,
            features=features,
            audio_bytes=audio_bytes,
            filename=filename,
            model_version=model_version,
        )

        # Assert
        assert prediction_id is not None
        assert isinstance(prediction_id, str)
        assert len(prediction_id) == 36  # UUID format

        # Verify monitoring service was called
        mock_monitoring_service.log_prediction.assert_called_once()
        call_args = mock_monitoring_service.log_prediction.call_args[0]
        record = call_args[0]

        assert isinstance(record, PredictionRecord)
        assert record.predicted_emotion == emotion.value
        assert record.confidence == confidence
        assert record.probabilities == {e.value: p for e, p in probabilities.items()}
        assert record.features == features
        assert record.filename == filename
        assert record.model_version == model_version
        assert record.api_version == "v1"  # Default api_version
        assert record.prediction_id == prediction_id

    def test_execute_logs_prediction_with_v2_api_version(self, use_case, mock_monitoring_service):
        """Test that execute logs prediction with v2 api_version."""
        # Arrange
        emotion = Emotion.HAPPY
        confidence = 0.92
        probabilities = {
            Emotion.ANGRY: 0.01,
            Emotion.DISGUST: 0.02,
            Emotion.FEAR: 0.03,
            Emotion.HAPPY: 0.92,
            Emotion.NEUTRAL: 0.01,
            Emotion.SAD: 0.01,
        }
        features = {"feature_1": 0.5, "feature_2": 1.2}
        audio_bytes = b"fake_audio_data"
        filename = "test.wav"
        model_version = "v5"
        api_version = "v2"

        # Act
        prediction_id = use_case.execute(
            emotion=emotion,
            confidence=confidence,
            probabilities=probabilities,
            features=features,
            audio_bytes=audio_bytes,
            filename=filename,
            model_version=model_version,
            api_version=api_version,
        )

        # Assert
        assert prediction_id is not None
        assert isinstance(prediction_id, str)

        # Verify monitoring service was called with v2 api_version
        mock_monitoring_service.log_prediction.assert_called_once()
        call_args = mock_monitoring_service.log_prediction.call_args[0]
        record = call_args[0]

        assert isinstance(record, PredictionRecord)
        assert record.api_version == "v2"
        assert record.model_version == model_version

    def test_execute_handles_monitoring_error_gracefully(
        self, use_case, mock_monitoring_service, mock_logger
    ):
        """Test that monitoring errors don't fail the use case."""
        # Arrange
        mock_monitoring_service.log_prediction.side_effect = Exception("Monitoring service error")

        emotion = Emotion.HAPPY
        confidence = 0.92
        probabilities = {
            Emotion.ANGRY: 0.01,
            Emotion.DISGUST: 0.02,
            Emotion.FEAR: 0.03,
            Emotion.HAPPY: 0.92,
            Emotion.NEUTRAL: 0.01,
            Emotion.SAD: 0.01,
        }
        features = {"feature_1": 0.5}
        audio_bytes = b"data"
        filename = "test.wav"
        model_version = "v5"

        # Act
        prediction_id = use_case.execute(
            emotion=emotion,
            confidence=confidence,
            probabilities=probabilities,
            features=features,
            audio_bytes=audio_bytes,
            filename=filename,
            model_version=model_version,
        )

        # Assert - should return empty string on error
        assert prediction_id == ""

        # Verify error was logged
        mock_logger.warning.assert_called_once()
        assert "Monitoring logging failed" in str(mock_logger.warning.call_args)

    def test_execute_with_minimal_data(self, use_case, mock_monitoring_service):
        """Test execute with minimal required data."""
        # Arrange
        emotion = Emotion.NEUTRAL
        confidence = 0.5
        probabilities = {
            Emotion.ANGRY: 0.1,
            Emotion.DISGUST: 0.1,
            Emotion.FEAR: 0.1,
            Emotion.HAPPY: 0.1,
            Emotion.NEUTRAL: 0.5,
            Emotion.SAD: 0.1,
        }
        features = {}
        audio_bytes = b""
        filename = "minimal.wav"
        model_version = "v1"

        # Act
        prediction_id = use_case.execute(
            emotion=emotion,
            confidence=confidence,
            probabilities=probabilities,
            features=features,
            audio_bytes=audio_bytes,
            filename=filename,
            model_version=model_version,
        )

        # Assert
        assert prediction_id is not None
        assert isinstance(prediction_id, str)
        mock_monitoring_service.log_prediction.assert_called_once()

    def test_execute_converts_emotion_enum_to_string(self, use_case, mock_monitoring_service):
        """Test that Emotion enum is converted to string for monitoring."""
        # Arrange
        emotion = Emotion.SAD
        confidence = 0.85
        probabilities = {
            Emotion.ANGRY: 0.02,
            Emotion.DISGUST: 0.02,
            Emotion.FEAR: 0.03,
            Emotion.HAPPY: 0.02,
            Emotion.NEUTRAL: 0.06,
            Emotion.SAD: 0.85,
        }
        features = {"feature_1": 1.0}
        audio_bytes = b"data"
        filename = "sad.wav"
        model_version = "v5"

        # Act
        use_case.execute(
            emotion=emotion,
            confidence=confidence,
            probabilities=probabilities,
            features=features,
            audio_bytes=audio_bytes,
            filename=filename,
            model_version=model_version,
        )

        # Assert
        call_args = mock_monitoring_service.log_prediction.call_args[0]
        record = call_args[0]
        assert record.predicted_emotion == "sad"  # String, not Emotion enum
        assert isinstance(record.predicted_emotion, str)
