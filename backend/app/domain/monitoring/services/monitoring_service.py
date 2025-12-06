"""Monitoring service interface."""

from abc import ABC, abstractmethod
from typing import Any


class MonitoringService(ABC):
    """Abstract monitoring service for generating reports."""

    @abstractmethod
    def generate_report(self) -> Any:
        """Generate monitoring report.

        Returns:
            Generated report data
        """
        pass
