"""Tests for ModelInfo entity."""

import pytest

from app.domain.model.entities.model_info import ModelInfo
from app.domain.model.value_objects.model_version import ModelVersion


class TestModelInfoCreation:
    """Test ModelInfo entity creation and validation."""

    def test_v4_model_factory(self):
        """Test creating ModelInfo for V4 model using factory method."""
        model_info = ModelInfo.v4_model()

        assert model_info.version == ModelVersion.from_string("v4")
        assert model_info.model_type == "LSTM"
        assert model_info.feature_dimension == 180

    def test_invalid_version_type_raises_error(self):
        """Test that non-ModelVersion type raises ValueError."""
        with pytest.raises(ValueError, match="version must be ModelVersion instance"):
            ModelInfo(
                version="v4",  # Should be ModelVersion, not string
                model_type="LSTM",
                feature_dimension=180,
            )

    def test_invalid_model_type_type_raises_error(self):
        """Test that non-string model_type raises ValueError."""
        version = ModelVersion.from_string("v4")

        with pytest.raises(ValueError, match="model_type must be a string"):
            ModelInfo(
                version=version,
                model_type=123,  # Should be string
                feature_dimension=180,
            )

    def test_empty_model_type_raises_error(self):
        """Test that empty model_type raises ValueError."""
        version = ModelVersion.from_string("v4")

        with pytest.raises(ValueError, match="model_type cannot be empty"):
            ModelInfo(
                version=version,
                model_type="",
                feature_dimension=180,
            )

    def test_invalid_feature_dimension_type_raises_error(self):
        """Test that non-int feature_dimension raises ValueError."""
        version = ModelVersion.from_string("v4")

        with pytest.raises(ValueError, match="feature_dimension must be an integer"):
            ModelInfo(
                version=version,
                model_type="LSTM",
                feature_dimension=180.5,  # Should be int
            )

    def test_zero_feature_dimension_raises_error(self):
        """Test that zero feature_dimension raises ValueError."""
        version = ModelVersion.from_string("v4")

        with pytest.raises(ValueError, match="feature_dimension must be positive"):
            ModelInfo(
                version=version,
                model_type="LSTM",
                feature_dimension=0,
            )

    def test_negative_feature_dimension_raises_error(self):
        """Test that negative feature_dimension raises ValueError."""
        version = ModelVersion.from_string("v4")

        with pytest.raises(ValueError, match="feature_dimension must be positive"):
            ModelInfo(
                version=version,
                model_type="LSTM",
                feature_dimension=-10,
            )


class TestModelInfoFeatureCompatibility:
    """Test ModelInfo feature compatibility checking."""

    def test_is_compatible_with_features_matching_dimension(self):
        """Test compatibility check passes for matching dimension."""
        model_info = ModelInfo(
            version=ModelVersion.from_string("v4"),
            model_type="LSTM",
            feature_dimension=180,
        )

        assert model_info.is_compatible_with_features(180) is True

    def test_is_compatible_with_features_non_matching_dimension(self):
        """Test compatibility check fails for non-matching dimension."""
        model_info = ModelInfo(
            version=ModelVersion.from_string("v4"),
            model_type="LSTM",
            feature_dimension=180,
        )

        assert model_info.is_compatible_with_features(128) is False

    def test_is_compatible_with_features_zero_dimension(self):
        """Test compatibility check fails for zero dimension."""
        model_info = ModelInfo(
            version=ModelVersion.from_string("v4"),
            model_type="LSTM",
            feature_dimension=180,
        )

        assert model_info.is_compatible_with_features(0) is False


class TestModelInfoStringRepresentation:
    """Test ModelInfo string representation."""

    def test_str_representation(self):
        """Test string representation includes all key information."""
        version = ModelVersion.from_string("v4")
        model_info = ModelInfo(
            version=version,
            model_type="LSTM",
            feature_dimension=180,
        )

        str_repr = str(model_info)

        assert "ModelInfo" in str_repr
        assert "v4" in str_repr
        assert "LSTM" in str_repr
        assert "180" in str_repr
