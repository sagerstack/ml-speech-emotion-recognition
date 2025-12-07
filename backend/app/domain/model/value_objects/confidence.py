"""Confidence value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Confidence:
    """Confidence score for predictions.

    Represents a probability value between 0.0 and 1.0.
    This is an immutable value object that ensures confidence
    scores are always within valid range.

    Attributes:
        value: Confidence score between 0.0 (no confidence) and 1.0 (full confidence)
    """

    value: float

    def __post_init__(self) -> None:
        """Validate confidence value is in valid range."""
        if not isinstance(self.value, (int, float)):
            raise ValueError(f"Confidence must be a number, got {type(self.value)}")

        if not 0.0 <= self.value <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.value}")

    @classmethod
    def from_probability(cls, probability: float) -> "Confidence":
        """Create Confidence from probability value.

        Args:
            probability: Probability value between 0.0 and 1.0

        Returns:
            Confidence instance

        Raises:
            ValueError: If probability is not in valid range
        """
        return cls(value=probability)

    def as_percentage(self) -> float:
        """Get confidence as percentage (0-100).

        Returns:
            Confidence value as percentage
        """
        return self.value * 100

    def is_high_confidence(self, threshold: float = 0.7) -> bool:
        """Check if confidence is above threshold.

        Args:
            threshold: Minimum confidence threshold (default: 0.7)

        Returns:
            True if confidence is above threshold
        """
        return self.value >= threshold

    def __float__(self) -> float:
        """Convert to float."""
        return float(self.value)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.as_percentage():.2f}%"
