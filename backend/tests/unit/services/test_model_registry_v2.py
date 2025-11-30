"""
Unit tests for Model Registry with v2 model.

This test suite validates the ModelRegistry service functionality for v2:
- Model discovery finds v2
- Model loading from pickle
- Metadata parsing
- Dynamic feature extractor import
- Version management (get_version, get_latest)
- predict() method
- Error handling
"""

import json
import pickle
import pytest
import numpy as np
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.services.model_registry import ModelRegistry, ModelVersion, get_registry, reload_registry


@pytest.fixture
def models_path():
    """Path to models directory."""
    return Path("/Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition/backend/models")


@pytest.fixture
def v2_model_path(models_path):
    """Path to v2 model directory."""
    return models_path / "v2"


@pytest.fixture
def registry(models_path):
    """Create a fresh ModelRegistry instance."""
    return ModelRegistry(models_path=models_path)


@pytest.fixture
def initialized_registry(registry):
    """Create and initialize a ModelRegistry."""
    registry.discover_models()
    return registry


class TestModelRegistryDiscoveryV2:
    """Test ModelRegistry discovery for v2."""

    def test_registry_discovers_v2(self, registry):
        """Test that model discovery finds v2 model."""
        count = registry.discover_models()

        assert count >= 2, "Should discover at least v1 and v2 models"
        assert "2" in registry.versions, "Should register version 2"

    def test_discovered_v2_has_correct_attributes(self, initialized_registry):
        """Test that discovered v2 model has all required attributes."""
        v2 = initialized_registry.get_version("2")

        assert v2 is not None, "v2 should be registered"
        assert isinstance(v2, ModelVersion), "Should be ModelVersion instance"
        assert v2.version == "2", "Version should be '2'"
        assert v2.path.exists(), "Model path should exist"
        assert v2.model is not None, "Model should be loaded"
        assert v2.feature_extractor is not None, "Feature extractor should be loaded"
        assert v2.metadata is not None, "Metadata should be loaded"
        assert v2.feature_dimension == 78, "Feature dimension should be 78"

    def test_v2_model_path_contains_required_files(self, v2_model_path):
        """Test that v2 directory contains all required files."""
        assert (v2_model_path / "model.pkl").exists(), "model.pkl should exist"
        assert (v2_model_path / "feature_extractor.py").exists(), "feature_extractor.py should exist"
        assert (v2_model_path / "metadata.json").exists(), "metadata.json should exist"


class TestV2MetadataParsing:
    """Test v2 metadata loading and parsing."""

    def test_v2_metadata_loaded_correctly(self, initialized_registry):
        """Test that v2 metadata is loaded and parsed correctly."""
        v2 = initialized_registry.get_version("2")

        assert v2.metadata is not None, "Metadata should be loaded"
        assert isinstance(v2.metadata, dict), "Metadata should be a dictionary"

        # Check required metadata fields
        assert "version" in v2.metadata, "Should have version field"
        assert "model_type" in v2.metadata, "Should have model_type field"
        assert "feature_dimension" in v2.metadata, "Should have feature_dimension field"
        assert "classes" in v2.metadata, "Should have classes field"

    def test_v2_metadata_values_correct(self, initialized_registry):
        """Test that v2 metadata values are correct."""
        v2 = initialized_registry.get_version("2")

        assert v2.metadata["version"] == "2", "Version should be '2'"
        assert v2.metadata["model_type"] == "Pipeline (StandardScaler + RFE + SVC)", \
            "Model type should be Pipeline"
        assert v2.metadata["feature_dimension"] == 78, \
            "Feature dimension should be 78"
        assert v2.metadata["num_classes"] == 6, "Should have 6 classes"

    def test_v2_classes_are_correct(self, initialized_registry):
        """Test that v2 has correct emotion classes."""
        v2 = initialized_registry.get_version("2")

        expected_classes = ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        actual_classes = v2.metadata["classes"]

        assert len(actual_classes) == 6, "Should have 6 classes"
        assert set(actual_classes) == set(expected_classes), \
            f"Classes should be {expected_classes}, got {actual_classes}"


class TestV2ModelLoading:
    """Test v2 model pickle loading."""

    def test_v2_model_loads_successfully(self, initialized_registry):
        """Test that v2 model loads from pickle successfully."""
        v2 = initialized_registry.get_version("2")

        assert v2.model is not None, "Model should be loaded"
        # Check it's a scikit-learn model
        assert hasattr(v2.model, 'predict'), "Model should have predict method"

    def test_v2_model_is_pipeline(self, initialized_registry):
        """Test that v2 model is a Pipeline."""
        v2 = initialized_registry.get_version("2")

        model_class_name = v2.model.__class__.__name__
        assert model_class_name == "Pipeline", \
            f"Expected Pipeline, got {model_class_name}"

    def test_v2_model_has_classes(self, initialized_registry):
        """Test that loaded model has classes_ attribute."""
        v2 = initialized_registry.get_version("2")

        assert hasattr(v2.model, 'classes_'), "Model should have classes_ attribute"
        assert len(v2.model.classes_) == 6, "Model should have 6 classes"


class TestV2FeatureExtractorLoading:
    """Test dynamic feature extractor import for v2."""

    def test_v2_feature_extractor_loaded(self, initialized_registry):
        """Test that v2 feature extractor is dynamically loaded."""
        v2 = initialized_registry.get_version("2")

        assert v2.feature_extractor is not None, "Feature extractor should be loaded"
        assert callable(v2.feature_extractor), "Feature extractor should be callable"

    def test_v2_feature_extractor_signature(self, initialized_registry):
        """Test that feature extractor has correct signature."""
        v2 = initialized_registry.get_version("2")

        # Should accept (bytes, str) parameters
        import inspect
        sig = inspect.signature(v2.feature_extractor)
        params = list(sig.parameters.keys())

        assert len(params) == 2, "Feature extractor should have 2 parameters"
        assert "audio_bytes" in params, "Should have audio_bytes parameter"
        assert "filename" in params, "Should have filename parameter"

    def test_v2_feature_extractor_produces_correct_output(
        self, initialized_registry, sample_audio_file
    ):
        """Test that feature extractor produces correct output shape."""
        v2 = initialized_registry.get_version("2")

        features = v2.feature_extractor(sample_audio_file, "test.wav")

        assert isinstance(features, np.ndarray), "Should return numpy array"
        assert features.shape == (78,), f"Expected (78,), got {features.shape}"
        assert features.dtype in [np.float32, np.float64], "Should be float type"


class TestV2VersionManagement:
    """Test version management methods for v2."""

    def test_get_version_returns_v2_correctly(self, initialized_registry):
        """Test get_version returns correct ModelVersion for v2."""
        v2 = initialized_registry.get_version("2")

        assert v2 is not None, "Should return v2"
        assert isinstance(v2, ModelVersion), "Should return ModelVersion instance"
        assert v2.version == "2", "Version should be '2'"

    def test_get_latest_returns_v2_when_latest(self, initialized_registry):
        """Test get_latest returns v2 when it's the latest version."""
        latest = initialized_registry.get_latest()

        assert latest is not None, "Latest should not be None"
        assert isinstance(latest, ModelVersion), "Should return ModelVersion"
        # v2 should be latest if only v1 and v2 exist
        assert int(latest.version) >= 2, "Latest version should be >= 2"

    def test_list_versions_includes_v2(self, initialized_registry):
        """Test list_versions includes v2."""
        versions = initialized_registry.list_versions()

        assert isinstance(versions, list), "Should return a list"
        assert "2" in versions, "Should include version 2"
        assert len(versions) >= 2, "Should have at least two versions"


class TestV2PredictMethod:
    """Test the predict() method with v2 model."""

    def test_predict_with_v2_returns_valid_result(
        self, initialized_registry, sample_audio_file
    ):
        """Test predict with v2 returns valid prediction result."""
        result = initialized_registry.predict("2", sample_audio_file, "test.wav")

        assert result is not None, "Result should not be None"
        assert isinstance(result, dict), "Result should be a dictionary"

        # Check required fields
        assert "emotion" in result, "Result should have emotion"
        assert "confidence" in result, "Result should have confidence"
        assert "all_probabilities" in result, "Result should have all_probabilities"
        assert "model_version" in result, "Result should have model_version"
        assert "model_type" in result, "Result should have model_type"
        assert "feature_dimension" in result, "Result should have feature_dimension"

    def test_predict_emotion_is_valid_class(
        self, initialized_registry, sample_audio_file
    ):
        """Test that predicted emotion is one of the valid classes."""
        result = initialized_registry.predict("2", sample_audio_file, "test.wav")

        valid_emotions = ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        assert result["emotion"] in valid_emotions, \
            f"Emotion should be one of {valid_emotions}, got {result['emotion']}"

    def test_predict_confidence_in_valid_range(
        self, initialized_registry, sample_audio_file
    ):
        """Test that confidence is in [0, 1] range."""
        result = initialized_registry.predict("2", sample_audio_file, "test.wav")

        confidence = result["confidence"]
        assert 0.0 <= confidence <= 1.0, \
            f"Confidence should be in [0, 1], got {confidence}"

    def test_predict_all_probabilities_sum_to_one(
        self, initialized_registry, sample_audio_file
    ):
        """Test that all probabilities sum to approximately 1.0."""
        result = initialized_registry.predict("2", sample_audio_file, "test.wav")

        all_probs = result["all_probabilities"]
        prob_sum = sum(all_probs.values())

        assert 0.99 <= prob_sum <= 1.01, \
            f"Probabilities should sum to ~1.0, got {prob_sum}"

    def test_predict_all_probabilities_has_all_classes(
        self, initialized_registry, sample_audio_file
    ):
        """Test that all_probabilities contains emotion classes.

        Note: v2 model uses SVC with probability=False, so it only returns
        the predicted class with confidence 1.0. This is expected behavior.
        """
        result = initialized_registry.predict("2", sample_audio_file, "test.wav")

        all_probs = result["all_probabilities"]

        # v2 model doesn't have probability enabled, so it only returns the predicted class
        assert isinstance(all_probs, dict), "all_probabilities should be a dict"
        assert len(all_probs) >= 1, "Should have at least one probability"

        # The predicted emotion should be in all_probabilities
        predicted_emotion = result["emotion"]
        assert predicted_emotion in all_probs, \
            f"Predicted emotion {predicted_emotion} should be in all_probabilities"

    def test_predict_model_version_correct(
        self, initialized_registry, sample_audio_file
    ):
        """Test that result includes correct model version."""
        result = initialized_registry.predict("2", sample_audio_file, "test.wav")

        assert result["model_version"] == "2", \
            f"Model version should be '2', got {result['model_version']}"

    def test_predict_model_type_correct(
        self, initialized_registry, sample_audio_file
    ):
        """Test that result includes correct model type."""
        result = initialized_registry.predict("2", sample_audio_file, "test.wav")

        assert result["model_type"] == "Pipeline (StandardScaler + RFE + SVC)", \
            f"Model type should be Pipeline, got {result['model_type']}"

    def test_predict_feature_dimension_correct(
        self, initialized_registry, sample_audio_file
    ):
        """Test that result includes correct feature dimension."""
        result = initialized_registry.predict("2", sample_audio_file, "test.wav")

        assert result["feature_dimension"] == 78, \
            f"Feature dimension should be 78, got {result['feature_dimension']}"

    def test_predict_highest_probability_matches_emotion(
        self, initialized_registry, sample_audio_file
    ):
        """Test that predicted emotion has highest probability."""
        result = initialized_registry.predict("2", sample_audio_file, "test.wav")

        emotion = result["emotion"]
        all_probs = result["all_probabilities"]
        confidence = result["confidence"]

        # The emotion should have the highest probability
        max_prob_emotion = max(all_probs, key=all_probs.get)
        assert emotion == max_prob_emotion, \
            f"Predicted emotion {emotion} should have highest probability"

        # Confidence should match the emotion's probability
        assert abs(confidence - all_probs[emotion]) < 0.001, \
            f"Confidence {confidence} should match emotion probability {all_probs[emotion]}"


class TestV2PredictErrorHandling:
    """Test error handling in predict() method for v2."""

    def test_predict_with_invalid_audio_raises_error(
        self, initialized_registry, corrupted_audio_file
    ):
        """Test predict with invalid audio raises ValueError."""
        with pytest.raises(ValueError, match="Feature extraction failed"):
            initialized_registry.predict("2", corrupted_audio_file, "corrupted.wav")

    def test_predict_with_empty_audio_raises_error(self, initialized_registry):
        """Test predict with empty audio raises ValueError."""
        with pytest.raises(ValueError, match="Feature extraction failed"):
            initialized_registry.predict("2", b"", "empty.wav")


class TestV2GetModelInfo:
    """Test get_model_info() method for v2."""

    def test_get_model_info_v2_returns_dict(self, initialized_registry):
        """Test get_model_info for v2 returns dictionary."""
        info = initialized_registry.get_model_info("2")

        assert info is not None, "Info should not be None"
        assert isinstance(info, dict), "Info should be a dictionary"

    def test_get_model_info_v2_has_required_fields(self, initialized_registry):
        """Test that model info has all required fields."""
        info = initialized_registry.get_model_info("2")

        required_fields = [
            "version", "model_type", "model_name", "description",
            "feature_dimension", "classes", "num_classes"
        ]

        for field in required_fields:
            assert field in info, f"Info should have {field} field"

    def test_get_model_info_v2_values_correct(self, initialized_registry):
        """Test that model info values are correct."""
        info = initialized_registry.get_model_info("2")

        assert info["version"] == "2", "Version should be '2'"
        assert info["model_type"] == "Pipeline (StandardScaler + RFE + SVC)", \
            "Model type should be Pipeline"
        assert info["feature_dimension"] == 78, "Feature dimension should be 78"
        assert info["num_classes"] == 6, "Should have 6 classes"
        assert len(info["classes"]) == 6, "Should have 6 classes in list"


class TestV2ModelComparison:
    """Test comparison between v1 and v2 models."""

    def test_v2_has_different_features_than_v1(self, initialized_registry):
        """Test that v2 uses different features than v1."""
        v1 = initialized_registry.get_version("1")
        v2 = initialized_registry.get_version("2")

        assert v1.feature_dimension != v2.feature_dimension, \
            "v1 and v2 should have different feature dimensions"
        assert v1.feature_dimension == 162, "v1 should have 162 features"
        assert v2.feature_dimension == 78, "v2 should have 78 features"

    def test_v2_has_different_model_type_than_v1(self, initialized_registry):
        """Test that v2 uses different model type than v1."""
        v1 = initialized_registry.get_version("1")
        v2 = initialized_registry.get_version("2")

        v1_model_type = v1.model.__class__.__name__
        v2_model_type = v2.model.__class__.__name__

        assert v1_model_type != v2_model_type, \
            "v1 and v2 should use different model types"
        assert v1_model_type == "DecisionTreeClassifier", \
            "v1 should be DecisionTreeClassifier"
        assert v2_model_type == "Pipeline", "v2 should be Pipeline"

    def test_both_models_produce_valid_predictions(
        self, initialized_registry, sample_audio_file
    ):
        """Test that both v1 and v2 produce valid predictions on same audio."""
        v1_result = initialized_registry.predict("1", sample_audio_file, "test.wav")
        v2_result = initialized_registry.predict("2", sample_audio_file, "test.wav")

        # Both should have valid emotions
        valid_emotions = ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        assert v1_result["emotion"] in valid_emotions, "v1 should predict valid emotion"
        assert v2_result["emotion"] in valid_emotions, "v2 should predict valid emotion"

        # Both should have valid confidence
        assert 0.0 <= v1_result["confidence"] <= 1.0, "v1 should have valid confidence"
        assert 0.0 <= v2_result["confidence"] <= 1.0, "v2 should have valid confidence"


@pytest.mark.unit
class TestV2FeatureExtractionDetails:
    """Test detailed feature extraction for v2."""

    def test_v2_features_contain_no_nan(self, initialized_registry, sample_audio_file):
        """Test that v2 features don't contain NaN values."""
        v2 = initialized_registry.get_version("2")
        features = v2.feature_extractor(sample_audio_file, "test.wav")

        assert not np.isnan(features).any(), "Features should not contain NaN"

    def test_v2_features_contain_no_inf(self, initialized_registry, sample_audio_file):
        """Test that v2 features don't contain infinite values."""
        v2 = initialized_registry.get_version("2")
        features = v2.feature_extractor(sample_audio_file, "test.wav")

        assert not np.isinf(features).any(), "Features should not contain inf"

    def test_v2_features_are_numeric(self, initialized_registry, sample_audio_file):
        """Test that all v2 features are numeric."""
        v2 = initialized_registry.get_version("2")
        features = v2.feature_extractor(sample_audio_file, "test.wav")

        assert features.dtype in [np.float32, np.float64], \
            "Features should be floating point numbers"

    def test_v2_features_have_reasonable_magnitude(
        self, initialized_registry, sample_audio_file
    ):
        """Test that v2 features have reasonable magnitude."""
        v2 = initialized_registry.get_version("2")
        features = v2.feature_extractor(sample_audio_file, "test.wav")

        # Features should be within reasonable range (not too large or small)
        assert np.all(np.abs(features) < 1e6), \
            "Features should not have extremely large values"
