"""Tests for ModelVersion value object."""

import pytest

from app.domain.model.value_objects.model_version import ModelVersion


class TestModelVersionValidation:
    """Test cases for ModelVersion validation."""

    def test_model_version_without_v_prefix_raises_error(self):
        """Test that version without 'v' prefix raises ValueError."""
        # Arrange
        invalid_versions = ["4", "123", "1"]

        # Act & Assert
        for invalid in invalid_versions:
            with pytest.raises(ValueError) as exc_info:
                ModelVersion(version=invalid)

            assert "must match pattern 'vN'" in str(exc_info.value)

    def test_model_version_with_non_numeric_suffix_raises_error(self):
        """Test that version with non-numeric suffix raises ValueError."""
        # Arrange
        invalid_versions = ["vabc", "v1.2", "v1a", "vfour"]

        # Act & Assert
        for invalid in invalid_versions:
            with pytest.raises(ValueError) as exc_info:
                ModelVersion(version=invalid)

            assert "must match pattern 'vN'" in str(exc_info.value)

    def test_model_version_empty_string_raises_error(self):
        """Test that empty version string raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            ModelVersion(version="")

        assert "Version cannot be empty" in str(exc_info.value)

    def test_model_version_non_string_raises_error(self):
        """Test that non-string version raises ValueError."""
        # Arrange
        invalid_values = [4, 4.0, None, ["v4"], {"version": "v4"}]

        # Act & Assert
        for invalid in invalid_values:
            with pytest.raises(ValueError) as exc_info:
                ModelVersion(version=invalid)

            assert "Version must be a string" in str(exc_info.value)

    def test_model_version_with_decimal_raises_error(self):
        """Test that version with decimal number raises ValueError."""
        # Arrange
        invalid_versions = ["v1.0", "v2.3.4", "v1.2"]

        # Act & Assert
        for invalid in invalid_versions:
            with pytest.raises(ValueError) as exc_info:
                ModelVersion(version=invalid)

            assert "must match pattern 'vN'" in str(exc_info.value)

    def test_model_version_with_leading_zero_is_valid(self):
        """Test that version with leading zeros is valid."""
        # Arrange & Act
        version = ModelVersion(version="v01")

        # Assert
        assert version.version == "v01"
        assert version.get_number() == 1


class TestModelVersionFactoryMethods:
    """Test cases for ModelVersion factory methods."""

    def test_from_string_without_v_prefix(self):
        """Test creating ModelVersion from string without 'v' prefix."""
        # Arrange & Act
        version = ModelVersion.from_string("4")

        # Assert
        assert version.version == "v4"
        assert version.get_number() == 4

    def test_from_string_adds_prefix_automatically(self):
        """Test that from_string adds 'v' prefix if missing."""
        # Arrange & Act
        version1 = ModelVersion.from_string("3")
        version2 = ModelVersion.from_string("v3")

        # Assert
        assert version1.version == "v3"
        assert version2.version == "v3"
        assert version1 == version2

    def test_from_number_with_zero_raises_error(self):
        """Test that version number 0 raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            ModelVersion.from_number(0)

        assert "must be a positive integer" in str(exc_info.value)

    def test_from_number_with_negative_raises_error(self):
        """Test that negative version number raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            ModelVersion.from_number(-1)

        assert "must be a positive integer" in str(exc_info.value)

    def test_from_number_with_non_integer_raises_error(self):
        """Test that non-integer version number raises ValueError."""
        # Arrange
        invalid_values = [4.0, "4", None, [4]]

        # Act & Assert
        for invalid in invalid_values:
            with pytest.raises(ValueError) as exc_info:
                ModelVersion.from_number(invalid)

            assert "must be a positive integer" in str(exc_info.value)


class TestModelVersionGetNumber:
    """Test cases for get_number method."""

    def test_get_number_extracts_version_number(self):
        """Test that get_number extracts integer from version string."""
        # Arrange & Act & Assert
        test_cases = [
            ("v1", 1),
            ("v4", 4),
            ("v10", 10),
            ("v999", 999),
        ]

        for version_str, expected_number in test_cases:
            version = ModelVersion(version=version_str)
            assert version.get_number() == expected_number


class TestModelVersionComparisons:
    """Test cases for ModelVersion comparison operators."""

    def test_model_version_less_than(self):
        """Test less than comparison between versions."""
        # Arrange
        v1 = ModelVersion(version="v1")
        v2 = ModelVersion(version="v2")
        v4 = ModelVersion(version="v4")

        # Assert
        assert v1 < v2
        assert v2 < v4
        assert v1 < v4
        assert not v4 < v2
        assert not v2 < v1

    def test_model_version_greater_than(self):
        """Test greater than comparison between versions."""
        # Arrange
        v1 = ModelVersion(version="v1")
        v2 = ModelVersion(version="v2")
        v4 = ModelVersion(version="v4")

        # Assert
        assert v4 > v2
        assert v2 > v1
        assert v4 > v1
        assert not v1 > v2
        assert not v2 > v4

    def test_model_version_less_than_or_equal(self):
        """Test less than or equal comparison between versions."""
        # Arrange
        v1 = ModelVersion(version="v1")
        v2 = ModelVersion(version="v2")
        v2_copy = ModelVersion(version="v2")

        # Assert
        assert v1 <= v2
        assert v2 <= v2_copy
        assert not v2 <= v1

    def test_model_version_greater_than_or_equal(self):
        """Test greater than or equal comparison between versions."""
        # Arrange
        v1 = ModelVersion(version="v1")
        v2 = ModelVersion(version="v2")
        v2_copy = ModelVersion(version="v2")

        # Assert
        assert v2 >= v1
        assert v2 >= v2_copy
        assert not v1 >= v2

    def test_model_version_comparison_with_large_numbers(self):
        """Test comparisons with large version numbers."""
        # Arrange
        v10 = ModelVersion(version="v10")
        v99 = ModelVersion(version="v99")
        v100 = ModelVersion(version="v100")

        # Assert
        assert v10 < v99 < v100
        assert v100 > v99 > v10

    def test_model_version_comparison_with_non_model_version_returns_not_implemented(self):
        """Test that comparing with non-ModelVersion returns NotImplemented."""
        # Arrange
        version = ModelVersion(version="v4")

        # Act & Assert
        # These should return NotImplemented, which Python handles appropriately
        assert version.__lt__("v5") is NotImplemented
        assert version.__gt__("v3") is NotImplemented
        assert version.__le__("v4") is NotImplemented
        assert version.__ge__("v4") is NotImplemented


class TestModelVersionImmutability:
    """Test cases for ModelVersion immutability."""

    def test_model_version_is_frozen(self):
        """Test that ModelVersion is immutable (frozen dataclass)."""
        # Arrange
        version = ModelVersion(version="v4")

        # Act & Assert
        with pytest.raises(Exception):  # FrozenInstanceError
            version.version = "v5"


class TestModelVersionEdgeCases:
    """Test cases for edge cases and special scenarios."""

    def test_model_version_sorting(self):
        """Test that ModelVersion instances can be sorted."""
        # Arrange
        versions = [
            ModelVersion(version="v4"),
            ModelVersion(version="v1"),
            ModelVersion(version="v3"),
            ModelVersion(version="v2"),
        ]

        # Act
        sorted_versions = sorted(versions)

        # Assert
        assert sorted_versions[0].version == "v1"
        assert sorted_versions[1].version == "v2"
        assert sorted_versions[2].version == "v3"
        assert sorted_versions[3].version == "v4"
