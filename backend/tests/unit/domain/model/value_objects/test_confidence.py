"""Tests for Confidence value object."""

import pytest

from app.domain.model.value_objects.confidence import Confidence


class TestConfidenceCreation:
    """Test cases for creating Confidence instances."""

    def test_create_confidence_with_integer(self):
        """Test creating Confidence with integer value."""
        # Arrange & Act
        confidence = Confidence(value=1)

        # Assert
        assert confidence.value == 1
        assert float(confidence) == 1.0


class TestConfidenceValidation:
    """Test cases for Confidence validation."""

    def test_confidence_below_zero_raises_error(self):
        """Test that confidence below 0.0 raises ValueError."""
        # Arrange
        invalid_values = [-0.1, -1.0, -100.0]

        # Act & Assert
        for value in invalid_values:
            with pytest.raises(ValueError) as exc_info:
                Confidence(value=value)

            assert "between 0.0 and 1.0" in str(exc_info.value)
            assert str(value) in str(exc_info.value)

    def test_confidence_above_one_raises_error(self):
        """Test that confidence above 1.0 raises ValueError."""
        # Arrange
        invalid_values = [1.1, 2.0, 100.0]

        # Act & Assert
        for value in invalid_values:
            with pytest.raises(ValueError) as exc_info:
                Confidence(value=value)

            assert "between 0.0 and 1.0" in str(exc_info.value)
            assert str(value) in str(exc_info.value)

    def test_confidence_with_non_numeric_raises_error(self):
        """Test that non-numeric confidence raises ValueError."""
        # Arrange
        invalid_values = ["0.5", None, [0.5], {"value": 0.5}]

        # Act & Assert
        for value in invalid_values:
            with pytest.raises(ValueError) as exc_info:
                Confidence(value=value)

            assert "must be a number" in str(exc_info.value)


class TestConfidenceImmutability:
    """Test cases for Confidence immutability."""

    def test_confidence_is_frozen(self):
        """Test that Confidence is immutable (frozen dataclass)."""
        # Arrange
        confidence = Confidence(value=0.8)

        # Act & Assert
        with pytest.raises(Exception):  # FrozenInstanceError in Python 3.10+
            confidence.value = 0.9


class TestConfidenceAsPercentage:
    """Test cases for as_percentage method."""

    def test_confidence_as_percentage_precision(self):
        """Test percentage conversion with various values."""
        # Arrange & Act & Assert
        test_cases = [
            (0.123, 12.3),
            (0.999, 99.9),
            (0.5, 50.0),
            (0.333, 33.3),
        ]

        for value, expected_percentage in test_cases:
            confidence = Confidence(value=value)
            assert confidence.as_percentage() == pytest.approx(expected_percentage)


class TestConfidenceThreshold:
    """Test cases for is_high_confidence method."""

    def test_is_high_confidence_default_threshold(self):
        """Test high confidence check with default threshold (0.7)."""
        # Arrange
        high_conf = Confidence(value=0.8)
        medium_conf = Confidence(value=0.7)
        low_conf = Confidence(value=0.6)

        # Assert
        assert high_conf.is_high_confidence() is True
        assert medium_conf.is_high_confidence() is True
        assert low_conf.is_high_confidence() is False

    def test_is_high_confidence_custom_threshold(self):
        """Test high confidence check with custom threshold."""
        # Arrange
        confidence = Confidence(value=0.75)

        # Assert
        assert confidence.is_high_confidence(threshold=0.7) is True
        assert confidence.is_high_confidence(threshold=0.75) is True
        assert confidence.is_high_confidence(threshold=0.8) is False

    def test_is_high_confidence_edge_cases(self):
        """Test high confidence with edge case values."""
        # Arrange
        zero_conf = Confidence(value=0.0)
        full_conf = Confidence(value=1.0)

        # Assert
        assert zero_conf.is_high_confidence() is False
        assert full_conf.is_high_confidence() is True
        assert full_conf.is_high_confidence(threshold=1.0) is True
        assert full_conf.is_high_confidence(threshold=0.0) is True


class TestConfidenceConversions:
    """Test cases for type conversions."""

    def test_confidence_float_conversion_in_operations(self):
        """Test that Confidence can be used in numeric operations via float()."""
        # Arrange
        confidence = Confidence(value=0.5)

        # Act & Assert
        assert float(confidence) * 2 == 1.0
        assert float(confidence) + 0.5 == 1.0
        assert float(confidence) < 1.0
        assert float(confidence) > 0.0

    def test_confidence_string_format_with_various_values(self):
        """Test string representation with various confidence values."""
        # Arrange & Act & Assert
        test_cases = [
            (0.0, "0.00%"),
            (1.0, "100.00%"),
            (0.5, "50.00%"),
            (0.123, "12.30%"),
            (0.999, "99.90%"),
        ]

        for value, expected_str in test_cases:
            confidence = Confidence(value=value)
            assert str(confidence) == expected_str




class TestConfidenceEdgeCases:
    """Test cases for edge cases and special scenarios."""

    def test_confidence_from_probability_validates_range(self):
        """Test that from_probability validates range."""
        # Act & Assert
        with pytest.raises(ValueError):
            Confidence.from_probability(1.5)

        with pytest.raises(ValueError):
            Confidence.from_probability(-0.5)
