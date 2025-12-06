"""Model information entity."""

from dataclasses import dataclass

from app.domain.model.value_objects.model_version import ModelVersion


@dataclass
class ModelInfo:
    """Model metadata and information.

    Contains metadata about a trained ML model including version,
    type, and technical specifications. This entity represents
    the core information needed to work with a model.

    Attributes:
        version: Model version identifier
        model_type: Type of model architecture (e.g., 'LSTM', 'CNN', 'Transformer')
        feature_dimension: Expected input feature dimension
        model_name: Descriptive name of the model (optional)
        sklearn_version: Version of scikit-learn used (optional)
        created_date: Date when model was created (optional)
        dataset: Dataset used for training (optional)
        classes: List of emotion classes (optional)
        num_classes: Number of emotion classes (optional)
        training_samples: Number of training samples (optional)
        validation_dataset: Dataset used for validation (optional)
        feature_extraction: Description of feature extraction method (optional)
        notes: Additional notes about the model (optional)
    """

    version: ModelVersion
    model_type: str
    feature_dimension: int
    model_name: str | None = None
    sklearn_version: str | None = None
    created_date: str | None = None
    dataset: str | None = None
    classes: list[str] | None = None
    num_classes: int | None = None
    training_samples: str | None = None
    validation_dataset: str | None = None
    feature_extraction: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        """Validate model information."""
        if not isinstance(self.version, ModelVersion):
            raise ValueError(f"version must be ModelVersion instance, got {type(self.version)}")

        if not isinstance(self.model_type, str):
            raise ValueError(f"model_type must be a string, got {type(self.model_type)}")

        if not self.model_type:
            raise ValueError("model_type cannot be empty")

        if not isinstance(self.feature_dimension, int):
            raise ValueError(
                f"feature_dimension must be an integer, got {type(self.feature_dimension)}"
            )

        if self.feature_dimension <= 0:
            raise ValueError(f"feature_dimension must be positive, got {self.feature_dimension}")

    @classmethod
    def create(
        cls,
        version: ModelVersion,
        model_type: str,
        feature_dimension: int,
        model_name: str | None = None,
        sklearn_version: str | None = None,
        created_date: str | None = None,
        dataset: str | None = None,
        classes: list[str] | None = None,
        num_classes: int | None = None,
        training_samples: str | None = None,
        validation_dataset: str | None = None,
        feature_extraction: str | None = None,
        notes: str | None = None,
    ) -> "ModelInfo":
        """Factory method to create ModelInfo.

        Args:
            version: Model version identifier
            model_type: Type of model architecture
            feature_dimension: Expected input feature dimension
            model_name: Descriptive name of the model (optional)
            sklearn_version: Version of scikit-learn used (optional)
            created_date: Date when model was created (optional)
            dataset: Dataset used for training (optional)
            classes: List of emotion classes (optional)
            num_classes: Number of emotion classes (optional)
            training_samples: Number of training samples (optional)
            validation_dataset: Dataset used for validation (optional)
            feature_extraction: Description of feature extraction method (optional)
            notes: Additional notes about the model (optional)

        Returns:
            ModelInfo instance

        Raises:
            ValueError: If any parameter is invalid
        """
        return cls(
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

    @classmethod
    def v4_model(cls) -> "ModelInfo":
        """Create ModelInfo for V4 model.

        V4 is the current production model with LSTM architecture
        and 180-dimensional feature input (30 MFCCs * 6 statistical features).

        Returns:
            ModelInfo instance for V4 model
        """
        return cls(
            version=ModelVersion.from_string("v4"),
            model_type="LSTM",
            feature_dimension=180,
        )

    def is_compatible_with_features(self, features_dimension: int) -> bool:
        """Check if features are compatible with this model.

        Args:
            features_dimension: Dimension of extracted features

        Returns:
            True if features dimension matches model's expected dimension
        """
        return features_dimension == self.feature_dimension

    def __str__(self) -> str:
        """String representation."""
        return (
            f"ModelInfo(version={self.version}, "
            f"type={self.model_type}, "
            f"features={self.feature_dimension}D)"
        )
