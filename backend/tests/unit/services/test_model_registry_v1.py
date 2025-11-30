"""
Unit tests for Model Registry with v1 model.

This test suite validates the ModelRegistry service functionality:
- Model discovery finds v1
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
    # Calculate path relative to this test file
    # tests/unit/services/test_model_registry_v1.py -> ../../../models
    backend_dir = Path(__file__).resolve().parents[3]
    return backend_dir / "models"


@pytest.fixture
def v1_model_path(models_path):
    """Path to v1 model directory."""
    return models_path / "v1"


@pytest.fixture
def registry(models_path):
    """Create a fresh ModelRegistry instance."""
    return ModelRegistry(models_path=models_path)


@pytest.fixture
def initialized_registry(registry):
    """Create and initialize a ModelRegistry."""
    registry.discover_models()
    return registry


class TestModelRegistryInitialization:
    """Test ModelRegistry initialization."""

    def test_registry_initializes_with_default_path(self):
        """Test registry initializes with default models path."""
        registry = ModelRegistry()
        assert registry.models_path is not None
        assert isinstance(registry.models_path, Path)
        assert registry.versions == {}
        assert registry.latest_version is None

    def test_registry_initializes_with_custom_path(self, models_path):
        """Test registry initializes with custom path."""
        registry = ModelRegistry(models_path=models_path)
        assert registry.models_path == models_path
        assert registry.versions == {}
        assert registry.latest_version is None

    def test_registry_path_must_exist_for_discovery(self):
        """Test that discovery raises error if path doesn't exist."""
        fake_path = Path("/nonexistent/path/to/models")
        registry = ModelRegistry(models_path=fake_path)

        with pytest.raises(FileNotFoundError, match="Models directory not found"):
            registry.discover_models()


class TestModelDiscovery:
    """Test model discovery functionality."""

    def test_discover_models_finds_v1(self, registry):
        """Test that model discovery finds v1 model."""
        count = registry.discover_models()

        assert count >= 1, "Should discover at least v1 model"
        assert "1" in registry.versions, "Should register version 1"
        assert registry.latest_version is not None, "Should set latest version"

    def test_discovered_v1_has_correct_attributes(self, initialized_registry):
        """Test that discovered v1 model has all required attributes."""
        v1 = initialized_registry.get_version("1")

        assert v1 is not None, "v1 should be registered"
        assert isinstance(v1, ModelVersion), "Should be ModelVersion instance"
        assert v1.version == "1", "Version should be '1'"
        assert v1.path.exists(), "Model path should exist"
        assert v1.model is not None, "Model should be loaded"
        assert v1.feature_extractor is not None, "Feature extractor should be loaded"
        assert v1.metadata is not None, "Metadata should be loaded"
        assert v1.feature_dimension == 162, "Feature dimension should be 162"

    def test_v1_model_path_contains_required_files(self, v1_model_path):
        """Test that v1 directory contains all required files."""
        assert (v1_model_path / "model.pkl").exists(), "model.pkl should exist"
        assert (v1_model_path / "feature_extractor.py").exists(), "feature_extractor.py should exist"
        assert (v1_model_path / "metadata.json").exists(), "metadata.json should exist"

    def test_discover_models_returns_correct_count(self, registry):
        """Test that discover_models returns correct count."""
        count = registry.discover_models()
        assert count == len(registry.versions), \
            "Returned count should match registered versions"
        assert count >= 1, "Should have at least v1 registered"

    def test_latest_version_is_set_correctly(self, initialized_registry):
        """Test that latest_version points to highest version number."""
        latest_version = initialized_registry.latest_version

        assert latest_version is not None, "Latest version should be set"
        assert latest_version in initialized_registry.versions, \
            "Latest version should be in registered versions"

        # Latest should be the max version number
        all_versions = initialized_registry.list_versions()
        expected_latest = max(all_versions, key=int)
        assert latest_version == expected_latest, \
            f"Latest should be {expected_latest}, got {latest_version}"


class TestMetadataParsing:
    """Test metadata loading and parsing."""

    def test_v1_metadata_loaded_correctly(self, initialized_registry):
        """Test that v1 metadata is loaded and parsed correctly."""
        v1 = initialized_registry.get_version("1")

        assert v1.metadata is not None, "Metadata should be loaded"
        assert isinstance(v1.metadata, dict), "Metadata should be a dictionary"

        # Check required metadata fields
        assert "version" in v1.metadata, "Should have version field"
        assert "model_type" in v1.metadata, "Should have model_type field"
        assert "feature_dimension" in v1.metadata, "Should have feature_dimension field"
        assert "classes" in v1.metadata, "Should have classes field"

    def test_v1_metadata_values_correct(self, initialized_registry):
        """Test that v1 metadata values are correct."""
        v1 = initialized_registry.get_version("1")

        assert v1.metadata["version"] == "1", "Version should be '1'"
        assert v1.metadata["model_type"] == "DecisionTreeClassifier", \
            "Model type should be DecisionTreeClassifier"
        assert v1.metadata["feature_dimension"] == 162, \
            "Feature dimension should be 162"
        assert v1.metadata["num_classes"] == 6, "Should have 6 classes"

    def test_v1_classes_are_correct(self, initialized_registry):
        """Test that v1 has correct emotion classes."""
        v1 = initialized_registry.get_version("1")

        expected_classes = ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        actual_classes = v1.metadata["classes"]

        assert len(actual_classes) == 6, "Should have 6 classes"
        assert set(actual_classes) == set(expected_classes), \
            f"Classes should be {expected_classes}, got {actual_classes}"


class TestModelLoading:
    """Test model pickle loading."""

    def test_v1_model_loads_successfully(self, initialized_registry):
        """Test that v1 model loads from pickle successfully."""
        v1 = initialized_registry.get_version("1")

        assert v1.model is not None, "Model should be loaded"
        # Check it's a scikit-learn model
        assert hasattr(v1.model, 'predict'), "Model should have predict method"

    def test_v1_model_is_decision_tree(self, initialized_registry):
        """Test that v1 model is a DecisionTreeClassifier."""
        v1 = initialized_registry.get_version("1")

        model_class_name = v1.model.__class__.__name__
        assert model_class_name == "DecisionTreeClassifier", \
            f"Expected DecisionTreeClassifier, got {model_class_name}"

    def test_v1_model_has_classes(self, initialized_registry):
        """Test that loaded model has classes_ attribute."""
        v1 = initialized_registry.get_version("1")

        assert hasattr(v1.model, 'classes_'), "Model should have classes_ attribute"
        assert len(v1.model.classes_) == 6, "Model should have 6 classes"


class TestFeatureExtractorLoading:
    """Test dynamic feature extractor import."""

    def test_v1_feature_extractor_loaded(self, initialized_registry):
        """Test that v1 feature extractor is dynamically loaded."""
        v1 = initialized_registry.get_version("1")

        assert v1.feature_extractor is not None, "Feature extractor should be loaded"
        assert callable(v1.feature_extractor), "Feature extractor should be callable"

    def test_v1_feature_extractor_signature(self, initialized_registry):
        """Test that feature extractor has correct signature."""
        v1 = initialized_registry.get_version("1")

        # Should accept (bytes, str) parameters
        import inspect
        sig = inspect.signature(v1.feature_extractor)
        params = list(sig.parameters.keys())

        assert len(params) == 2, "Feature extractor should have 2 parameters"
        assert "audio_bytes" in params, "Should have audio_bytes parameter"
        assert "filename" in params, "Should have filename parameter"

    def test_v1_feature_extractor_produces_correct_output(
        self, initialized_registry, sample_audio_file
    ):
        """Test that feature extractor produces correct output shape."""
        v1 = initialized_registry.get_version("1")

        features = v1.feature_extractor(sample_audio_file, "test.wav")

        assert isinstance(features, np.ndarray), "Should return numpy array"
        assert features.shape == (162,), f"Expected (162,), got {features.shape}"
        assert features.dtype in [np.float32, np.float64], "Should be float type"


class TestVersionManagement:
    """Test version management methods."""

    def test_get_version_returns_correct_model(self, initialized_registry):
        """Test get_version returns correct ModelVersion."""
        v1 = initialized_registry.get_version("1")

        assert v1 is not None, "Should return v1"
        assert isinstance(v1, ModelVersion), "Should return ModelVersion instance"
        assert v1.version == "1", "Version should be '1'"

    def test_get_version_nonexistent_returns_none(self, initialized_registry):
        """Test get_version with nonexistent version returns None."""
        v999 = initialized_registry.get_version("999")

        assert v999 is None, "Nonexistent version should return None"

    def test_get_latest_returns_v1_when_only_v1_exists(self, initialized_registry):
        """Test get_latest returns v1 when it's the only/latest version."""
        latest = initialized_registry.get_latest()

        assert latest is not None, "Latest should not be None"
        assert isinstance(latest, ModelVersion), "Should return ModelVersion"
        # Could be v1 or higher if more versions exist
        assert int(latest.version) >= 1, "Latest version should be >= 1"

    def test_list_versions_includes_v1(self, initialized_registry):
        """Test list_versions includes v1."""
        versions = initialized_registry.list_versions()

        assert isinstance(versions, list), "Should return a list"
        assert "1" in versions, "Should include version 1"
        assert len(versions) >= 1, "Should have at least one version"

    def test_list_versions_sorted_numerically(self, initialized_registry):
        """Test that list_versions returns numerically sorted list."""
        versions = initialized_registry.list_versions()

        # Convert to integers and check sorting
        version_ints = [int(v) for v in versions]
        assert version_ints == sorted(version_ints), \
            "Versions should be sorted numerically"


class TestPredictMethod:
    """Test the predict() method."""

    def test_predict_with_v1_returns_valid_result(
        self, initialized_registry, sample_audio_file
    ):
        """Test predict with v1 returns valid prediction result."""
        result = initialized_registry.predict("1", sample_audio_file, "test.wav")

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
        result = initialized_registry.predict("1", sample_audio_file, "test.wav")

        valid_emotions = ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        assert result["emotion"] in valid_emotions, \
            f"Emotion should be one of {valid_emotions}, got {result['emotion']}"

    def test_predict_confidence_in_valid_range(
        self, initialized_registry, sample_audio_file
    ):
        """Test that confidence is in [0, 1] range."""
        result = initialized_registry.predict("1", sample_audio_file, "test.wav")

        confidence = result["confidence"]
        assert 0.0 <= confidence <= 1.0, \
            f"Confidence should be in [0, 1], got {confidence}"

    def test_predict_all_probabilities_sum_to_one(
        self, initialized_registry, sample_audio_file
    ):
        """Test that all probabilities sum to approximately 1.0."""
        result = initialized_registry.predict("1", sample_audio_file, "test.wav")

        all_probs = result["all_probabilities"]
        prob_sum = sum(all_probs.values())

        assert 0.99 <= prob_sum <= 1.01, \
            f"Probabilities should sum to ~1.0, got {prob_sum}"

    def test_predict_all_probabilities_has_all_classes(
        self, initialized_registry, sample_audio_file
    ):
        """Test that all_probabilities contains all emotion classes."""
        result = initialized_registry.predict("1", sample_audio_file, "test.wav")

        all_probs = result["all_probabilities"]
        expected_classes = {"angry", "disgust", "fear", "happy", "neutral", "sad"}

        assert set(all_probs.keys()) == expected_classes, \
            f"Should have all classes, got {set(all_probs.keys())}"

    def test_predict_model_version_correct(
        self, initialized_registry, sample_audio_file
    ):
        """Test that result includes correct model version."""
        result = initialized_registry.predict("1", sample_audio_file, "test.wav")

        assert result["model_version"] == "1", \
            f"Model version should be '1', got {result['model_version']}"

    def test_predict_model_type_correct(
        self, initialized_registry, sample_audio_file
    ):
        """Test that result includes correct model type."""
        result = initialized_registry.predict("1", sample_audio_file, "test.wav")

        assert result["model_type"] == "DecisionTreeClassifier", \
            f"Model type should be DecisionTreeClassifier, got {result['model_type']}"

    def test_predict_feature_dimension_correct(
        self, initialized_registry, sample_audio_file
    ):
        """Test that result includes correct feature dimension."""
        result = initialized_registry.predict("1", sample_audio_file, "test.wav")

        assert result["feature_dimension"] == 162, \
            f"Feature dimension should be 162, got {result['feature_dimension']}"

    def test_predict_highest_probability_matches_emotion(
        self, initialized_registry, sample_audio_file
    ):
        """Test that predicted emotion has highest probability."""
        result = initialized_registry.predict("1", sample_audio_file, "test.wav")

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


class TestPredictErrorHandling:
    """Test error handling in predict() method."""

    def test_predict_with_nonexistent_version_raises_error(
        self, initialized_registry, sample_audio_file
    ):
        """Test predict with nonexistent version raises ValueError."""
        with pytest.raises(ValueError, match="Model version .* not found"):
            initialized_registry.predict("999", sample_audio_file, "test.wav")

    def test_predict_with_invalid_audio_raises_error(
        self, initialized_registry, corrupted_audio_file
    ):
        """Test predict with invalid audio raises ValueError."""
        with pytest.raises(ValueError, match="Feature extraction failed"):
            initialized_registry.predict("1", corrupted_audio_file, "corrupted.wav")

    def test_predict_with_empty_audio_raises_error(self, initialized_registry):
        """Test predict with empty audio raises ValueError."""
        with pytest.raises(ValueError, match="Feature extraction failed"):
            initialized_registry.predict("1", b"", "empty.wav")


class TestGetModelInfo:
    """Test get_model_info() method."""

    def test_get_model_info_v1_returns_dict(self, initialized_registry):
        """Test get_model_info for v1 returns dictionary."""
        info = initialized_registry.get_model_info("1")

        assert info is not None, "Info should not be None"
        assert isinstance(info, dict), "Info should be a dictionary"

    def test_get_model_info_v1_has_required_fields(self, initialized_registry):
        """Test that model info has all required fields."""
        info = initialized_registry.get_model_info("1")

        required_fields = [
            "version", "model_type", "model_name", "description",
            "feature_dimension", "classes", "num_classes"
        ]

        for field in required_fields:
            assert field in info, f"Info should have {field} field"

    def test_get_model_info_v1_values_correct(self, initialized_registry):
        """Test that model info values are correct."""
        info = initialized_registry.get_model_info("1")

        assert info["version"] == "1", "Version should be '1'"
        assert info["model_type"] == "DecisionTreeClassifier", \
            "Model type should be DecisionTreeClassifier"
        assert info["feature_dimension"] == 162, "Feature dimension should be 162"
        assert info["num_classes"] == 6, "Should have 6 classes"
        assert len(info["classes"]) == 6, "Should have 6 classes in list"

    def test_get_model_info_nonexistent_returns_none(self, initialized_registry):
        """Test get_model_info with nonexistent version returns None."""
        info = initialized_registry.get_model_info("999")
        assert info is None, "Nonexistent version should return None"


class TestGlobalRegistrySingleton:
    """Test global registry singleton pattern."""

    def test_get_registry_returns_instance(self):
        """Test get_registry returns a ModelRegistry instance."""
        registry = get_registry()

        assert registry is not None, "Registry should not be None"
        assert isinstance(registry, ModelRegistry), \
            "Should return ModelRegistry instance"

    def test_get_registry_returns_same_instance(self):
        """Test get_registry returns the same instance (singleton)."""
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2, \
            "Should return the same instance (singleton pattern)"

    def test_get_registry_has_models_discovered(self):
        """Test that global registry has models already discovered."""
        registry = get_registry()

        # Should have discovered models automatically
        assert len(registry.versions) >= 1, \
            "Global registry should have discovered models"
        assert "1" in registry.versions, "Should have v1 registered"

    def test_reload_registry_creates_new_instance(self):
        """Test reload_registry creates a new instance."""
        original_registry = get_registry()
        reloaded_registry = reload_registry()

        # Should be a new instance
        assert reloaded_registry is not original_registry, \
            "reload_registry should create new instance"

        # But should have same models
        assert len(reloaded_registry.versions) >= 1, \
            "Reloaded registry should have models"


@pytest.mark.unit
class TestModelRegistryEdgeCases:
    """Test edge cases and error scenarios."""

    def test_registry_with_empty_directory(self, tmp_path):
        """Test registry with directory containing no models."""
        empty_dir = tmp_path / "empty_models"
        empty_dir.mkdir()

        registry = ModelRegistry(models_path=empty_dir)
        count = registry.discover_models()

        assert count == 0, "Should discover 0 models in empty directory"
        assert len(registry.versions) == 0, "Should have no versions"
        assert registry.latest_version is None, "Latest version should be None"

    def test_registry_ignores_non_versioned_directories(self, tmp_path):
        """Test that registry ignores directories not matching v{number} pattern."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        # Create directories that should be ignored
        (models_dir / "random_folder").mkdir()
        (models_dir / "v1abc").mkdir()
        (models_dir / "version1").mkdir()
        (models_dir / "1").mkdir()

        registry = ModelRegistry(models_path=models_dir)
        count = registry.discover_models()

        assert count == 0, "Should ignore non-matching directories"

    def test_registry_handles_incomplete_model_directory(self, tmp_path):
        """Test registry handles model directory missing required files."""
        models_dir = tmp_path / "models"
        models_dir.mkdir()

        # Create v1 directory with only metadata (missing model.pkl and feature_extractor.py)
        v1_dir = models_dir / "v1"
        v1_dir.mkdir()

        metadata = {"version": "1", "feature_dimension": 162}
        with open(v1_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f)

        registry = ModelRegistry(models_path=models_dir)
        count = registry.discover_models()

        # Should fail to register because files are missing
        assert count == 0, "Should not register incomplete model"
        assert "1" not in registry.versions, "v1 should not be registered"
