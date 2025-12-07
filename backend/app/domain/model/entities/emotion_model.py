"""Domain model interface for emotion prediction models.

This module defines the abstract interface that all emotion prediction models
must implement. This follows the Dependency Inversion Principle - the domain
layer defines what it needs, and the infrastructure layer provides the implementation.
"""

from abc import ABC, abstractmethod

import numpy as np

from app.domain.model.value_objects.emotion import Emotion


class EmotionModel(ABC):
    """Abstract interface for emotion prediction models.

    This interface defines the contract that all emotion prediction models
    must implement. The domain layer (use cases) depends on this abstraction,
    not on concrete implementations like UltraEnsembleModel or pickle files.

    This follows the Dependency Inversion Principle:
    - High-level modules (use cases) depend on abstractions (this interface)
    - Low-level modules (infrastructure) implement the abstraction
    - Both depend on the abstraction, not on each other

    Example implementations:
    - SklearnEmotionModel (wraps pickled sklearn/ensemble models)
    - TensorFlowEmotionModel (wraps Keras models)
    - PyTorchEmotionModel (wraps PyTorch models)
    - SageMakerEmotionModel (calls AWS SageMaker endpoint)
    """

    @abstractmethod
    def predict_emotion_probabilities(self, features: np.ndarray) -> dict[Emotion, float]:
        """Predict emotion probabilities from audio features.

        This method takes audio features and returns the probability distribution
        over all emotions. The domain layer uses these probabilities to determine
        the predicted emotion and create an Inference entity.

        Args:
            features: Audio feature array of shape (n_features,) or (1, n_features).
                     Expected to be a 1D or 2D numpy array of float values.
                     For v3/v4 models, this should be 210 features.

        Returns:
            Dictionary mapping each Emotion enum to its probability (0.0-1.0).
            Probabilities must sum to 1.0 (or very close due to floating point).
            All six emotions must be present: ANGRY, DISGUST, FEAR, HAPPY, NEUTRAL, SAD.

            Example:
                {
                    Emotion.ANGRY: 0.05,
                    Emotion.DISGUST: 0.02,
                    Emotion.FEAR: 0.08,
                    Emotion.HAPPY: 0.75,  # Predicted emotion (highest)
                    Emotion.NEUTRAL: 0.05,
                    Emotion.SAD: 0.05
                }

        Raises:
            PredictionFailedError: If prediction fails for any reason:
                - Invalid features shape
                - Model execution error
                - Invalid output format
                - Missing emotion in output
        """
        pass
