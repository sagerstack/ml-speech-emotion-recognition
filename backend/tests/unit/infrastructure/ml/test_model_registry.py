"""
Unit tests for ModelRegistry.

Tests the model registry functionality including:
- Model discovery and registration
- Model loading and pickle handling
- Feature extractor imports
- Prediction and inference
- Model information and metadata
"""

import json
import pickle
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import numpy as np
import pytest

from app.infrastructure.ml.model_registry import (
    ModelRegistry,
    ModelVersion,
    get_registry,
    reload_registry,
)


class TestModelVersion:
    """Test ModelVersion dataclass."""

    def test_model_version_creation(self):
        """Test creating a ModelVersion instance."""
        mock_model = Mock()
        mock_extractor = Mock()
        mock_path = Path("/fake/models/v1")

        model_version = ModelVersion(
            version="1",
            path=mock_path,
            model=mock_model,
            feature_extractor=mock_extractor,
            metadata={"model_type": "RandomForest"},
            feature_dimension=162,
            scaler=None,
        )

        assert model_version.version == "1"
        assert model_version.path == mock_path
        assert model_version.model == mock_model
        assert model_version.feature_extractor == mock_extractor
        assert model_version.metadata["model_type"] == "RandomForest"
        assert model_version.feature_dimension == 162
        assert model_version.scaler is None

    def test_model_version_with_scaler(self):
        """Test ModelVersion with scaler."""
        mock_scaler = Mock()

        model_version = ModelVersion(
            version="3",
            path=Path("/fake/models/v3"),
            model=Mock(),
            feature_extractor=Mock(),
            metadata={},
            feature_dimension=210,
            scaler=mock_scaler,
        )

        assert model_version.scaler == mock_scaler


class TestModelRegistryInitialization:
    """Test ModelRegistry initialization."""

    @patch("app.infrastructure.ml.model_registry.get_settings")
    def test_initialization_with_default_paths(self, mock_get_settings):
        """Test initialization with default paths."""
        mock_settings = Mock()
        mock_settings.models_dir = "/fake/models"
        mock_get_settings.return_value = mock_settings

        registry = ModelRegistry()

        assert registry.models_path == Path("/fake/models")
        assert registry.versions == {}
        assert registry.latest_version is None

    def test_initialization_with_custom_paths(self):
        """Test initialization with custom paths."""
        models_path = Path("/custom/models")
        infrastructure_path = Path("/custom/infrastructure")

        registry = ModelRegistry(models_path=models_path, infrastructure_path=infrastructure_path)

        assert registry.models_path == models_path
        assert registry.infrastructure_path == infrastructure_path

    def test_infrastructure_path_defaults_correctly(self):
        """Test that infrastructure path defaults to correct location."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        # Should be app/infrastructure/model relative to backend root
        assert registry.infrastructure_path.name == "model"
        assert str(registry.infrastructure_path).endswith("app/infrastructure/model")


class TestModelRegistryDiscovery:
    """Test model discovery functionality."""

    def test_discover_models_with_no_models_directory(self):
        """Test discovery when models directory doesn't exist."""
        registry = ModelRegistry(models_path=Path("/nonexistent/path"))

        with pytest.raises(FileNotFoundError) as exc_info:
            registry.discover_models()

        assert "Models directory not found" in str(exc_info.value)

    @patch("app.infrastructure.ml.model_registry.Path.exists")
    @patch("app.infrastructure.ml.model_registry.Path.is_dir")
    @patch("app.infrastructure.ml.model_registry.Path.iterdir")
    def test_discover_models_with_no_valid_versions(
        self, mock_iterdir, mock_is_dir, mock_exists
    ):
        """Test discovery with no valid version directories."""
        mock_exists.return_value = True
        mock_is_dir.return_value = False

        # Create fake non-version directories
        fake_items = [Path("/fake/models/README.md"), Path("/fake/models/data")]
        mock_iterdir.return_value = fake_items

        registry = ModelRegistry(models_path=Path("/fake/models"))
        count = registry.discover_models()

        assert count == 0
        assert len(registry.versions) == 0

    @patch("app.infrastructure.ml.model_registry.ModelRegistry._register_version")
    def test_discover_models_with_valid_versions(self, mock_register):
        """Test discovery with valid version directories."""
        import tempfile
        import os

        # Create actual temporary directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            models_path = Path(tmpdir)
            # Create version directories
            (models_path / "v1").mkdir()
            (models_path / "v2").mkdir()
            (models_path / "data").mkdir()  # Non-version directory

            registry = ModelRegistry(
                models_path=models_path,
                infrastructure_path=Path("/fake/infrastructure/model"),
            )

            count = registry.discover_models()

            # Should register v1 and v2, but not 'data'
            assert mock_register.call_count == 2

    @patch("app.infrastructure.ml.model_registry.ModelRegistry._register_version")
    def test_discover_models_sets_latest_version(self, mock_register):
        """Test that discover_models sets latest_version correctly."""
        import tempfile

        # Create actual temporary directory structure
        with tempfile.TemporaryDirectory() as tmpdir:
            models_path = Path(tmpdir)
            # Create version directories
            (models_path / "v1").mkdir()
            (models_path / "v3").mkdir()

            registry = ModelRegistry(
                models_path=models_path,
                infrastructure_path=Path("/fake/infrastructure/model"),
            )

            # Manually add versions to simulate successful registration
            registry.versions = {"1": Mock(), "3": Mock()}

            registry.discover_models()

            # Latest should be v3
            assert registry.latest_version == "3"


class TestModelRegistryRegistration:
    """Test model registration functionality."""

    @patch("pathlib.Path.exists")
    def test_register_version_missing_model_file(self, mock_exists):
        """Test registration fails when model.pkl is missing."""
        # model.pkl doesn't exist
        mock_exists.return_value = False

        registry = ModelRegistry(models_path=Path("/fake/models"))

        with pytest.raises(FileNotFoundError) as exc_info:
            registry._register_version("1", Path("/fake/models/v1"))

        assert "model.pkl not found" in str(exc_info.value)

    def test_register_version_missing_feature_extractor(self):
        """Test registration fails when feature_extractor.py is missing."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        with patch("pathlib.Path.exists") as mock_exists:
            # model.pkl exists, extractor doesn't
            mock_exists.side_effect = [True, False]

            version_path = Path("/fake/models/v1")

            with pytest.raises(FileNotFoundError) as exc_info:
                registry._register_version("1", version_path)

            assert "feature_extractor.py not found" in str(exc_info.value)

    def test_register_version_missing_metadata(self):
        """Test registration fails when metadata.json is missing."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        with patch("pathlib.Path.exists") as mock_exists:
            # model.pkl and extractor exist, metadata doesn't
            mock_exists.side_effect = [True, True, False]

            version_path = Path("/fake/models/v1")

            with pytest.raises(FileNotFoundError) as exc_info:
                registry._register_version("1", version_path)

            assert "metadata.json not found" in str(exc_info.value)


class TestModelRegistryPrediction:
    """Test prediction functionality."""

    @pytest.fixture
    def mock_registry_with_model(self):
        """Create a mock registry with a registered model."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        # Create mock model
        mock_model = Mock()
        mock_model.predict.return_value = np.array(["happy"])
        mock_model.predict_proba.return_value = np.array([[0.1, 0.05, 0.1, 0.6, 0.1, 0.05]])
        mock_model.classes_ = np.array(["angry", "disgust", "fear", "happy", "neutral", "sad"])

        # Create mock feature extractor
        mock_extractor = Mock(return_value=np.random.rand(162))

        # Create model version
        model_version = ModelVersion(
            version="1",
            path=Path("/fake/models/v1"),
            model=mock_model,
            feature_extractor=mock_extractor,
            metadata={"model_type": "RandomForest", "feature_dimension": 162},
            feature_dimension=162,
            scaler=None,
        )

        registry.versions = {"1": model_version}
        registry.latest_version = "1"

        return registry

    def test_predict_success(self, mock_registry_with_model):
        """Test successful prediction."""
        audio_bytes = b"fake audio data"
        filename = "test.wav"

        result = mock_registry_with_model.predict("1", audio_bytes, filename)

        assert result["emotion"] == "happy"
        assert result["confidence"] == 0.6
        assert result["model_version"] == "1"
        assert result["model_type"] == "RandomForest"
        assert result["feature_dimension"] == 162
        assert "all_probabilities" in result
        assert len(result["all_probabilities"]) == 6

    def test_predict_with_invalid_version(self, mock_registry_with_model):
        """Test prediction with non-existent version."""
        with pytest.raises(ValueError) as exc_info:
            mock_registry_with_model.predict("99", b"audio", "test.wav")

        assert "Model version 99 not found" in str(exc_info.value)

    def test_predict_with_include_features(self, mock_registry_with_model):
        """Test prediction with include_features=True."""
        result = mock_registry_with_model.predict(
            "1", b"fake audio", "test.wav", include_features=True
        )

        assert "features" in result
        assert isinstance(result["features"], dict)

    def test_predict_with_scaler(self):
        """Test prediction with scaler transformation."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        # Create mock scaler
        mock_scaler = Mock()
        mock_scaler.transform.return_value = np.array([[0.5] * 210])

        # Create mock model
        mock_model = Mock()
        mock_model.predict.return_value = np.array(["happy"])
        mock_model.predict_proba.return_value = np.array([[0.1, 0.05, 0.1, 0.6, 0.1, 0.05]])
        mock_model.classes_ = np.array(["angry", "disgust", "fear", "happy", "neutral", "sad"])

        # Create mock extractor
        mock_extractor = Mock(return_value=np.random.rand(210))

        model_version = ModelVersion(
            version="3",
            path=Path("/fake/models/v3"),
            model=mock_model,
            feature_extractor=mock_extractor,
            metadata={"model_type": "Ensemble", "feature_dimension": 210},
            feature_dimension=210,
            scaler=mock_scaler,
        )

        registry.versions = {"3": model_version}

        result = registry.predict("3", b"audio", "test.wav")

        # Verify scaler was called
        assert mock_scaler.transform.called
        assert result["emotion"] == "happy"

    def test_predict_without_probabilities(self):
        """Test prediction with model that doesn't support predict_proba."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        # Create mock model without predict_proba
        mock_model = Mock()
        mock_model.predict.return_value = np.array(["sad"])
        delattr(mock_model, "predict_proba")  # Remove predict_proba

        mock_extractor = Mock(return_value=np.random.rand(162))

        model_version = ModelVersion(
            version="1",
            path=Path("/fake/models/v1"),
            model=mock_model,
            feature_extractor=mock_extractor,
            metadata={"model_type": "DecisionTree", "feature_dimension": 162},
            feature_dimension=162,
            scaler=None,
        )

        registry.versions = {"1": model_version}

        result = registry.predict("1", b"audio", "test.wav")

        assert result["emotion"] == "sad"
        assert result["confidence"] == 1.0  # Should default to 1.0
        assert result["all_probabilities"] == {"sad": 1.0}

    def test_predict_feature_extraction_failure(self, mock_registry_with_model):
        """Test prediction when feature extraction fails."""
        # Make feature extractor raise exception
        mock_registry_with_model.versions["1"].feature_extractor.side_effect = Exception(
            "Feature extraction error"
        )

        with pytest.raises(ValueError) as exc_info:
            mock_registry_with_model.predict("1", b"audio", "test.wav")

        assert "Feature extraction failed" in str(exc_info.value)

    def test_predict_invalid_feature_dimension(self, mock_registry_with_model):
        """Test prediction with incorrect feature dimension."""
        # Return wrong dimension
        mock_registry_with_model.versions["1"].feature_extractor.return_value = np.random.rand(50)

        with pytest.raises(ValueError) as exc_info:
            mock_registry_with_model.predict("1", b"audio", "test.wav")

        assert "Invalid features" in str(exc_info.value)

    def test_predict_all(self, mock_registry_with_model):
        """Test predict_all with multiple models."""
        # Add second model
        mock_model2 = Mock()
        mock_model2.predict.return_value = np.array(["sad"])
        mock_model2.predict_proba.return_value = np.array([[0.1, 0.1, 0.1, 0.1, 0.1, 0.5]])
        mock_model2.classes_ = np.array(["angry", "disgust", "fear", "happy", "neutral", "sad"])

        mock_extractor2 = Mock(return_value=np.random.rand(78))

        model_version2 = ModelVersion(
            version="2",
            path=Path("/fake/models/v2"),
            model=mock_model2,
            feature_extractor=mock_extractor2,
            metadata={"model_type": "SVM", "feature_dimension": 78},
            feature_dimension=78,
            scaler=None,
        )

        mock_registry_with_model.versions["2"] = model_version2

        results = mock_registry_with_model.predict_all(b"audio", "test.wav")

        assert len(results) == 2
        assert results[0]["emotion"] == "happy"
        assert results[1]["emotion"] == "sad"

    def test_predict_all_with_failure(self, mock_registry_with_model):
        """Test predict_all when one model fails."""
        # Add failing model
        mock_extractor_failing = Mock(side_effect=Exception("Failed"))

        model_version_failing = ModelVersion(
            version="99",
            path=Path("/fake/models/v99"),
            model=Mock(),
            feature_extractor=mock_extractor_failing,
            metadata={"model_type": "Broken", "feature_dimension": 100},
            feature_dimension=100,
            scaler=None,
        )

        mock_registry_with_model.versions["99"] = model_version_failing

        results = mock_registry_with_model.predict_all(b"audio", "test.wav")

        # Should have 2 results: 1 success, 1 failure
        assert len(results) == 2

        # Find the failing result
        failing_result = next(r for r in results if r.get("model_version") == "99")
        assert "error" in failing_result
        assert failing_result["success"] is False


class TestModelRegistryAudioFeatures:
    """Test audio_features functionality."""

    def test_predict_with_audio_features(self):
        """Test prediction with audio_features=True."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        # Create mock model
        mock_model = Mock()
        mock_model.predict.return_value = np.array(["happy"])
        mock_model.predict_proba.return_value = np.array([[0.1, 0.05, 0.1, 0.6, 0.1, 0.05]])
        mock_model.classes_ = np.array(["angry", "disgust", "fear", "happy", "neutral", "sad"])

        # Create mock extractor module
        mock_extractor_module = Mock()
        mock_extractor_module.extract_features_with_audio_data = Mock(
            return_value={
                "features": np.random.rand(162),
                "audio_features": {"sample_rate": 22050, "mel_spectrogram": [[0.1] * 10] * 128},
            }
        )

        # Mock the import
        with patch.object(registry, "_import_extractor", return_value=mock_extractor_module):
            model_version = ModelVersion(
                version="1",
                path=Path("/fake/models/v1"),
                model=mock_model,
                feature_extractor=lambda x, y: np.random.rand(162),
                metadata={"model_type": "RF", "feature_dimension": 162},
                feature_dimension=162,
                scaler=None,
            )

            registry.versions = {"1": model_version}
            registry.infrastructure_path = Path("/fake/infrastructure/model")

            result = registry.predict("1", b"audio", "test.wav", audio_features=True)

            assert "audio_features" in result
            assert result["audio_features"]["sample_rate"] == 22050
            assert "mel_spectrogram" in result["audio_features"]

    def test_predict_with_audio_features_not_supported(self, ):
        """Test prediction with audio_features when model doesn't support it."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        # Create mock model
        mock_model = Mock()
        mock_model.predict.return_value = np.array(["happy"])
        mock_model.predict_proba.return_value = np.array([[0.1, 0.05, 0.1, 0.6, 0.1, 0.05]])
        mock_model.classes_ = np.array(["angry", "disgust", "fear", "happy", "neutral", "sad"])

        # Create mock extractor module without audio_features support
        mock_extractor_module = Mock(spec=[])  # No extract_features_with_audio_data

        mock_extractor = Mock(return_value=np.random.rand(162))

        with patch.object(registry, "_import_extractor", return_value=mock_extractor_module):
            model_version = ModelVersion(
                version="1",
                path=Path("/fake/models/v1"),
                model=mock_model,
                feature_extractor=mock_extractor,
                metadata={"model_type": "RF", "feature_dimension": 162},
                feature_dimension=162,
                scaler=None,
            )

            registry.versions = {"1": model_version}

            result = registry.predict("1", b"audio", "test.wav", audio_features=True)

            # Should succeed but without audio_features
            assert result["emotion"] == "happy"
            assert "audio_features" not in result or result.get("audio_features") is None


class TestModelRegistryAccessors:
    """Test model accessor methods."""

    @pytest.fixture
    def populated_registry(self):
        """Create registry with multiple versions."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        v1 = ModelVersion(
            version="1",
            path=Path("/fake/v1"),
            model=Mock(),
            feature_extractor=Mock(),
            metadata={"model_type": "RF", "model_name": "Random Forest v1"},
            feature_dimension=162,
        )

        v2 = ModelVersion(
            version="2",
            path=Path("/fake/v2"),
            model=Mock(),
            feature_extractor=Mock(),
            metadata={"model_type": "SVM", "model_name": "SVM v2"},
            feature_dimension=78,
        )

        registry.versions = {"1": v1, "2": v2}
        registry.latest_version = "2"

        return registry

    def test_get_version_exists(self, populated_registry):
        """Test getting an existing version."""
        version = populated_registry.get_version("1")

        assert version is not None
        assert version.version == "1"
        assert version.metadata["model_type"] == "RF"

    def test_get_version_not_exists(self, populated_registry):
        """Test getting a non-existent version."""
        version = populated_registry.get_version("99")

        assert version is None

    def test_get_latest(self, populated_registry):
        """Test getting latest version."""
        latest = populated_registry.get_latest()

        assert latest is not None
        assert latest.version == "2"

    def test_get_latest_no_models(self):
        """Test getting latest when no models registered."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        latest = registry.get_latest()

        assert latest is None

    def test_list_versions(self, populated_registry):
        """Test listing all versions."""
        versions = populated_registry.list_versions()

        assert versions == ["1", "2"]

    def test_list_versions_empty(self):
        """Test listing versions when none registered."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        versions = registry.list_versions()

        assert versions == []

    def test_get_model_info_exists(self, populated_registry):
        """Test getting model info for existing model."""
        info = populated_registry.get_model_info("1")

        assert info is not None
        assert info["version"] == "1"
        assert info["model_type"] == "RF"
        assert info["model_name"] == "Random Forest v1"
        assert info["feature_dimension"] == 162

    def test_get_model_info_not_exists(self, populated_registry):
        """Test getting model info for non-existent model."""
        info = populated_registry.get_model_info("99")

        assert info is None


class TestModelRegistrySerialization:
    """Test serialization utilities."""

    def test_serialize_audio_features_data_with_numpy_arrays(self):
        """Test serializing audio_features with numpy arrays."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        viz_data = {
            "mel_spectrogram": np.array([[0.1, 0.2], [0.3, 0.4]]),
            "sample_rate": np.int64(22050),
            "duration": np.float64(2.5),
        }

        serialized = registry._serialize_audio_features_data(viz_data)

        assert isinstance(serialized["mel_spectrogram"], list)
        assert isinstance(serialized["sample_rate"], int)
        assert isinstance(serialized["duration"], float)

    def test_serialize_audio_features_data_with_lists(self):
        """Test serializing audio_features with lists."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        viz_data = {"waveform": [0.1, 0.2, 0.3], "sample_rate": 22050}

        serialized = registry._serialize_audio_features_data(viz_data)

        assert serialized["waveform"] == [0.1, 0.2, 0.3]
        assert serialized["sample_rate"] == 22050

    def test_serialize_audio_features_data_with_unexpected_type(self):
        """Test serializing with unexpected data types."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        viz_data = {"custom_object": object()}

        serialized = registry._serialize_audio_features_data(viz_data)

        # Should convert to string
        assert isinstance(serialized["custom_object"], str)


class TestModelRegistryFeatureNames:
    """Test feature name generation."""

    def test_feature_names_v1(self):
        """Test feature names for v1 model."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        model_version = ModelVersion(
            version="1",
            path=Path("/fake/v1"),
            model=Mock(),
            feature_extractor=Mock(),
            metadata={},
            feature_dimension=162,
        )

        names = registry._feature_names(model_version)

        assert len(names) == 162
        assert names[0] == "zero_crossing_rate"
        assert names[1] == "chroma_0"
        assert "mfcc_0" in names
        assert "rms_energy" in names

    def test_feature_names_v2(self):
        """Test feature names for v2 model."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        model_version = ModelVersion(
            version="2",
            path=Path("/fake/v2"),
            model=Mock(),
            feature_extractor=Mock(),
            metadata={},
            feature_dimension=78,
        )

        names = registry._feature_names(model_version)

        assert len(names) == 78
        assert "mfcc_mean_0" in names
        assert "mfcc_std_0" in names
        assert "delta_mean_0" in names

    def test_feature_names_unknown_version(self):
        """Test feature names for unknown version."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        model_version = ModelVersion(
            version="99",
            path=Path("/fake/v99"),
            model=Mock(),
            feature_extractor=Mock(),
            metadata={},
            feature_dimension=100,
        )

        names = registry._feature_names(model_version)

        assert len(names) == 100
        assert names[0] == "feature_0"
        assert names[99] == "feature_99"


class TestModelRegistrySingleton:
    """Test singleton pattern for model registry."""

    @patch("app.infrastructure.ml.model_registry.ModelRegistry.discover_models")
    def test_get_registry_returns_singleton(self, mock_discover):
        """Test that get_registry returns the same instance."""
        # Reset global instance
        import app.infrastructure.ml.model_registry as registry_module

        registry_module._registry = None

        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2
        assert id(registry1) == id(registry2)

        # Should only discover once
        assert mock_discover.call_count == 1

    @patch("app.infrastructure.ml.model_registry.ModelRegistry.discover_models")
    def test_reload_registry_creates_new_instance(self, mock_discover):
        """Test that reload_registry creates a new instance."""
        # Reset global instance
        import app.infrastructure.ml.model_registry as registry_module

        registry_module._registry = None

        registry1 = get_registry()
        registry2 = reload_registry()

        # Should be different instances
        assert registry1 is not registry2

        # Should discover twice
        assert mock_discover.call_count == 2


class TestModelRegistryPickleLoading:
    """Test model pickle loading functionality."""

    def test_load_model_pickle_simple_model(self):
        """Test loading a simple pickled model."""
        import tempfile
        import pickle as pkl

        registry = ModelRegistry(models_path=Path("/fake/models"))

        # Create an actual pickle file with a simple object
        simple_model = {"type": "simple_model", "params": [1, 2, 3]}

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            pkl.dump(simple_model, f)
            temp_path = Path(f.name)

        try:
            model, scaler = registry._load_model_pickle(temp_path)

            assert model == simple_model
            assert scaler is None
        finally:
            temp_path.unlink()

    def test_load_model_pickle_with_bundle_no_classes(self):
        """Test loading a bundle dictionary without class_labels."""
        import tempfile
        import pickle as pkl

        registry = ModelRegistry(models_path=Path("/fake/models"))

        # Create a bundle with model and scaler but no class_labels
        inner_model = {"name": "inner_model"}
        inner_scaler = {"name": "scaler"}
        bundle = {"model": inner_model, "scaler": inner_scaler}

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            pkl.dump(bundle, f)
            temp_path = Path(f.name)

        try:
            model, scaler = registry._load_model_pickle(temp_path)

            assert model == inner_model
            assert scaler == inner_scaler
        finally:
            temp_path.unlink()

    def test_load_model_pickle_with_bundle_and_classes(self):
        """Test loading a bundle where model object gets classes_ attribute."""
        import tempfile
        import pickle as pkl
        from sklearn.linear_model import LogisticRegression

        registry = ModelRegistry(models_path=Path("/fake/models"))

        # Use a real sklearn model that can be pickled and have attributes set
        inner_model = LogisticRegression()
        inner_scaler = {"name": "scaler"}
        bundle = {"model": inner_model, "scaler": inner_scaler, "class_labels": ["angry", "happy"]}

        with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as f:
            pkl.dump(bundle, f)
            temp_path = Path(f.name)

        try:
            model, scaler = registry._load_model_pickle(temp_path)

            assert model is not None
            assert scaler == inner_scaler
            assert hasattr(model, "classes_")
            assert list(model.classes_) == ["angry", "happy"]
        finally:
            temp_path.unlink()


class TestModelRegistryImportExtractor:
    """Test feature extractor import functionality."""

    def test_import_extractor_success(self):
        """Test successfully importing a feature extractor."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        with patch("importlib.util.spec_from_file_location") as mock_spec_from_file:
            with patch("importlib.util.module_from_spec") as mock_module_from_spec:
                # Setup mocks
                mock_spec = Mock()
                mock_loader = Mock()
                mock_spec.loader = mock_loader
                mock_spec_from_file.return_value = mock_spec

                mock_module = Mock()
                mock_module_from_spec.return_value = mock_module

                result = registry._import_extractor(Path("/fake/extractor.py"), "1")

                assert result == mock_module
                assert mock_loader.exec_module.called

    def test_import_extractor_no_spec(self):
        """Test import when spec creation fails."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        with patch("importlib.util.spec_from_file_location", return_value=None):
            with pytest.raises(ImportError) as exc_info:
                registry._import_extractor(Path("/fake/extractor.py"), "1")

            assert "Cannot load feature extractor" in str(exc_info.value)

    def test_import_extractor_no_loader(self):
        """Test import when spec has no loader."""
        registry = ModelRegistry(models_path=Path("/fake/models"))

        with patch("importlib.util.spec_from_file_location") as mock_spec_from_file:
            mock_spec = Mock()
            mock_spec.loader = None
            mock_spec_from_file.return_value = mock_spec

            with pytest.raises(ImportError) as exc_info:
                registry._import_extractor(Path("/fake/extractor.py"), "1")

            assert "Cannot load feature extractor" in str(exc_info.value)
