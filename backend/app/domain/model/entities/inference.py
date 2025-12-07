"""Inference result entity."""

from dataclasses import dataclass
from typing import Any

from app.domain.model.value_objects.confidence import Confidence
from app.domain.model.value_objects.emotion import Emotion
from app.domain.model.value_objects.model_version import ModelVersion


@dataclass
class Inference:
    """Result of emotion inference.

    Represents the complete output of running emotion recognition
    on an audio file. Contains the predicted emotion, confidence score,
    all class probabilities, and metadata about the inference.

    Attributes:
        emotion: Predicted emotion
        confidence: Confidence score for the prediction
        all_probabilities: Probability distribution over all emotions
        model_version: Version of model used for inference
        processing_time_ms: Time taken to process in milliseconds
        audio_features: Optional audio features data (mel spectrogram, chroma, MFCCs, pitch contour)
        prediction_id: Optional unique identifier for monitoring/feedback (UUID string)
    """

    emotion: Emotion
    confidence: Confidence
    all_probabilities: dict[Emotion, float]
    model_version: ModelVersion
    processing_time_ms: float
    audio_features: dict[str, Any] | None = None
    prediction_id: str | None = None

    def __post_init__(self) -> None:
        """Validate inference result."""
        # Validate emotion
        if not isinstance(self.emotion, Emotion):
            raise ValueError(f"emotion must be Emotion instance, got {type(self.emotion)}")

        # Validate confidence
        if not isinstance(self.confidence, Confidence):
            raise ValueError(f"confidence must be Confidence instance, got {type(self.confidence)}")

        # Validate all_probabilities
        if not isinstance(self.all_probabilities, dict):
            raise ValueError(
                f"all_probabilities must be a dict, got {type(self.all_probabilities)}"
            )

        # Check all emotions are present
        all_emotions = set(Emotion.all_emotions())
        provided_emotions = set(self.all_probabilities.keys())
        if provided_emotions != all_emotions:
            missing = all_emotions - provided_emotions
            extra = provided_emotions - all_emotions
            error_parts = []
            if missing:
                error_parts.append(f"missing emotions: {missing}")
            if extra:
                error_parts.append(f"unexpected emotions: {extra}")
            raise ValueError(
                f"all_probabilities must contain all emotions. {', '.join(error_parts)}"
            )

        # Validate probabilities sum to ~1.0 (with small tolerance for float precision)
        prob_sum = sum(self.all_probabilities.values())
        if not 0.99 <= prob_sum <= 1.01:
            raise ValueError(f"all_probabilities must sum to 1.0, got {prob_sum:.6f}")

        # Validate all probabilities are valid
        for emotion, prob in self.all_probabilities.items():
            if not isinstance(prob, (int, float)):
                raise ValueError(f"Probability for {emotion} must be a number, got {type(prob)}")
            if not 0.0 <= prob <= 1.0:
                raise ValueError(
                    f"Probability for {emotion} must be between 0.0 and 1.0, got {prob}"
                )

        # Validate predicted emotion has highest probability
        max_prob_emotion = max(self.all_probabilities.items(), key=lambda x: x[1])[0]
        if max_prob_emotion != self.emotion:
            raise ValueError(
                f"Predicted emotion {self.emotion} does not have highest probability. "
                f"Highest probability is {max_prob_emotion} "
                f"({self.all_probabilities[max_prob_emotion]:.4f})"
            )

        # Validate confidence matches predicted emotion probability
        expected_confidence = self.all_probabilities[self.emotion]
        if abs(self.confidence.value - expected_confidence) > 0.001:
            raise ValueError(
                f"Confidence {self.confidence.value:.4f} does not match "
                f"probability for {self.emotion} ({expected_confidence:.4f})"
            )

        # Validate model_version
        if not isinstance(self.model_version, ModelVersion):
            raise ValueError(
                f"model_version must be ModelVersion instance, got {type(self.model_version)}"
            )

        # Validate processing_time_ms
        if not isinstance(self.processing_time_ms, (int, float)):
            raise ValueError(
                f"processing_time_ms must be a number, got {type(self.processing_time_ms)}"
            )
        if self.processing_time_ms < 0:
            raise ValueError(
                f"processing_time_ms cannot be negative, got {self.processing_time_ms}"
            )

    @classmethod
    def create(
        cls,
        emotion: Emotion,
        all_probabilities: dict[Emotion, float],
        model_version: ModelVersion,
        processing_time_ms: float,
        audio_features: dict[str, Any] | None = None,
        prediction_id: str | None = None,
    ) -> "Inference":
        """Factory method to create Inference.

        Automatically derives confidence from the predicted emotion's probability.

        Args:
            emotion: Predicted emotion
            all_probabilities: Probability distribution over all emotions
            model_version: Version of model used
            processing_time_ms: Processing time in milliseconds
            audio_features: Optional audio features data
            prediction_id: Optional unique identifier for monitoring/feedback

        Returns:
            Inference instance

        Raises:
            ValueError: If any parameter is invalid
        """
        # Get confidence from probability of predicted emotion
        confidence_value = all_probabilities.get(emotion)
        if confidence_value is None:
            raise ValueError(
                f"Probability for predicted emotion {emotion} not found in all_probabilities"
            )

        confidence = Confidence.from_probability(confidence_value)

        return cls(
            emotion=emotion,
            confidence=confidence,
            all_probabilities=all_probabilities,
            model_version=model_version,
            processing_time_ms=processing_time_ms,
            audio_features=audio_features,
            prediction_id=prediction_id,
        )

    def get_top_n_emotions(self, n: int = 3) -> list[tuple[Emotion, float]]:
        """Get top N emotions by probability.

        Args:
            n: Number of top emotions to return (default: 3)

        Returns:
            List of (emotion, probability) tuples, sorted by probability descending
        """
        if n <= 0:
            raise ValueError(f"n must be positive, got {n}")

        sorted_probs = sorted(
            self.all_probabilities.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        return sorted_probs[:n]

    def is_ambiguous(self, threshold: float = 0.2) -> bool:
        """Check if prediction is ambiguous.

        A prediction is considered ambiguous if the difference between
        the top probability and second-highest probability is small.

        Args:
            threshold: Maximum difference for ambiguous classification (default: 0.2)

        Returns:
            True if prediction is ambiguous
        """
        top_2 = self.get_top_n_emotions(n=2)
        if len(top_2) < 2:
            return False

        top_prob = top_2[0][1]
        second_prob = top_2[1][1]
        difference = top_prob - second_prob

        return difference < threshold

    def __str__(self) -> str:
        """String representation."""
        return (
            f"Inference(emotion={self.emotion.value}, "
            f"confidence={self.confidence}, "
            f"model={self.model_version}, "
            f"time={self.processing_time_ms:.2f}ms)"
        )
