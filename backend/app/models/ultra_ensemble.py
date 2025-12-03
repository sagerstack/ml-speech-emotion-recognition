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
        Predict emotion classes using majority voting across all models.

        Args:
            X: Feature array of shape (n_samples, n_features)

        Returns:
            np.ndarray: Predicted class labels for each sample
        """
        all_preds = {}

        for name, model in self.models.items():
            if name == 'stacking_selected' and self.selector is not None:
                X_sel = self.selector.transform(X)
                all_preds[name] = model.predict(X_sel)
            else:
                all_preds[name] = model.predict(X)

        # Majority voting
        n_samples = len(X)
        final_preds = []
        for i in range(n_samples):
            votes = [pred[i] for pred in all_preds.values()]
            final_preds.append(max(set(votes), key=votes.count))

        return np.array(final_preds)

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
            if name == 'stacking_selected' and self.selector is not None:
                X_sel = self.selector.transform(X)
                all_probas[name] = model.predict_proba(X_sel)
            else:
                all_probas[name] = model.predict_proba(X)

        # Average probabilities across all models
        averaged_probabilities = np.mean(list(all_probas.values()), axis=0)

        return averaged_probabilities
