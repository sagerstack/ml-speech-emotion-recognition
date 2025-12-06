"""
Model Registry Service

This service provides automatic discovery and management of versioned local ML models.
It scans the models directory for v{number} folders and registers each model with its
corresponding feature extractor.

Features:
- Auto-discovery of model versions
- Dynamic feature extractor loading
- Model validation
- Centralized model access
- Latest version tracking
"""

import importlib.util
import json
import pickle
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from app.interfaces import validate_feature_extractor, validate_feature_output
from app.utils.config import get_settings
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ModelVersion:
    """Data class representing a registered model version"""

    version: str
    path: Path
    model: Any  # Scikit-learn model
    feature_extractor: Callable[[bytes, str], np.ndarray]
    metadata: dict
    feature_dimension: int
    scaler: Any | None = None  # StandardScaler for v3 compatibility


class ModelRegistry:
    """
    Centralized registry for all local ML models.

    This class discovers, validates, and manages multiple versions of ML models.
    Each model version must have:
    - model.pkl: Serialized scikit-learn model
    - feature_extractor.py: Module with extract_features function
    - metadata.json: Model metadata

    Usage:
        registry = ModelRegistry()
        registry.discover_models()

        # Get latest model
        model = registry.get_latest()

        # Get specific version
        model = registry.get_version("2")

        # Run inference
        prediction = registry.predict(model.version, audio_bytes, filename)
    """

    def __init__(self, models_path: Path | None = None):
        """
        Initialize the model registry.

        Args:
            models_path: Path to models directory (default: settings.models_dir)
        """
        settings = get_settings()
        self.models_path = models_path or Path(settings.models_dir)
        self.versions: dict[str, ModelVersion] = {}
        self.latest_version: str | None = None

    def discover_models(self) -> int:
        """
        Scan models directory and auto-register all valid model versions.

        Returns:
            int: Number of models successfully registered

        Raises:
            FileNotFoundError: If models directory doesn't exist
        """
        if not self.models_path.exists():
            raise FileNotFoundError(f"Models directory not found: {self.models_path}")

        # Pattern to match v1, v2, v3, etc.
        version_pattern = re.compile(r"^v(\d+)$")
        registered_count = 0

        # Scan for versioned directories
        for item in sorted(self.models_path.iterdir()):
            if not item.is_dir():
                continue

            match = version_pattern.match(item.name)
            if not match:
                continue

            version_number = match.group(1)

            try:
                self._register_version(version_number, item)
                registered_count += 1
                logger.info("Registered model version", version=version_number)
            except Exception as e:
                logger.error(
                    "Failed to register model version",
                    version=version_number,
                    error=str(e)
                )

        # Update latest version
        if self.versions:
            self.latest_version = max(self.versions.keys(), key=int)
            logger.info("Latest model version determined", version=self.latest_version)

        return registered_count

    def _register_version(self, version: str, path: Path) -> None:
        """
        Register a single model version.

        Args:
            version: Version number (e.g., "1", "2")
            path: Path to version directory

        Raises:
            FileNotFoundError: If required files are missing
            ValueError: If validation fails
        """
        # Check required files exist
        model_file = path / "model.pkl"
        extractor_file = path / "feature_extractor.py"
        metadata_file = path / "metadata.json"

        if not model_file.exists():
            raise FileNotFoundError(f"model.pkl not found in {path}")
        if not extractor_file.exists():
            raise FileNotFoundError(f"feature_extractor.py not found in {path}")
        if not metadata_file.exists():
            raise FileNotFoundError(f"metadata.json not found in {path}")

        # Load metadata
        with open(metadata_file) as f:
            metadata = json.load(f)

        # Load model (now returns model and scaler)
        model, scaler = self._load_model_pickle(model_file)

        # Dynamically import feature extractor
        extractor_module = self._import_extractor(extractor_file, version)

        # Validate feature extractor contract
        if not validate_feature_extractor(extractor_module):
            raise ValueError(
                f"Feature extractor for version {version} doesn't implement required interface"
            )

        # Create ModelVersion instance
        model_version = ModelVersion(
            version=version,
            path=path,
            model=model,
            feature_extractor=extractor_module.extract_features,
            metadata=metadata,
            feature_dimension=metadata.get("feature_dimension", 0),
            scaler=scaler,  # Add scaler to ModelVersion
        )

        # Register
        self.versions[version] = model_version

    def _load_model_pickle(self, model_file: Path):
        """
        Load a pickled model with custom unpickler that handles __main__ module references.

        Some models (like v3) were trained in notebooks and have classes saved under
        the __main__ module. This method remaps those references to the correct module.

        Args:
            model_file: Path to the .pkl file

        Returns:
            tuple: (model, scaler) where scaler is None if not present in the bundle

        Raises:
            Exception: If model cannot be loaded
        """

        # Create a custom unpickler that remaps __main__ to our modules
        class CustomUnpickler(pickle.Unpickler):
            def find_class(self, module, name):
                # Remap __main__.UltraEnsembleModel to app.models.UltraEnsembleModel
                if module == "__main__" and name == "UltraEnsembleModel":
                    from app.models import UltraEnsembleModel

                    return UltraEnsembleModel
                return super().find_class(module, name)

        with open(model_file, "rb") as f:
            model_obj = CustomUnpickler(f).load()

            # Some models (like v3) are saved as dictionaries with the actual model inside
            # Extract the model from the bundle if it's a dict
            if isinstance(model_obj, dict) and "model" in model_obj:
                model = model_obj["model"]
                scaler = model_obj.get("scaler", None)  # Extract scaler if present

                # Add classes_ attribute if available in the bundle
                # This is needed for scikit-learn compatibility
                if "class_labels" in model_obj and not hasattr(model, "classes_"):
                    model.classes_ = model_obj["class_labels"]

                return model, scaler  # Return both model and scaler

            return model_obj, None  # Return model and None for scaler

    def _import_extractor(self, extractor_path: Path, version: str):
        """
        Dynamically import a feature extractor module.

        Args:
            extractor_path: Path to feature_extractor.py
            version: Version number for module naming

        Returns:
            Imported module

        Raises:
            ImportError: If module cannot be imported
        """
        module_name = f"models.v{version}.feature_extractor"

        spec = importlib.util.spec_from_file_location(module_name, extractor_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load feature extractor from {extractor_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return module

    def get_version(self, version: str) -> ModelVersion | None:
        """
        Get a specific model version.

        Args:
            version: Version number (e.g., "1", "2")

        Returns:
            ModelVersion or None if not found
        """
        return self.versions.get(version)

    def get_latest(self) -> ModelVersion | None:
        """
        Get the latest model version.

        Returns:
            ModelVersion or None if no models registered
        """
        if self.latest_version:
            return self.versions.get(self.latest_version)
        return None

    def list_versions(self) -> list[str]:
        """
        Get list of all registered version numbers.

        Returns:
            List of version numbers sorted numerically
        """
        return sorted(self.versions.keys(), key=int)

    def predict(
        self,
        version: str,
        audio_bytes: bytes,
        filename: str,
        include_features: bool = False,
        audio_features: bool = False,
    ) -> dict:
        """
        Run inference using a specific model version.

        Args:
            version: Model version to use
            audio_bytes: Raw audio file bytes
            filename: Original filename
            include_features: Whether to include feature values in response
            audio_features: Whether to include audio_features matrices in response

        Returns:
            Dict with prediction results:
                {
                    "emotion": str,
                    "confidence": float,
                    "all_probabilities": Dict[str, float],
                    "model_version": str,
                    "model_type": str,
                    "feature_dimension": int,
                    "audio_features": Dict (optional, if audio_features=True)
                }

        Raises:
            ValueError: If version not found or prediction fails
        """
        model_version = self.get_version(version)
        if model_version is None:
            raise ValueError(f"Model version {version} not found")

        # Extract features (with or without audio_features)
        viz_data = None
        try:
            if audio_features:
                # Check if model version has extract_features_with_audio_data method
                extractor_module_path = model_version.path / "feature_extractor.py"
                extractor_module = self._import_extractor(extractor_module_path, version)

                if hasattr(extractor_module, "extract_features_with_audio_data"):
                    logger.debug(
                        "Using extract_features_with_audio_data for audio_features", version=version
                    )
                    result_dict = extractor_module.extract_features_with_audio_data(audio_bytes, filename)
                    features = result_dict["features"]
                    viz_data = result_dict["audio_features"]
                else:
                    logger.warning(
                        "Model version does not support audio_features, falling back to regular extraction",
                        version=version,
                    )
                    features = model_version.feature_extractor(audio_bytes, filename)
            else:
                # Regular feature extraction
                features = model_version.feature_extractor(audio_bytes, filename)

        except Exception as e:
            raise ValueError(f"Feature extraction failed: {str(e)}")

        # Validate features
        if not validate_feature_output(features, model_version.feature_dimension):
            raise ValueError(
                f"Invalid features: expected shape ({model_version.feature_dimension},), "
                f"got {features.shape}"
            )

        # Apply scaler if present (required for v3)
        if model_version.scaler is not None:
            features = model_version.scaler.transform(features.reshape(1, -1)).flatten()

        # Run prediction
        try:
            # Reshape for sklearn (expects 2D array)
            features_2d = features.reshape(1, -1)

            # Get prediction
            prediction = model_version.model.predict(features_2d)[0]

            # Get probability scores if available
            if hasattr(model_version.model, "predict_proba"):
                probabilities = model_version.model.predict_proba(features_2d)[0]
                classes = model_version.model.classes_
                all_probs = dict(zip(classes, probabilities.tolist()))
                # Get confidence for the predicted emotion, not the maximum probability
                confidence = all_probs.get(prediction, max(probabilities))
            else:
                # For models without probability scores (like decision trees without probability)
                all_probs = {prediction: 1.0}
                confidence = 1.0

            result = {
                "emotion": prediction,
                "confidence": float(confidence),
                "all_probabilities": all_probs,
                "model_version": version,
                "model_type": model_version.metadata.get("model_type", "unknown"),
                "feature_dimension": model_version.feature_dimension,
            }

            if include_features:
                feature_names = self._feature_names(model_version)
                result["features"] = dict(zip(feature_names, features.tolist()))

            # Include audio_features data if available
            if viz_data is not None:
                result["audio_features"] = self._serialize_audio_features_data(viz_data)
                logger.info(
                    "Visualization data included in response",
                    version=version,
                    viz_keys=list(viz_data.keys()),
                )

            return result

        except Exception as e:
            raise ValueError(f"Prediction failed: {str(e)}")

    def _serialize_audio_features_data(self, viz_data: dict[str, Any]) -> dict[str, Any]:
        """
        Serialize audio_features data for JSON response.

        Converts numpy arrays to lists and ensures all data types are JSON-serializable.
        The viz_data from extract_features_with_audio_data() should already have lists,
        but this method ensures consistency and handles edge cases.

        Args:
            viz_data: Visualization data dictionary from extract_features_with_audio_data()

        Returns:
            JSON-serializable dictionary

        Example:
            >>> viz_data = {"mel_spectrogram": [[0.1, 0.2], [0.3, 0.4]]}
            >>> serialized = self._serialize_audio_features_data(viz_data)
            >>> isinstance(serialized["mel_spectrogram"], list)
            True
        """
        serialized = {}

        for key, value in viz_data.items():
            if isinstance(value, np.ndarray):
                # Convert numpy arrays to lists
                serialized[key] = value.tolist()
            elif isinstance(value, (np.integer, np.floating)):
                # Convert numpy scalars to Python types
                serialized[key] = value.item()
            elif isinstance(value, list):
                # Already a list, keep as-is
                serialized[key] = value
            elif isinstance(value, (int, float, str)):
                # Native Python types, keep as-is
                serialized[key] = value
            else:
                # For any other type, try to convert to string
                logger.warning(
                    "Unexpected type in audio_features data, converting to string",
                    key=key,
                    type=type(value).__name__,
                )
                serialized[key] = str(value)

        return serialized

    def _feature_names(self, model_version: ModelVersion) -> list[str]:
        if model_version.version == "1" and model_version.feature_dimension == 162:
            return [
                "zero_crossing_rate",
                *[f"chroma_{i}" for i in range(12)],
                *[f"mfcc_{i}" for i in range(20)],
                "rms_energy",
                *[f"mel_{i}" for i in range(128)],
            ]

        if model_version.version == "2" and model_version.feature_dimension == 78:
            return [
                *[f"mfcc_mean_{i}" for i in range(13)],
                *[f"mfcc_std_{i}" for i in range(13)],
                *[f"delta_mean_{i}" for i in range(13)],
                *[f"delta_std_{i}" for i in range(13)],
                *[f"delta2_mean_{i}" for i in range(13)],
                *[f"delta2_std_{i}" for i in range(13)],
            ]

        return [f"feature_{i}" for i in range(model_version.feature_dimension)]

    def predict_all(self, audio_bytes: bytes, filename: str) -> list[dict]:
        """
        Run inference using ALL registered model versions.

        Args:
            audio_bytes: Raw audio file bytes
            filename: Original filename

        Returns:
            List of prediction results from all models
        """
        results = []

        for version in self.list_versions():
            try:
                result = self.predict(version, audio_bytes, filename)
                results.append(result)
            except Exception as e:
                # Include failed predictions with error info
                results.append({"model_version": version, "error": str(e), "success": False})

        return results

    def get_model_info(self, version: str) -> dict | None:
        """
        Get metadata information for a specific model version.

        Args:
            version: Version number

        Returns:
            Dict with model metadata or None if not found
        """
        model_version = self.get_version(version)
        if model_version is None:
            return None

        return {
            "version": version,
            "model_type": model_version.metadata.get("model_type"),
            "model_name": model_version.metadata.get("model_name"),
            "description": model_version.metadata.get("description"),
            "feature_dimension": model_version.feature_dimension,
            "feature_extraction": model_version.metadata.get("feature_extraction"),
            "classes": model_version.metadata.get("classes"),
            "num_classes": model_version.metadata.get("num_classes"),
            "created_date": model_version.metadata.get("created_date"),
            "dataset": model_version.metadata.get("dataset"),
            "notes": model_version.metadata.get("notes"),
        }


# Global registry instance
_registry: ModelRegistry | None = None


def get_registry() -> ModelRegistry:
    """
    Get the global model registry instance (singleton pattern).

    Returns:
        ModelRegistry instance
    """
    global _registry
    if _registry is None:
        _registry = ModelRegistry()
        _registry.discover_models()
    return _registry


def reload_registry() -> ModelRegistry:
    """
    Force reload of the model registry (for adding new models).

    Returns:
        New ModelRegistry instance
    """
    global _registry
    _registry = ModelRegistry()
    _registry.discover_models()
    return _registry
