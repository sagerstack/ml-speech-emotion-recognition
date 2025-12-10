"""
Unit tests for SetActualEmotionUseCase.
"""

from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.use_cases.monitoring.set_actual_emotion import SetActualEmotionUseCase


class TestSetActualEmotionUseCase:
    """Test SetActualEmotionUseCase."""

    def test_execute_success(self):
        """Test successful emotion update."""
        mock_repository = Mock()
        mock_prediction = Mock()
        mock_repository.update_actual_emotion.return_value = mock_prediction

        use_case = SetActualEmotionUseCase(prediction_repository=mock_repository)
        prediction_id = uuid4()
        result = use_case.execute(prediction_id, "happy")

        assert result == mock_prediction
        mock_repository.update_actual_emotion.assert_called_once_with(prediction_id, "happy")

    def test_execute_not_found(self):
        """Test when prediction is not found."""
        mock_repository = Mock()
        mock_repository.update_actual_emotion.return_value = None

        use_case = SetActualEmotionUseCase(prediction_repository=mock_repository)
        prediction_id = uuid4()
        result = use_case.execute(prediction_id, "sad")

        assert result is None
        mock_repository.update_actual_emotion.assert_called_once()

    def test_init(self):
        """Test initialization."""
        mock_repository = Mock()

        use_case = SetActualEmotionUseCase(prediction_repository=mock_repository)

        assert use_case._repository == mock_repository
