"""
Unit tests for GenerateReportUseCase.
"""

from unittest.mock import Mock

import pytest

from app.use_cases.monitoring.generate_report import GenerateReportUseCase


class TestGenerateReportUseCase:
    """Test GenerateReportUseCase."""

    def test_execute_success(self):
        """Test successful report generation."""
        mock_service = Mock()
        mock_report = {"name": "test_report", "path": "/tmp/report.html"}
        mock_service.generate_report.return_value = mock_report

        use_case = GenerateReportUseCase(monitoring_service=mock_service)
        result = use_case.execute()

        assert result == mock_report
        mock_service.generate_report.assert_called_once()

    def test_init(self):
        """Test initialization."""
        mock_service = Mock()

        use_case = GenerateReportUseCase(monitoring_service=mock_service)

        assert use_case._service == mock_service
