"""
Unit tests for LogPredictionForMonitoringUseCase.

Tests the monitoring logging use case including:
- Successful prediction logging
- Handling when monitoring is disabled
- Error handling
- Auto-report triggering
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.domain.model.value_objects.emotion import Emotion
from app.use_cases.monitoring.log_prediction_for_monitoring import LogPredictionForMonitoringUseCase


class TestLogPredictionForMonitoringUseCaseExecute:
    """Test execute method."""

    def test_execute_success(self):
        """Test successful prediction logging."""
        mock_monitoring_service = Mock()
        mock_monitoring_service.log_prediction.return_value = 5
        mock_logger = Mock()

        use_case = LogPredictionForMonitoringUseCase(
            monitoring_service=mock_monitoring_service,
            logger=mock_logger,
        )

        prediction_id = use_case.execute(
            emotion=Emotion.HAPPY,
            confidence=0.9,
            probabilities={Emotion.HAPPY: 0.9, Emotion.SAD: 0.1},
            features={"feature_a": 0.5},
            audio_bytes=b"fake audio",
            filename="test.wav",
            model_version="1",
            api_version="v2",
        )

        # Should return a valid UUID
        assert len(prediction_id) == 36
        assert "-" in prediction_id

        # Should log prediction
        mock_monitoring_service.log_prediction.assert_called_once()
        mock_logger.info.assert_called_once()

    def test_execute_monitoring_disabled(self):
        """Test execute when monitoring is disabled (service is None)."""
        mock_logger = Mock()

        use_case = LogPredictionForMonitoringUseCase(
            monitoring_service=None,
            logger=mock_logger,
        )

        prediction_id = use_case.execute(
            emotion=Emotion.HAPPY,
            confidence=0.9,
            probabilities={Emotion.HAPPY: 0.9},
            features={"feature_a": 0.5},
            audio_bytes=b"fake audio",
            filename="test.wav",
            model_version="1",
        )

        # Should return empty string
        assert prediction_id == ""
        mock_logger.info.assert_not_called()

    def test_execute_with_exception(self):
        """Test execute when monitoring service raises exception."""
        mock_monitoring_service = Mock()
        mock_monitoring_service.log_prediction.side_effect = Exception("Buffer full")
        mock_logger = Mock()

        use_case = LogPredictionForMonitoringUseCase(
            monitoring_service=mock_monitoring_service,
            logger=mock_logger,
        )

        prediction_id = use_case.execute(
            emotion=Emotion.HAPPY,
            confidence=0.9,
            probabilities={Emotion.HAPPY: 0.9},
            features={"feature_a": 0.5},
            audio_bytes=b"fake audio",
            filename="test.wav",
            model_version="1",
        )

        # Should return empty string on error
        assert prediction_id == ""

        # Should log warning
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "Monitoring logging failed" in str(call_args)


class TestLogPredictionForMonitoringUseCaseTriggerAutoReport:
    """Test _trigger_auto_report method."""

    def test_trigger_auto_report_success(self):
        """Test successful auto-report generation."""
        mock_monitoring_service = Mock()
        mock_report_info = Mock()
        mock_report_info.name = "test_report"
        mock_report_info.html_path = "/tmp/test_report.html"
        mock_monitoring_service.generate_report.return_value = mock_report_info
        mock_logger = Mock()

        use_case = LogPredictionForMonitoringUseCase(
            monitoring_service=mock_monitoring_service,
            logger=mock_logger,
        )

        use_case._trigger_auto_report(buffer_length=100)

        # Should call generate_report
        mock_monitoring_service.generate_report.assert_called_once()

        # Should log info twice (starting and success)
        assert mock_logger.info.call_count == 2

    def test_trigger_auto_report_failure(self):
        """Test auto-report generation when it fails."""
        mock_monitoring_service = Mock()
        mock_monitoring_service.generate_report.side_effect = Exception("Report generation failed")
        mock_logger = Mock()

        use_case = LogPredictionForMonitoringUseCase(
            monitoring_service=mock_monitoring_service,
            logger=mock_logger,
        )

        # Should not raise exception
        use_case._trigger_auto_report(buffer_length=100)

        # Should log warning
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "Auto-report generation failed" in str(call_args)


class TestLogPredictionForMonitoringUseCaseInit:
    """Test initialization."""

    def test_init_with_service(self):
        """Test initialization with monitoring service."""
        mock_service = Mock()
        mock_logger = Mock()

        use_case = LogPredictionForMonitoringUseCase(
            monitoring_service=mock_service,
            logger=mock_logger,
        )

        assert use_case.monitoring_service == mock_service
        assert use_case.logger == mock_logger

    def test_init_without_service(self):
        """Test initialization without monitoring service."""
        mock_logger = Mock()

        use_case = LogPredictionForMonitoringUseCase(
            monitoring_service=None,
            logger=mock_logger,
        )

        assert use_case.monitoring_service is None
        assert use_case.logger == mock_logger
