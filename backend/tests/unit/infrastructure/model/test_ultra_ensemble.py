"""
Unit tests for UltraEnsembleModel.

Tests the custom ensemble model functionality including:
- Initialization with models dictionary
- Prediction with majority voting
- Probability averaging
- Handling of feature selectors
"""

from unittest.mock import Mock

import numpy as np
import pytest

from app.infrastructure.model.ultra_ensemble import UltraEnsembleModel


class TestUltraEnsembleModelInitialization:
    """Test UltraEnsembleModel initialization."""

    def test_initialization_with_models(self):
        """Test initialization with models dictionary."""
        mock_model1 = Mock()
        mock_model2 = Mock()
        models_dict = {"model1": mock_model1, "model2": mock_model2}

        ensemble = UltraEnsembleModel(models_dict)

        assert ensemble.models == models_dict
        assert ensemble.selector is None

    def test_initialization_with_feature_selector(self):
        """Test initialization with feature selector."""
        mock_model = Mock()
        mock_selector = Mock()
        models_dict = {"model": mock_model}

        ensemble = UltraEnsembleModel(models_dict, feature_selector=mock_selector)

        assert ensemble.models == models_dict
        assert ensemble.selector == mock_selector


class TestUltraEnsembleModelPredictProba:
    """Test predict_proba functionality."""

    def test_predict_proba_single_model(self):
        """Test probability prediction with single model."""
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.1, 0.6, 0.3]])

        ensemble = UltraEnsembleModel({"model": mock_model})
        X = np.array([[1, 2, 3]])

        result = ensemble.predict_proba(X)

        np.testing.assert_array_almost_equal(result, [[0.1, 0.6, 0.3]])
        mock_model.predict_proba.assert_called_once()

    def test_predict_proba_multiple_models(self):
        """Test probability prediction with multiple models."""
        mock_model1 = Mock()
        mock_model1.predict_proba.return_value = np.array([[0.2, 0.6, 0.2]])

        mock_model2 = Mock()
        mock_model2.predict_proba.return_value = np.array([[0.1, 0.8, 0.1]])

        ensemble = UltraEnsembleModel({"model1": mock_model1, "model2": mock_model2})
        X = np.array([[1, 2, 3]])

        result = ensemble.predict_proba(X)

        # Average of [0.2, 0.6, 0.2] and [0.1, 0.8, 0.1] = [0.15, 0.7, 0.15]
        np.testing.assert_array_almost_equal(result, [[0.15, 0.7, 0.15]])

    def test_predict_proba_with_stacking_selected(self):
        """Test probability prediction with stacking_selected model and selector."""
        mock_model1 = Mock()
        mock_model1.predict_proba.return_value = np.array([[0.2, 0.6, 0.2]])

        mock_stacking = Mock()
        mock_stacking.predict_proba.return_value = np.array([[0.3, 0.5, 0.2]])

        mock_selector = Mock()
        mock_selector.transform.return_value = np.array([[1, 2]])  # Reduced features

        ensemble = UltraEnsembleModel(
            {"model1": mock_model1, "stacking_selected": mock_stacking},
            feature_selector=mock_selector,
        )
        X = np.array([[1, 2, 3]])

        result = ensemble.predict_proba(X)

        # Verify selector was called for stacking_selected
        mock_selector.transform.assert_called_once()
        # Stacking model should receive transformed features
        mock_stacking.predict_proba.assert_called_once()

    def test_predict_proba_without_selector_attribute(self):
        """Test predict_proba when selector attribute doesn't exist (backward compatibility)."""
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.3, 0.4, 0.3]])

        ensemble = UltraEnsembleModel({"model": mock_model})
        # Remove selector attribute to simulate old pickle
        del ensemble.selector

        X = np.array([[1, 2, 3]])
        result = ensemble.predict_proba(X)

        np.testing.assert_array_almost_equal(result, [[0.3, 0.4, 0.3]])

    def test_predict_proba_multiple_samples(self):
        """Test probability prediction with multiple samples."""
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([
            [0.1, 0.8, 0.1],
            [0.7, 0.2, 0.1],
            [0.3, 0.3, 0.4],
        ])

        ensemble = UltraEnsembleModel({"model": mock_model})
        X = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])

        result = ensemble.predict_proba(X)

        assert result.shape == (3, 3)


class TestUltraEnsembleModelPredict:
    """Test predict functionality."""

    def test_predict_with_classes_attribute(self):
        """Test prediction with classes_ attribute."""
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.1, 0.6, 0.3]])

        ensemble = UltraEnsembleModel({"model": mock_model})
        ensemble.classes_ = np.array(["angry", "happy", "sad"])

        X = np.array([[1, 2, 3]])
        result = ensemble.predict(X)

        assert result[0] == "happy"  # Index 1 has highest probability

    def test_predict_without_classes_attribute(self):
        """Test prediction without classes_ attribute returns indices."""
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([[0.1, 0.6, 0.3]])

        ensemble = UltraEnsembleModel({"model": mock_model})
        # Don't set classes_ attribute

        X = np.array([[1, 2, 3]])
        result = ensemble.predict(X)

        assert result[0] == 1  # Index of highest probability

    def test_predict_multiple_samples(self):
        """Test prediction with multiple samples."""
        mock_model = Mock()
        mock_model.predict_proba.return_value = np.array([
            [0.1, 0.8, 0.1],  # happy (index 1)
            [0.7, 0.2, 0.1],  # angry (index 0)
            [0.3, 0.3, 0.4],  # sad (index 2)
        ])

        ensemble = UltraEnsembleModel({"model": mock_model})
        ensemble.classes_ = np.array(["angry", "happy", "sad"])

        X = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        result = ensemble.predict(X)

        assert list(result) == ["happy", "angry", "sad"]

    def test_predict_consistent_with_predict_proba(self):
        """Test that predict() is consistent with predict_proba()."""
        mock_model1 = Mock()
        mock_model1.predict_proba.return_value = np.array([[0.3, 0.4, 0.3]])

        mock_model2 = Mock()
        mock_model2.predict_proba.return_value = np.array([[0.2, 0.5, 0.3]])

        ensemble = UltraEnsembleModel({"model1": mock_model1, "model2": mock_model2})
        ensemble.classes_ = np.array(["angry", "happy", "sad"])

        X = np.array([[1, 2, 3]])

        # Get prediction
        prediction = ensemble.predict(X)

        # Get probabilities
        probas = ensemble.predict_proba(X)

        # Verify prediction matches highest probability class
        predicted_class_idx = np.argmax(probas, axis=1)[0]
        assert prediction[0] == ensemble.classes_[predicted_class_idx]
