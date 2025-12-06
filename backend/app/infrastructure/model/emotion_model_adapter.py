"""Adapter that wraps pickle models to implement domain EmotionModel interface.

This module implements the Adapter Pattern to convert pickled sklearn/ensemble models
(like UltraEnsembleModel) into the domain's EmotionModel interface. This isolates
the domain layer from infrastructure concerns like pickle serialization.
"""

from typing import Any

import numpy as np

from app.domain.model.entities.emotion_model import EmotionModel
from app.domain.model.exceptions.prediction_failed_error import PredictionFailedError
from app.domain.model.value_objects.emotion import Emotion
from app.infrastructure.observability.logging import get_logger


class SklearnEmotionModelAdapter(EmotionModel):
    """Adapts pickled sklearn/ensemble models to domain EmotionModel interface.

    This adapter wraps models loaded from pickle files (like UltraEnsembleModel,
    sklearn classifiers) and exposes them through the domain's EmotionModel interface.
    This isolates the domain from pickle-specific details and sklearn API.

    Adapter Pattern:
    - Target: EmotionModel (domain interface)
    - Adaptee: Pickled model with predict_proba() method
    - Adapter: SklearnEmotionModelAdapter (this class)

    The adapter handles:
    - Calling the underlying model's predict_proba() method
    - Reshaping features if needed (1D -> 2D)
    - Extracting single sample probabilities (2D -> 1D)
    - Converting numpy arrays to domain Emotion dictionary
    - Validating outputs
    - Converting errors to domain exceptions
    """

    # Emotion order expected by v3/v4 models
    # This matches the class order used during model training
    _EMOTION_MAPPING = [
        Emotion.ANGRY,
        Emotion.DISGUST,
        Emotion.FEAR,
        Emotion.HAPPY,
        Emotion.NEUTRAL,
        Emotion.SAD,
    ]

    def __init__(self, pickled_model: Any):
        """Initialize adapter with a pickled model.

        Args:
            pickled_model: Any model with predict_proba() method.
                          Examples: UltraEnsembleModel, sklearn.ensemble.RandomForestClassifier

        Raises:
            ValueError: If model doesn't have predict_proba() method
        """
        if not hasattr(pickled_model, "predict_proba"):
            raise ValueError(
                f"Model {type(pickled_model).__name__} doesn't have predict_proba() method. "
                f"Only sklearn-compatible models are supported."
            )

        self._model = pickled_model
        self.logger = get_logger(__name__)

    def predict_emotion_probabilities(self, features: np.ndarray) -> dict[Emotion, float]:
        """Predict emotion probabilities using wrapped model.

        Implementation strategy:
        1. Validate and reshape features if needed
        2. Call underlying model's predict_proba()
        3. Extract probabilities for single sample
        4. Validate output shape
        5. Convert to domain types (dict[Emotion, float])

        Args:
            features: Audio feature array of shape (n_features,) or (1, n_features)

        Returns:
            Dictionary mapping each Emotion to its probability (0.0-1.0)

        Raises:
            PredictionFailedError: If prediction fails for any reason
        """
        self.logger.debug(
            "Running emotion prediction",
            input_shape=features.shape
        )

        try:
            # Step 1: Reshape features if needed
            # sklearn models expect (n_samples, n_features)
            if len(features.shape) == 1:
                features = features.reshape(1, -1)
            elif len(features.shape) != 2:
                raise PredictionFailedError(
                    f"Invalid features shape: {features.shape}. "
                    f"Expected 1D (n_features,) or 2D (1, n_features)"
                )

            # Step 2: Call underlying model
            probabilities = self._model.predict_proba(features)

            # Step 3: Extract single sample probabilities
            # Model returns (n_samples, n_classes), we need (n_classes,)
            if len(probabilities.shape) == 2:
                if probabilities.shape[0] != 1:
                    raise PredictionFailedError(
                        f"Expected single sample, got {probabilities.shape[0]} samples"
                    )
                probabilities = probabilities[0]

            # Step 4: Validate output shape
            if len(probabilities) != len(self._EMOTION_MAPPING):
                raise PredictionFailedError(
                    f"Model returned {len(probabilities)} probabilities, "
                    f"expected {len(self._EMOTION_MAPPING)} (one per emotion). "
                    f"Model may not be compatible with v3/v4 emotion set."
                )

            # Step 5: Convert to domain types
            emotion_probabilities: dict[Emotion, float] = {
                emotion: float(prob) for emotion, prob in zip(self._EMOTION_MAPPING, probabilities)
            }

            # Step 6: Validate probabilities sum to ~1.0
            total_prob = sum(emotion_probabilities.values())
            if not (0.99 <= total_prob <= 1.01):
                raise PredictionFailedError(
                    f"Probabilities sum to {total_prob:.4f}, expected ~1.0. "
                    f"Model output may be invalid."
                )

            # Find predicted emotion
            predicted_emotion = max(emotion_probabilities.items(), key=lambda x: x[1])

            self.logger.debug(
                "Prediction completed",
                predicted_emotion=str(predicted_emotion[0]),
                confidence=round(predicted_emotion[1], 4)
            )

            return emotion_probabilities

        except PredictionFailedError:
            # Re-raise domain exceptions as-is
            raise

        except Exception as e:
            # Convert any other exception to domain exception
            self.logger.error(
                "Prediction failed unexpectedly",
                error=str(e),
                input_shape=features.shape
            )
            raise PredictionFailedError(
                f"Model prediction failed: {type(e).__name__}: {str(e)}"
            ) from e
