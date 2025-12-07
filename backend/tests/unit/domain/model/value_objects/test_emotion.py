"""Tests for Emotion value object."""

import pytest

from app.domain.model.value_objects.emotion import Emotion


class TestEmotion:
    """Test cases for Emotion enum."""

    def test_emotion_has_all_six_basic_emotions(self):
        """Test that Emotion enum contains all six basic emotions."""
        # Arrange & Act
        emotions = list(Emotion)

        # Assert
        assert len(emotions) == 6
        assert Emotion.ANGRY in emotions
        assert Emotion.DISGUST in emotions
        assert Emotion.FEAR in emotions
        assert Emotion.HAPPY in emotions
        assert Emotion.NEUTRAL in emotions
        assert Emotion.SAD in emotions

    def test_emotion_from_string_mixed_case(self):
        """Test creating Emotion from mixed case string."""
        # Arrange & Act
        angry = Emotion.from_string("AnGrY")
        happy = Emotion.from_string("HaPpY")

        # Assert
        assert angry == Emotion.ANGRY
        assert happy == Emotion.HAPPY

    def test_emotion_from_string_invalid_raises_value_error(self):
        """Test that invalid emotion string raises ValueError."""
        # Arrange
        invalid_emotions = ["invalid", "excited", "bored", ""]

        # Act & Assert
        for invalid in invalid_emotions:
            with pytest.raises(ValueError) as exc_info:
                Emotion.from_string(invalid)

            assert "Invalid emotion" in str(exc_info.value)
            assert invalid in str(exc_info.value)

    def test_emotion_from_string_error_message_shows_valid_emotions(self):
        """Test that error message lists all valid emotions."""
        # Arrange
        invalid = "excited"

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            Emotion.from_string(invalid)

        error_message = str(exc_info.value)
        assert "angry" in error_message
        assert "disgust" in error_message
        assert "fear" in error_message
        assert "happy" in error_message
        assert "neutral" in error_message
        assert "sad" in error_message

    def test_emotion_all_emotions_contains_all_values(self):
        """Test that all_emotions contains all emotion values."""
        # Act
        emotions = Emotion.all_emotions()

        # Assert
        assert Emotion.ANGRY in emotions
        assert Emotion.DISGUST in emotions
        assert Emotion.FEAR in emotions
        assert Emotion.HAPPY in emotions
        assert Emotion.NEUTRAL in emotions
        assert Emotion.SAD in emotions
