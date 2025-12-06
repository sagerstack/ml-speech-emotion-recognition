"""File system-based model repository implementation."""

import json
import pickle
from pathlib import Path
from typing import Any

import joblib

from app.domain.model.entities.emotion_model import EmotionModel
from app.domain.model.entities.model_info import ModelInfo
from app.domain.model.exceptions.inference_error import InferenceError
from app.domain.model.exceptions.model_not_found_error import ModelNotFoundError
from app.domain.model.repositories.model_repository import ModelRepository
from app.domain.model.value_objects.model_version import ModelVersion
from app.infrastructure.model.emotion_model_adapter import SklearnEmotionModelAdapter
from app.infrastructure.observability.logging import get_logger


class FileSystemModelRepository(ModelRepository):
    """File system-based implementation of ModelRepository.

    This implementation loads models from local file system and metadata from infrastructure:

    models/                        # Model pickle files
      v4/
        model.pkl
      v5/
        model.pkl
      ...

    app/infrastructure/model/      # Metadata and feature extractors
      v4/
        metadata.json
        feature_extractor.py
      v5/
        metadata.json
        feature_extractor.py
      ...

    The implementation follows clean architecture principles:
    - Depends on domain abstractions (ModelRepository interface)
    - Implements infrastructure concerns (file system access, joblib loading)
    - Handles error translation from infrastructure to domain exceptions
    - Caches loaded models for performance
    """

    def __init__(self, models_dir: str = None, infrastructure_dir: str = None):
        """Initialize FileSystemModelRepository.

        Args:
            models_dir: Path to models directory. Defaults to 'models' in backend root.
            infrastructure_dir: Path to infrastructure/model directory for metadata.
                               Defaults to 'app/infrastructure/model' in backend root.
        """
        backend_root = Path(__file__).parents[3]

        if models_dir is None:
            # Default to backend/models directory
            self.models_dir = backend_root / "models"
        else:
            self.models_dir = Path(models_dir)

        if infrastructure_dir is None:
            # Default to backend/app/infrastructure/model directory
            self.infrastructure_dir = backend_root / "app" / "infrastructure" / "model"
        else:
            self.infrastructure_dir = Path(infrastructure_dir)

        # Cache for loaded models {version_str: EmotionModel (adapter)}
        self._model_cache: dict[str, EmotionModel] = {}

        # Initialize logger
        self.logger = get_logger(__name__)

    def load_model(self, version: ModelVersion) -> EmotionModel:
        """Load a trained model by version.

        Loads the model.pkl file using joblib, wraps it in SklearnEmotionModelAdapter,
        and returns the domain interface. Caches wrapped models after first load.

        Implementation strategy:
        1. Check cache for previously loaded model
        2. Load pickle file using joblib (may be UltraEnsembleModel, sklearn model, etc.)
        3. Wrap in SklearnEmotionModelAdapter to implement EmotionModel interface
        4. Cache and return the adapter

        Args:
            version: Model version to load

        Returns:
            EmotionModel: Adapter wrapping the loaded pickle model.
                         This implements the domain interface and isolates use cases
                         from pickle-specific details.

        Raises:
            ModelNotFoundError: If model version doesn't exist
            InferenceError: If model loading or adapter creation fails
        """
        version_str = str(version)

        # Check cache first (cached adapters, not raw pickle models)
        if version_str in self._model_cache:
            self.logger.debug("Model cache hit", version=version_str)
            return self._model_cache[version_str]

        self.logger.info("Loading model from disk", version=version_str)

        # Verify model exists
        if not self.model_exists(version):
            self.logger.error(
                "Model not found",
                version=version_str,
                models_dir=str(self.models_dir)
            )
            raise ModelNotFoundError(f"Model version {version_str} not found in {self.models_dir}")

        try:
            # Step 1: Load raw pickle model from file using custom unpickler
            # This handles models saved with __main__ module references (like v3/v4 UltraEnsembleModel)
            model_path = self._get_model_path(version)
            pickled_model = self._load_model_with_custom_unpickler(model_path)

            # Step 1.5: Extract model from dictionary structure if needed
            # Some models (like v3/v4) are saved as dictionaries with 'model', 'scaler', 'class_labels'
            actual_model = pickled_model
            if isinstance(pickled_model, dict) and 'model' in pickled_model:
                actual_model = pickled_model['model']

                # Add class_labels as classes_ attribute if available
                if 'class_labels' in pickled_model and not hasattr(actual_model, 'classes_'):
                    actual_model.classes_ = pickled_model['class_labels']

                self.logger.debug(
                    "Extracted model from dictionary structure",
                    version=version_str,
                    has_scaler='scaler' in pickled_model,
                    has_class_labels='class_labels' in pickled_model
                )

            # Step 2: Wrap in adapter to implement domain interface
            # The adapter converts pickle's predict_proba() to domain's predict_emotion_probabilities()
            emotion_model = SklearnEmotionModelAdapter(actual_model)

            # Step 3: Cache the wrapped adapter (not the raw pickle)
            self._model_cache[version_str] = emotion_model

            self.logger.info(
                "Model loaded successfully",
                version=version_str,
                model_type=type(emotion_model).__name__
            )

            return emotion_model

        except FileNotFoundError:
            self.logger.error("Model file not found", version=version_str)
            raise ModelNotFoundError(f"Model file not found for version {version_str}")
        except ValueError as e:
            # Adapter creation failed (e.g., model doesn't have predict_proba)
            self.logger.error(
                "Failed to create model adapter",
                version=version_str,
                error=str(e)
            )
            raise InferenceError(
                f"Failed to create adapter for model {version_str}: {str(e)}"
            )
        except Exception as e:
            self.logger.error(
                "Model load failed",
                version=version_str,
                error=str(e)
            )
            raise InferenceError(f"Failed to load model {version_str}: {str(e)}")

    def get_model_info(self, version: ModelVersion) -> ModelInfo | None:
        """Get metadata about a model version.

        Reads metadata.json from the model directory and constructs ModelInfo.
        Loads all available metadata fields including model_name, sklearn_version,
        dataset, classes, and other optional fields.

        Args:
            version: Model version to get info for

        Returns:
            ModelInfo if model exists and metadata is valid, None otherwise
        """
        if not self.model_exists(version):
            return None

        try:
            metadata_path = self._get_metadata_path(version)

            with open(metadata_path) as f:
                metadata = json.load(f)

            # Extract required fields from metadata
            model_type = metadata.get("model_type", "Unknown")
            feature_dimension = metadata.get("feature_dimension", 0)

            # Extract optional fields from metadata
            model_name = metadata.get("model_name")
            sklearn_version = metadata.get("sklearn_version")
            created_date = metadata.get("created_date")
            dataset = metadata.get("dataset")
            classes = metadata.get("classes")
            num_classes = metadata.get("num_classes")
            training_samples = metadata.get("training_samples")
            validation_dataset = metadata.get("validation_dataset")
            feature_extraction = metadata.get("feature_extraction")
            notes = metadata.get("notes")

            return ModelInfo(
                version=version,
                model_type=model_type,
                feature_dimension=feature_dimension,
                model_name=model_name,
                sklearn_version=sklearn_version,
                created_date=created_date,
                dataset=dataset,
                classes=classes,
                num_classes=num_classes,
                training_samples=training_samples,
                validation_dataset=validation_dataset,
                feature_extraction=feature_extraction,
                notes=notes,
            )

        except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError):
            # If metadata is missing or invalid, return None
            return None
        except Exception:
            # Catch any other errors and return None
            return None

    def list_available_versions(self) -> list[ModelVersion]:
        """List all available model versions.

        Scans the models directory for subdirectories that contain model.pkl.

        Returns:
            List of available model versions, sorted from newest to oldest
        """
        if not self.models_dir.exists():
            self.logger.warning("Models directory does not exist", models_dir=str(self.models_dir))
            return []

        versions = []

        for item in self.models_dir.iterdir():
            if not item.is_dir():
                continue

            # Check if model.pkl exists
            model_path = item / "model.pkl"
            if model_path.exists():
                try:
                    # Extract version from directory name
                    version_str = item.name
                    if not version_str.startswith("v"):
                        version_str = f"v{version_str}"

                    version = ModelVersion.from_string(version_str)
                    versions.append(version)
                except (ValueError, Exception):
                    # Skip invalid version names
                    continue

        # Sort from newest to oldest
        versions.sort(key=lambda v: v.get_number(), reverse=True)

        self.logger.debug(
            "Discovered model versions",
            count=len(versions),
            versions=[str(v) for v in versions]
        )

        return versions

    def model_exists(self, version: ModelVersion) -> bool:
        """Check if a model version exists.

        Checks if both the model directory and model.pkl file exist.

        Args:
            version: Model version to check

        Returns:
            True if model exists and can be loaded
        """
        try:
            model_path = self._get_model_path(version)
            return model_path.exists() and model_path.is_file()
        except Exception:
            return False

    def get_latest_version(self) -> ModelVersion | None:
        """Get the latest available model version.

        Returns:
            Latest ModelVersion if any models exist, None otherwise
        """
        versions = self.list_available_versions()

        if not versions:
            self.logger.warning("No model versions available")
            return None

        # Versions are already sorted newest to oldest
        latest = versions[0]
        self.logger.debug("Latest model version", version=str(latest))
        return latest

    # Private helper methods

    def _load_model_with_custom_unpickler(self, model_path: Path) -> Any:
        """Load a pickled model with custom unpickler that handles __main__ module references.

        Some models (like v3/v4 UltraEnsembleModel) were trained in notebooks and have classes
        saved under the __main__ module. This method remaps those references to the correct module.

        Args:
            model_path: Path to the .pkl file

        Returns:
            Loaded model object (may be a dict or the model itself)

        Raises:
            Exception: If model cannot be loaded
        """
        class CustomUnpickler(pickle.Unpickler):
            """Custom unpickler that remaps __main__ module references."""

            def find_class(self, module, name):
                """Remap __main__.UltraEnsembleModel to our infrastructure module."""
                if module == '__main__' and name == 'UltraEnsembleModel':
                    from app.infrastructure.model.ultra_ensemble import UltraEnsembleModel
                    return UltraEnsembleModel
                return super().find_class(module, name)

        with open(model_path, 'rb') as f:
            return CustomUnpickler(f).load()

    def _get_model_dir(self, version: ModelVersion) -> Path:
        """Get the directory path for a model version.

        Args:
            version: Model version

        Returns:
            Path to model directory
        """
        # Use version string for directory name (e.g., "v4")
        version_str = str(version)
        return self.models_dir / version_str

    def _get_model_path(self, version: ModelVersion) -> Path:
        """Get the model.pkl file path for a model version.

        Args:
            version: Model version

        Returns:
            Path to model.pkl file
        """
        return self._get_model_dir(version) / "model.pkl"

    def _get_metadata_path(self, version: ModelVersion) -> Path:
        """Get the metadata.json file path for a model version.

        Metadata is stored in the infrastructure/model directory following clean architecture.

        Args:
            version: Model version

        Returns:
            Path to metadata.json file
        """
        version_str = str(version)
        return self.infrastructure_dir / version_str / "metadata.json"
