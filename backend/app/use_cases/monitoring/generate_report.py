"""Use case for generating monitoring reports."""

from typing import Any

from app.domain.monitoring.services.monitoring_service import MonitoringService


class GenerateReportUseCase:
    """Generate Evidently AI report."""

    def __init__(self, monitoring_service: MonitoringService):
        """Initialize use case.

        Args:
            monitoring_service: Service for generating reports
        """
        self._service = monitoring_service

    def execute(self) -> Any:
        """Execute use case to generate report.

        Returns:
            Generated report data
        """
        return self._service.generate_report()
