"""Tests for AudioMetadata value object."""

import pytest

from app.domain.model.value_objects.audio_metadata import AudioMetadata


class TestAudioMetadataDurationValidation:
    """Test cases for duration validation."""

    def test_audio_metadata_with_zero_duration_raises_error(self):
        """Test that zero duration raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            AudioMetadata(duration_seconds=0.0, sample_rate=16000, channels=1)

        assert "Duration must be positive" in str(exc_info.value)

    def test_audio_metadata_with_negative_duration_raises_error(self):
        """Test that negative duration raises ValueError."""
        # Arrange
        invalid_durations = [-1.0, -5.5, -0.1]

        # Act & Assert
        for duration in invalid_durations:
            with pytest.raises(ValueError) as exc_info:
                AudioMetadata(duration_seconds=duration, sample_rate=16000, channels=1)

            assert "Duration must be positive" in str(exc_info.value)

    def test_audio_metadata_with_non_numeric_duration_raises_error(self):
        """Test that non-numeric duration raises ValueError."""
        # Arrange
        invalid_durations = ["5.5", None, [5.5], {"duration": 5.5}]

        # Act & Assert
        for duration in invalid_durations:
            with pytest.raises(ValueError) as exc_info:
                AudioMetadata(duration_seconds=duration, sample_rate=16000, channels=1)

            assert "Duration must be a number" in str(exc_info.value)


class TestAudioMetadataSampleRateValidation:
    """Test cases for sample rate validation."""

    def test_audio_metadata_with_zero_sample_rate_raises_error(self):
        """Test that zero sample rate raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            AudioMetadata(duration_seconds=5.0, sample_rate=0, channels=1)

        assert "Sample rate must be positive" in str(exc_info.value)

    def test_audio_metadata_with_negative_sample_rate_raises_error(self):
        """Test that negative sample rate raises ValueError."""
        # Arrange
        invalid_rates = [-16000, -1, -44100]

        # Act & Assert
        for rate in invalid_rates:
            with pytest.raises(ValueError) as exc_info:
                AudioMetadata(duration_seconds=5.0, sample_rate=rate, channels=1)

            assert "Sample rate must be positive" in str(exc_info.value)

    def test_audio_metadata_with_non_integer_sample_rate_raises_error(self):
        """Test that non-integer sample rate raises ValueError."""
        # Arrange
        invalid_rates = [16000.5, "16000", None, [16000]]

        # Act & Assert
        for rate in invalid_rates:
            with pytest.raises(ValueError) as exc_info:
                AudioMetadata(duration_seconds=5.0, sample_rate=rate, channels=1)

            assert "Sample rate must be an integer" in str(exc_info.value)


class TestAudioMetadataChannelsValidation:
    """Test cases for channels validation."""

    def test_audio_metadata_with_zero_channels_raises_error(self):
        """Test that zero channels raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            AudioMetadata(duration_seconds=5.0, sample_rate=16000, channels=0)

        assert "Channels must be positive" in str(exc_info.value)

    def test_audio_metadata_with_negative_channels_raises_error(self):
        """Test that negative channels raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            AudioMetadata(duration_seconds=5.0, sample_rate=16000, channels=-1)

        assert "Channels must be positive" in str(exc_info.value)

    def test_audio_metadata_with_more_than_two_channels_raises_error(self):
        """Test that more than 2 channels raises ValueError."""
        # Arrange
        invalid_channels = [3, 4, 5, 8]

        # Act & Assert
        for channels in invalid_channels:
            with pytest.raises(ValueError) as exc_info:
                AudioMetadata(duration_seconds=5.0, sample_rate=16000, channels=channels)

            assert "Only mono (1) and stereo (2) audio supported" in str(exc_info.value)

    def test_audio_metadata_with_non_integer_channels_raises_error(self):
        """Test that non-integer channels raises ValueError."""
        # Arrange
        invalid_channels = [1.5, "1", None, [1]]

        # Act & Assert
        for channels in invalid_channels:
            with pytest.raises(ValueError) as exc_info:
                AudioMetadata(duration_seconds=5.0, sample_rate=16000, channels=channels)

            assert "Channels must be an integer" in str(exc_info.value)


class TestAudioMetadataChannelMethods:
    """Test cases for channel-related methods."""

    def test_is_mono_returns_true_for_mono_audio(self):
        """Test that is_mono returns True for 1 channel."""
        # Arrange
        metadata = AudioMetadata(duration_seconds=5.0, sample_rate=16000, channels=1)

        # Act & Assert
        assert metadata.is_mono() is True
        assert metadata.is_stereo() is False

    def test_is_stereo_returns_true_for_stereo_audio(self):
        """Test that is_stereo returns True for 2 channels."""
        # Arrange
        metadata = AudioMetadata(duration_seconds=5.0, sample_rate=16000, channels=2)

        # Act & Assert
        assert metadata.is_stereo() is True
        assert metadata.is_mono() is False


class TestAudioMetadataTotalSamples:
    """Test cases for total_samples calculation."""

    def test_total_samples_calculation(self):
        """Test that total_samples calculates correctly."""
        # Arrange
        metadata = AudioMetadata(duration_seconds=5.0, sample_rate=16000, channels=1)

        # Act
        total = metadata.total_samples()

        # Assert
        assert total == 80000  # 5.0 * 16000

    def test_total_samples_with_fractional_duration(self):
        """Test total_samples with fractional duration."""
        # Arrange
        metadata = AudioMetadata(duration_seconds=2.5, sample_rate=44100, channels=2)

        # Act
        total = metadata.total_samples()

        # Assert
        expected = int(2.5 * 44100)
        assert total == expected
        assert total == 110250

    def test_total_samples_with_various_configurations(self):
        """Test total_samples with various audio configurations."""
        # Arrange & Act & Assert
        test_cases = [
            (1.0, 8000, 8000),
            (2.0, 22050, 44100),
            (0.5, 48000, 24000),
            (10.0, 16000, 160000),
        ]

        for duration, sample_rate, expected_total in test_cases:
            metadata = AudioMetadata(duration_seconds=duration, sample_rate=sample_rate, channels=1)
            assert metadata.total_samples() == expected_total


class TestAudioMetadataImmutability:
    """Test cases for AudioMetadata immutability."""

    def test_audio_metadata_is_frozen(self):
        """Test that AudioMetadata is immutable (frozen dataclass)."""
        # Arrange
        metadata = AudioMetadata(duration_seconds=5.0, sample_rate=16000, channels=1)

        # Act & Assert
        with pytest.raises(Exception):  # FrozenInstanceError
            metadata.duration_seconds = 10.0


class TestAudioMetadataStringRepresentation:
    """Test cases for AudioMetadata string representation."""

    def test_audio_metadata_string_representation_mono(self):
        """Test string representation for mono audio."""
        # Arrange
        metadata = AudioMetadata(duration_seconds=5.5, sample_rate=16000, channels=1)

        # Act
        string_repr = str(metadata)

        # Assert
        assert "5.50s" in string_repr
        assert "16000Hz" in string_repr
        assert "mono" in string_repr

    def test_audio_metadata_string_representation_stereo(self):
        """Test string representation for stereo audio."""
        # Arrange
        metadata = AudioMetadata(duration_seconds=3.25, sample_rate=44100, channels=2)

        # Act
        string_repr = str(metadata)

        # Assert
        assert "3.25s" in string_repr
        assert "44100Hz" in string_repr
        assert "stereo" in string_repr

    def test_audio_metadata_string_format_precision(self):
        """Test that duration is formatted with 2 decimal places."""
        # Arrange
        metadata = AudioMetadata(duration_seconds=1.123456, sample_rate=16000, channels=1)

        # Act
        string_repr = str(metadata)

        # Assert
        assert "1.12s" in string_repr  # Rounded to 2 decimal places


class TestAudioMetadataFactoryMethod:
    """Test cases for create factory method."""

    def test_factory_method_validates_parameters(self):
        """Test that create factory method validates parameters."""
        # Act & Assert
        with pytest.raises(ValueError):
            AudioMetadata.create(duration_seconds=-1.0, sample_rate=16000, channels=1)

        with pytest.raises(ValueError):
            AudioMetadata.create(duration_seconds=5.0, sample_rate=0, channels=1)

        with pytest.raises(ValueError):
            AudioMetadata.create(duration_seconds=5.0, sample_rate=16000, channels=3)
