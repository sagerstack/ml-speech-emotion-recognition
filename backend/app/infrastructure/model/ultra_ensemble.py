"""
Ultra Ensemble Model Class

This module defines the UltraEnsembleModel class which is required to unpickle
the v3 model. The v3 model was trained using this custom ensemble class that
combines multiple models via majority voting.
"""

import numpy as np


class UltraEnsembleModel:
    """Combines multiple models via majority voting"""

    def __init__(self, models_dict, feature_selector=None):
        """
        Initialize the Ultra Ensemble Model.

        Args:
            models_dict: Dictionary of model names to model instances
            feature_selector: Optional feature selector for specific models
        """
        self.models = models_dict
        self.selector = feature_selector

    def predict(self, X):
        """
        Predict emotion classes using the class with highest averaged probability.

        This ensures consistency between predict() and predict_proba() methods.
        The predicted class will always be the one with the maximum averaged probability.

        Args:
            X: Feature array of shape (n_samples, n_features)

        Returns:
            np.ndarray: Predicted class labels for each sample
        """
        # Get averaged probabilities
        probabilities = self.predict_proba(X)

        # Return class with highest probability for each sample
        # This ensures predict() is consistent with predict_proba()
        if not hasattr(self, "classes_"):
            # Fallback: if classes_ not set, use indices
            return np.argmax(probabilities, axis=1)

        # Return actual class labels
        return self.classes_[np.argmax(probabilities, axis=1)]

    def predict_proba(self, X):
        """
        Predict class probabilities by averaging probabilities from all models.

        This method follows the standard scikit-learn API and returns only
        the averaged probabilities array.

        Args:
            X: Feature array of shape (n_samples, n_features)

        Returns:
            np.ndarray: Averaged probability array of shape (n_samples, n_classes)
        """
        all_probas = dict()

        for name, model in self.models.items():
            if name == "stacking_selected" and self.selector is not None:
                X_sel = self.selector.transform(X)
                all_probas[name] = model.predict_proba(X_sel)
            else:
                all_probas[name] = model.predict_proba(X)

        # Average probabilities across all models
        averaged_probabilities = np.mean(list(all_probas.values()), axis=0)

        return averaged_probabilities
