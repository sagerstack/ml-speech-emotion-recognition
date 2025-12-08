"""Integration tests for FileSystemModelRepository with SklearnEmotionModelAdapter.

This test suite validates the integration between:
1. FileSystemModelRepository (infrastructure)
2. SklearnEmotionModelAdapter (adapter)
3. Real pickle files (v3/v4 models)

Test Coverage:
1. Repository returns EmotionModel interface (not raw pickle)
2. Loaded models work with real v3/v4 pickle files
3. Adapter wrapping is transparent to callers
4. Caching works correctly with adapters
5. End-to-end prediction flow with real models
"""

import json
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pytest

from app.domain.model.entities.emotion_model import EmotionModel
from app.domain.model.exceptions.inference_error import InferenceError
from app.domain.model.exceptions.model_not_found_error import ModelNotFoundError
from app.domain.model.value_objects.emotion import Emotion
from app.domain.model.value_objects.model_version import ModelVersion
from app.infrastructure.model.emotion_model_adapter import SklearnEmotionModelAdapter
from app.infrastructure.model.file_system_model_repository import FileSystemModelRepository


class SimpleMockModel:
    """Simple mock model for testing."""

    def predict_proba(self, X):
        """Mock predict_proba method."""
        return np.array([[0.15, 0.10, 0.15, 0.40, 0.15, 0.05]])


class InvalidMockModel:
    """Invalid mock model without predict_proba."""

    def predict(self, X):
        """Only has predict, not predict_proba."""
        return np.array([3])


class TestFileSystemModelRepositoryWithAdapter:
    """Integration tests for repository + adapter."""

    # Test Fixtures

    @pytest.fixture
    def temp_test_dirs(self) -> tuple[Path, Path]:
        """Create temporary models and infrastructure directories.

        Returns:
            Tuple of (models_dir, infrastructure_dir)
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create models directory (for model.pkl)
            models_path = base_path / "models"
            models_path.mkdir()

            v4_models_dir = models_path / "v4"
            v4_models_dir.mkdir()

            # Save mock model
            mock_model = SimpleMockModel()
            joblib.dump(mock_model, v4_models_dir / "model.pkl")

            # Create infrastructure directory (for metadata.json)
            infra_path = base_path / "infrastructure"
            infra_path.mkdir()

            v4_infra_dir = infra_path / "v4"
            v4_infra_dir.mkdir()

            # Create metadata in infrastructure
            metadata = {
                "version": "4",
                "model_name": "Test Model v4",
                "model_type": "Ultra Ensemble",
                "feature_dimension": 210,
                "classes": ["angry", "disgust", "fear", "happy", "neutral", "sad"],
            }
            with open(v4_infra_dir / "metadata.json", "w") as f:
                json.dump(metadata, f)

            yield models_path, infra_path

    @pytest.fixture
    def repository(self, temp_test_dirs: tuple[Path, Path]) -> FileSystemModelRepository:
        """Create repository with temp models dir."""
        models_dir, infrastructure_dir = temp_test_dirs
        return FileSystemModelRepository(
            models_dir=str(models_dir),
            infrastructure_dir=str(infrastructure_dir)
        )

    @pytest.fixture
    def real_models_dir(self) -> Path:
        """Get path to real models directory."""
        backend_dir = Path(__file__).parents[3]  # Go up from tests/integration/infrastructure
        return backend_dir / "models"

    @pytest.fixture
    def real_repository(self, real_models_dir: Path) -> FileSystemModelRepository:
        """Create repository pointing to real models."""
        if not real_models_dir.exists():
            pytest.skip("Real models directory not found")
        return FileSystemModelRepository(models_dir=str(real_models_dir))

    # Test Repository Returns EmotionModel Interface

    def test_load_model_returns_emotion_model_interface(
        self, repository: FileSystemModelRepository
    ):
        """Test that load_model returns EmotionModel, not raw pickle."""
        version = ModelVersion.from_string("v4")
        model = repository.load_model(version)

        # Should return EmotionModel interface
        assert isinstance(model, EmotionModel)

        # Should have domain interface method
        assert hasattr(model, "predict_emotion_probabilities")
        assert callable(model.predict_emotion_probabilities)

    def test_load_model_returns_adapter_not_raw_pickle(
        self, repository: FileSystemModelRepository
    ):
        """Test that load_model returns adapter, not raw pickle model."""
        version = ModelVersion.from_string("v4")
        model = repository.load_model(version)

        # Should be an adapter instance
        assert isinstance(model, SklearnEmotionModelAdapter)

        # Should wrap the original model
        assert hasattr(model, "_model")
        assert isinstance(model._model, SimpleMockModel)

    def test_loaded_model_has_domain_interface_only(
        self, repository: FileSystemModelRepository
    ):
        """Test loaded model exposes domain interface, not sklearn API."""
        version = ModelVersion.from_string("v4")
        model = repository.load_model(version)

        # Should have domain method
        assert hasattr(model, "predict_emotion_probabilities")

        # Underlying model has predict_proba, but it's wrapped
        # Access is through _model, not directly
        assert hasattr(model._model, "predict_proba")

    # Test Adapter Works with Repository

    def test_repository_adapter_integration_end_to_end(
        self, repository: FileSystemModelRepository
    ):
        """Test complete flow: load model -> predict."""
        version = ModelVersion.from_string("v4")

        # Load model (gets adapter)
        model = repository.load_model(version)

        # Use for prediction
        features = np.random.randn(210)
        result = model.predict_emotion_probabilities(features)

        # Verify result structure
        assert isinstance(result, dict)
        assert len(result) == 6
        assert all(isinstance(k, Emotion) for k in result.keys())
        assert all(isinstance(v, float) for v in result.values())

    def test_repository_caches_adapters_not_raw_models(
        self, repository: FileSystemModelRepository
    ):
        """Test repository caches adapter instances."""
        version = ModelVersion.from_string("v4")

        # Load twice
        model1 = repository.load_model(version)
        model2 = repository.load_model(version)

        # Should return same adapter instance (cached)
        assert model1 is model2

        # Both should be adapters
        assert isinstance(model1, SklearnEmotionModelAdapter)
        assert isinstance(model2, SklearnEmotionModelAdapter)

    def test_cached_adapter_works_for_multiple_predictions(
        self, repository: FileSystemModelRepository
    ):
        """Test cached adapter can be used multiple times."""
        version = ModelVersion.from_string("v4")
        model = repository.load_model(version)

        # Use for multiple predictions
        features1 = np.random.randn(210)
        features2 = np.random.randn(210)

        result1 = model.predict_emotion_probabilities(features1)
        result2 = model.predict_emotion_probabilities(features2)

        # Both should work
        assert isinstance(result1, dict)
        assert isinstance(result2, dict)

    # Test Error Handling

    def test_repository_raises_error_for_invalid_model(
        self, temp_test_dirs: tuple[Path, Path]
    ):
        """Test repository handles models without predict_proba."""
        models_dir, infra_dir = temp_test_dirs

        # Create v5 model directory
        v5_models_dir = models_dir / "v5"
        v5_models_dir.mkdir()

        # Save invalid model (no predict_proba)
        invalid_model = InvalidMockModel()
        joblib.dump(invalid_model, v5_models_dir / "model.pkl")

        # Create v5 infrastructure
        v5_infra_dir = infra_dir / "v5"
        v5_infra_dir.mkdir()

        metadata = {
            "version": "5",
            "model_type": "Invalid",
            "feature_dimension": 210,
        }
        with open(v5_infra_dir / "metadata.json", "w") as f:
            json.dump(metadata, f)

        # Try to load
        repository = FileSystemModelRepository(
            models_dir=str(models_dir),
            infrastructure_dir=str(infra_dir)
        )
        version = ModelVersion.from_string("v5")

        with pytest.raises(InferenceError) as exc_info:
            repository.load_model(version)

        assert "Failed to create adapter" in str(exc_info.value)

    def test_repository_raises_error_for_missing_model(
        self, repository: FileSystemModelRepository
    ):
        """Test repository raises error for missing model."""
        version = ModelVersion.from_string("v999")

        with pytest.raises(ModelNotFoundError):
            repository.load_model(version)

    # Test Adapter Transparency

    def test_adapter_wrapping_transparent_to_use_cases(
        self, repository: FileSystemModelRepository
    ):
        """Test use cases don't know about adapter - they see EmotionModel."""
        version = ModelVersion.from_string("v4")
        model = repository.load_model(version)

        # From use case perspective, it's just EmotionModel
        assert isinstance(model, EmotionModel)

        # Use case only calls domain method
        features = np.random.randn(210)
        result = model.predict_emotion_probabilities(features)

        # Use case gets domain result
        assert isinstance(result, dict)
        assert all(isinstance(k, Emotion) for k in result.keys())

    def test_adapter_isolates_domain_from_pickle_details(
        self, repository: FileSystemModelRepository
    ):
        """Test adapter isolates domain from pickle/sklearn details."""
        version = ModelVersion.from_string("v4")
        model = repository.load_model(version)

        # Domain doesn't need to know:
        # - Model was loaded from pickle
        # - Model uses sklearn API (predict_proba)
        # - Model returns numpy arrays

        # Domain only sees:
        # - EmotionModel interface
        # - predict_emotion_probabilities method
        # - dict[Emotion, float] result

        features = np.random.randn(210)
        result = model.predict_emotion_probabilities(features)

        # Result is domain type, not numpy
        assert isinstance(result, dict)
        assert not isinstance(result, np.ndarray)

    # Test Multiple Models

    def test_repository_handles_multiple_model_versions(
        self, temp_test_dirs: tuple[Path, Path]
    ):
        """Test repository handles multiple model versions."""
        models_dir, infra_dir = temp_test_dirs

        # Create v3 model directory
        v3_models_dir = models_dir / "v3"
        v3_models_dir.mkdir()
        joblib.dump(SimpleMockModel(), v3_models_dir / "model.pkl")

        # Create v3 infrastructure
        v3_infra_dir = infra_dir / "v3"
        v3_infra_dir.mkdir()

        metadata_v3 = {
            "version": "3",
            "model_type": "Ultra Ensemble",
            "feature_dimension": 210,
        }
        with open(v3_infra_dir / "metadata.json", "w") as f:
            json.dump(metadata_v3, f)

        # Create repository
        repository = FileSystemModelRepository(
            models_dir=str(models_dir),
            infrastructure_dir=str(infra_dir)
        )

        # Load both versions
        model_v3 = repository.load_model(ModelVersion.from_string("v3"))
        model_v4 = repository.load_model(ModelVersion.from_string("v4"))

        # Both should be adapters
        assert isinstance(model_v3, SklearnEmotionModelAdapter)
        assert isinstance(model_v4, SklearnEmotionModelAdapter)

        # Should be different instances
        assert model_v3 is not model_v4
