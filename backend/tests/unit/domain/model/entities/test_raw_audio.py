"""Tests for RawAudio entity."""

import pytest

from app.domain.model.entities.raw_audio import RawAudio
from app.domain.model.exceptions.invalid_audio_error import InvalidAudioError


class TestRawAudioCreation:
    """Test RawAudio entity creation and validation."""

    def test_create_valid_raw_audio(self):
        """Test creating a valid RawAudio instance."""
        audio_bytes = b"fake audio data"
        filename = "test.wav"

        audio = RawAudio(bytes=audio_bytes, filename=filename)

        assert audio.bytes == audio_bytes
        assert audio.filename == filename

    def test_from_bytes_factory_method(self):
        """Test creating RawAudio using from_bytes factory method."""
        audio_bytes = b"fake audio data"
        filename = "test.wav"

        audio = RawAudio.from_bytes(audio_bytes, filename)

        assert audio.bytes == audio_bytes
        assert audio.filename == filename

    def test_empty_bytes_raises_error(self):
        """Test that empty bytes raise InvalidAudioError."""
        with pytest.raises(InvalidAudioError, match="Audio data cannot be empty"):
            RawAudio(bytes=b"", filename="test.wav")

    def test_invalid_bytes_type_raises_error(self):
        """Test that non-bytes type raises InvalidAudioError."""
        with pytest.raises(InvalidAudioError, match="Audio data must be bytes"):
            RawAudio(bytes="not bytes", filename="test.wav")

    def test_empty_filename_raises_error(self):
        """Test that empty filename raises InvalidAudioError."""
        with pytest.raises(InvalidAudioError, match="Filename cannot be empty"):
            RawAudio(bytes=b"data", filename="")

    def test_invalid_filename_type_raises_error(self):
        """Test that non-string filename raises InvalidAudioError."""
        with pytest.raises(InvalidAudioError, match="Filename must be a string"):
            RawAudio(bytes=b"data", filename=123)


class TestRawAudioSizeValidation:
    """Test RawAudio size validation methods."""

    def test_validate_size_within_limit(self):
        """Test that size validation passes for files within limit."""
        # 1 KB of data
        audio_bytes = b"a" * 1024
        audio = RawAudio(bytes=audio_bytes, filename="test.wav")

        # Should not raise
        audio.validate_size(max_size_mb=1)

    def test_validate_size_exceeds_limit_raises_error(self):
        """Test that size validation fails for files exceeding limit."""
        # 2 MB of data
        audio_bytes = b"a" * (2 * 1024 * 1024)
        audio = RawAudio(bytes=audio_bytes, filename="test.wav")

        with pytest.raises(InvalidAudioError, match="Audio file too large"):
            audio.validate_size(max_size_mb=1)

    def test_validate_size_at_exact_limit(self):
        """Test size validation at exact limit."""
        # Exactly 1 MB
        audio_bytes = b"a" * (1024 * 1024)
        audio = RawAudio(bytes=audio_bytes, filename="test.wav")

        # Should not raise
        audio.validate_size(max_size_mb=1)

    def test_validate_size_invalid_max_size_raises_error(self):
        """Test that invalid max_size_mb raises ValueError."""
        audio = RawAudio(bytes=b"data", filename="test.wav")

        with pytest.raises(ValueError, match="max_size_mb must be a positive integer"):
            audio.validate_size(max_size_mb=0)

        with pytest.raises(ValueError, match="max_size_mb must be a positive integer"):
            audio.validate_size(max_size_mb=-1)

        with pytest.raises(ValueError, match="max_size_mb must be a positive integer"):
            audio.validate_size(max_size_mb="not an int")

    def test_get_size_bytes(self):
        """Test getting file size in bytes."""
        audio_bytes = b"a" * 1024
        audio = RawAudio(bytes=audio_bytes, filename="test.wav")

        assert audio.get_size_bytes() == 1024

    def test_get_size_mb(self):
        """Test getting file size in megabytes."""
        audio_bytes = b"a" * (2 * 1024 * 1024)
        audio = RawAudio(bytes=audio_bytes, filename="test.wav")

        assert audio.get_size_mb() == 2.0


class TestRawAudioFormatValidation:
    """Test RawAudio format validation methods."""

    def test_get_extension_wav(self):
        """Test extracting .wav extension."""
        audio = RawAudio(bytes=b"data", filename="test.wav")
        assert audio.get_extension() == "wav"

    def test_get_extension_mp3(self):
        """Test extracting .mp3 extension."""
        audio = RawAudio(bytes=b"data", filename="audio.mp3")
        assert audio.get_extension() == "mp3"

    def test_get_extension_uppercase(self):
        """Test that extension is returned in lowercase."""
        audio = RawAudio(bytes=b"data", filename="test.WAV")
        assert audio.get_extension() == "wav"

    def test_get_extension_no_extension(self):
        """Test file with no extension returns empty string."""
        audio = RawAudio(bytes=b"data", filename="noextension")
        assert audio.get_extension() == ""

    def test_get_extension_multiple_dots(self):
        """Test file with multiple dots returns last extension."""
        audio = RawAudio(bytes=b"data", filename="my.audio.file.wav")
        assert audio.get_extension() == "wav"

    def test_validate_format_allowed_format(self):
        """Test format validation passes for allowed format."""
        audio = RawAudio(bytes=b"data", filename="test.wav")

        # Should not raise
        audio.validate_format(allowed_formats=["wav", "mp3"])

    def test_validate_format_disallowed_format_raises_error(self):
        """Test format validation fails for disallowed format."""
        audio = RawAudio(bytes=b"data", filename="test.flac")

        with pytest.raises(InvalidAudioError, match="Audio format 'flac' not supported"):
            audio.validate_format(allowed_formats=["wav", "mp3"])

    def test_validate_format_no_extension_raises_error(self):
        """Test format validation fails for file with no extension."""
        audio = RawAudio(bytes=b"data", filename="noextension")

        with pytest.raises(InvalidAudioError, match="has no extension"):
            audio.validate_format(allowed_formats=["wav"])

    def test_validate_format_empty_allowed_formats_raises_error(self):
        """Test that empty allowed_formats raises ValueError."""
        audio = RawAudio(bytes=b"data", filename="test.wav")

        with pytest.raises(ValueError, match="allowed_formats cannot be empty"):
            audio.validate_format(allowed_formats=[])


class TestRawAudioStringRepresentation:
    """Test RawAudio string representation."""

    def test_str_representation(self):
        """Test string representation includes filename and size."""
        audio = RawAudio(bytes=b"a" * 1024, filename="test.wav")
        str_repr = str(audio)

        assert "test.wav" in str_repr
        assert "RawAudio" in str_repr
        assert "MB" in str_repr
