"""
Unit tests for SavePredictionUseCase.
"""

from unittest.mock import Mock

import pytest

from app.use_cases.monitoring.save_prediction import SavePredictionUseCase


class TestSavePredictionUseCase:
    """Test SavePredictionUseCase."""

    def test_execute_success(self):
        """Test successful prediction saving."""
        mock_repository = Mock()
        mock_prediction = Mock()
        mock_repository.save.return_value = mock_prediction

        use_case = SavePredictionUseCase(prediction_repository=mock_repository)
        result = use_case.execute(mock_prediction)

        assert result == mock_prediction
        mock_repository.save.assert_called_once_with(mock_prediction)

    def test_init(self):
        """Test initialization."""
        mock_repository = Mock()

        use_case = SavePredictionUseCase(prediction_repository=mock_repository)

        assert use_case._repository == mock_repository
