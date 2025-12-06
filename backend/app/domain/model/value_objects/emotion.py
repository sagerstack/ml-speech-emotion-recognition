"""Emotion value object."""

from enum import Enum


class Emotion(str, Enum):
    """Emotion categories for speech emotion recognition.

    This enum represents the six basic emotions that the model
    can recognize from speech audio. Each emotion corresponds to
    a specific label in the CREMA-D dataset.

    Attributes:
        ANGRY: Anger emotion
        DISGUST: Disgust emotion
        FEAR: Fear emotion
        HAPPY: Happy emotion
        NEUTRAL: Neutral (no strong emotion)
        SAD: Sadness emotion
    """

    ANGRY = "angry"
    DISGUST = "disgust"
    FEAR = "fear"
    HAPPY = "happy"
    NEUTRAL = "neutral"
    SAD = "sad"

    @classmethod
    def from_string(cls, value: str) -> "Emotion":
        """Create Emotion from string value.

        Args:
            value: String representation of emotion (case-insensitive)

        Returns:
            Emotion enum value

        Raises:
            ValueError: If value doesn't match any emotion
        """
        try:
            return cls(value.lower())
        except ValueError:
            valid_emotions = [e.value for e in cls]
            raise ValueError(f"Invalid emotion '{value}'. Must be one of: {valid_emotions}")

    @classmethod
    def all_emotions(cls) -> list["Emotion"]:
        """Get list of all emotion values.

        Returns:
            List of all Emotion enum values
        """
        return list(cls)

    def __str__(self) -> str:
        """Return the emotion value as string.

        Returns:
            The string value of the emotion
        """
        return self.value
