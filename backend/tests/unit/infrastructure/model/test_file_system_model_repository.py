"""Unit tests for FileSystemModelRepository."""

import json
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pytest

from app.domain.model.entities.model_info import ModelInfo
from app.domain.model.exceptions.model_not_found_error import ModelNotFoundError
from app.domain.model.value_objects.model_version import ModelVersion
from app.infrastructure.model.file_system_model_repository import FileSystemModelRepository


class SimpleMockModel:
    """Simple mock model that can be pickled."""

    def predict_proba(self, X):
        """Mock predict_proba method."""
        return np.array([[0.1, 0.2, 0.1, 0.4, 0.1, 0.1]])

    def predict(self, X):
        """Mock predict method."""
        return np.array([3])  # Index of max probability


class TestFileSystemModelRepository:
    """Test suite for FileSystemModelRepository."""

    @pytest.fixture
    def test_dirs(self) -> tuple[Path, Path]:
        """Create temporary models and infrastructure directories.

        Returns:
            Tuple of (models_dir, infrastructure_dir)
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            base_path = Path(temp_dir)

            # Create models directory structure (for model.pkl and metadata.json)
            models_path = base_path / "models"
            models_path.mkdir()

            v4_models_dir = models_path / "v4"
            v4_models_dir.mkdir()

            # Create a mock model.pkl (not a real model to save space)
            mock_model = SimpleMockModel()
            joblib.dump(mock_model, v4_models_dir / "model.pkl")

            # Create metadata.json alongside model.pkl (v6+ structure)
            metadata = {
                "version": "4",
                "model_name": "Ultra Ensemble Model v4",
                "model_type": "Ultra Ensemble",
                "feature_dimension": 210,
                "sklearn_version": "1.6.1",
                "created_date": "2024-12-03",
                "dataset": "CREMA-D",
                "classes": ["angry", "disgust", "fear", "happy", "neutral", "sad"],
                "num_classes": 6,
            }

            with open(v4_models_dir / "metadata.json", "w") as f:
                json.dump(metadata, f)

            # Create infrastructure directory (kept for compatibility, though not used for metadata anymore)
            infra_path = base_path / "infrastructure"
            infra_path.mkdir()

            yield models_path, infra_path

    @pytest.fixture
    def repository(self, test_dirs: tuple[Path, Path]) -> FileSystemModelRepository:
        """Create FileSystemModelRepository instance."""
        models_dir, infrastructure_dir = test_dirs
        return FileSystemModelRepository(
            models_dir=str(models_dir),
            infrastructure_dir=str(infrastructure_dir)
        )

    # Test load_model
    def test_load_model_returns_model(self, repository: FileSystemModelRepository):
        """Test that load_model successfully loads a model."""
        version = ModelVersion.from_string("v4")
        model = repository.load_model(version)

        assert model is not None
        # Model is wrapped in adapter, so it should have domain interface method
        assert hasattr(model, "predict_emotion_probabilities")

    def test_load_model_raises_error_for_nonexistent_version(
        self, repository: FileSystemModelRepository
    ):
        """Test that load_model raises ModelNotFoundError for nonexistent version."""
        version = ModelVersion.from_string("v999")

        with pytest.raises(ModelNotFoundError):
            repository.load_model(version)

    def test_load_model_caches_loaded_models(self, repository: FileSystemModelRepository):
        """Test that load_model caches models after first load."""
        version = ModelVersion.from_string("v4")

        # Load twice
        model1 = repository.load_model(version)
        model2 = repository.load_model(version)

        # Should be the same object (cached)
        assert model1 is model2

    # Test get_model_info
    def test_get_model_info_returns_correct_info(self, repository: FileSystemModelRepository):
        """Test that get_model_info returns correct ModelInfo."""
        version = ModelVersion.from_string("v4")
        info = repository.get_model_info(version)

        assert info is not None
        assert isinstance(info, ModelInfo)
        assert info.version == version
        assert info.model_type == "Ultra Ensemble"
        assert info.feature_dimension == 210

    def test_get_model_info_returns_none_for_nonexistent_version(
        self, repository: FileSystemModelRepository
    ):
        """Test that get_model_info returns None for nonexistent version."""
        version = ModelVersion.from_string("v999")
        info = repository.get_model_info(version)

        assert info is None

    # Test list_available_versions
    def test_list_available_versions_returns_versions(self, repository: FileSystemModelRepository):
        """Test that list_available_versions returns list of versions."""
        versions = repository.list_available_versions()

        assert len(versions) == 1
        assert versions[0] == ModelVersion.from_string("v4")

    def test_list_available_versions_returns_empty_for_empty_dir(self):
        """Test that list_available_versions returns empty list for empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = FileSystemModelRepository(models_dir=temp_dir)
            versions = repo.list_available_versions()

            assert versions == []

    # Test model_exists
    def test_model_exists_returns_true_for_existing_model(
        self, repository: FileSystemModelRepository
    ):
        """Test that model_exists returns True for existing model."""
        version = ModelVersion.from_string("v4")
        exists = repository.model_exists(version)

        assert exists is True

    def test_model_exists_returns_false_for_nonexistent_model(
        self, repository: FileSystemModelRepository
    ):
        """Test that model_exists returns False for nonexistent model."""
        version = ModelVersion.from_string("v999")
        exists = repository.model_exists(version)

        assert exists is False

    # Test get_latest_version
    def test_get_latest_version_returns_highest_version(
        self, repository: FileSystemModelRepository
    ):
        """Test that get_latest_version returns the highest version."""
        latest = repository.get_latest_version()

        assert latest is not None
        assert latest == ModelVersion.from_string("v4")

    def test_get_latest_version_returns_none_for_empty_dir(self):
        """Test that get_latest_version returns None for empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = FileSystemModelRepository(models_dir=temp_dir)
            latest = repo.get_latest_version()

            assert latest is None

    # Test error handling
    def test_load_model_raises_error_for_missing_model_file(
        self, test_dirs: tuple[Path, Path]
    ):
        """Test that load_model raises error if model.pkl is missing."""
        models_dir, infra_dir = test_dirs

        # Create v5 model directory without model.pkl
        v5_models_dir = models_dir / "v5"
        v5_models_dir.mkdir()

        # Create metadata in infrastructure
        v5_infra_dir = infra_dir / "v5"
        v5_infra_dir.mkdir()

        metadata = {"version": "5", "model_type": "Test", "feature_dimension": 210}
        with open(v5_infra_dir / "metadata.json", "w") as f:
            json.dump(metadata, f)

        repo = FileSystemModelRepository(
            models_dir=str(models_dir),
            infrastructure_dir=str(infra_dir)
        )
        version = ModelVersion.from_string("v5")

        with pytest.raises(ModelNotFoundError):
            repo.load_model(version)

    def test_get_model_info_handles_invalid_metadata(
        self, test_dirs: tuple[Path, Path]
    ):
        """Test that get_model_info handles invalid metadata gracefully."""
        models_dir, infra_dir = test_dirs

        # Create v5 model directory with model.pkl
        v5_models_dir = models_dir / "v5"
        v5_models_dir.mkdir()
        mock_model = SimpleMockModel()
        joblib.dump(mock_model, v5_models_dir / "model.pkl")

        # Create v5 infrastructure with invalid metadata
        v5_infra_dir = infra_dir / "v5"
        v5_infra_dir.mkdir()

        # Write invalid JSON
        with open(v5_infra_dir / "metadata.json", "w") as f:
            f.write("invalid json {")

        repo = FileSystemModelRepository(
            models_dir=str(models_dir),
            infrastructure_dir=str(infra_dir)
        )
        version = ModelVersion.from_string("v5")

        # Should return None instead of crashing
        info = repo.get_model_info(version)
        assert info is None

    # Integration tests
    def test_repository_with_real_latest_model_path(self):
        """Test repository with actual models directory and latest model."""
        # Use actual backend models directory
        backend_dir = Path(__file__).parents[4]  # Go up from tests/unit/infrastructure/model
        models_dir = backend_dir / "models"

        if not models_dir.exists():
            pytest.skip("Models directory not found")

        repo = FileSystemModelRepository(models_dir=str(models_dir))

        # Test latest model exists
        latest_version = repo.get_latest_version()
        if latest_version is None:
            pytest.skip("No model versions found")

        assert repo.model_exists(latest_version)

        # Test get model info
        info = repo.get_model_info(latest_version)
        assert info is not None
        assert info.feature_dimension == 210  # All current models use 210 features

    def test_full_repository_workflow(self, repository: FileSystemModelRepository):
        """Test complete workflow: check exists, get info, load model."""
        version = ModelVersion.from_string("v4")

        # Check exists
        assert repository.model_exists(version)

        # Get info
        info = repository.get_model_info(version)
        assert info is not None
        assert info.version == version

        # Load model
        model = repository.load_model(version)
        assert model is not None

        # Model should be cached
        model2 = repository.load_model(version)
        assert model is model2
