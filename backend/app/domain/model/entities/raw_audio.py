"""Raw audio entity."""

from dataclasses import dataclass

from app.domain.model.exceptions.invalid_audio_error import InvalidAudioError


@dataclass
class RawAudio:
    """Raw audio file with validation.

    Represents the raw bytes of an audio file along with metadata.
    This entity enforces business rules around audio file size and format.

    Attributes:
        bytes: Raw audio file bytes
        filename: Original filename of the audio file
    """

    bytes: bytes
    filename: str

    def __post_init__(self) -> None:
        """Validate raw audio data."""
        if not isinstance(self.bytes, bytes):
            raise InvalidAudioError(f"Audio data must be bytes, got {type(self.bytes)}")

        if not self.bytes:
            raise InvalidAudioError("Audio data cannot be empty")

        if not isinstance(self.filename, str):
            raise InvalidAudioError(f"Filename must be a string, got {type(self.filename)}")

        if not self.filename:
            raise InvalidAudioError("Filename cannot be empty")

    @classmethod
    def from_bytes(cls, audio_bytes: bytes, filename: str) -> "RawAudio":
        """Create RawAudio from bytes.

        Factory method for creating a RawAudio instance from raw bytes.

        Args:
            audio_bytes: Raw audio file bytes
            filename: Original filename

        Returns:
            RawAudio instance

        Raises:
            InvalidAudioError: If audio data or filename is invalid
        """
        return cls(bytes=audio_bytes, filename=filename)

    def validate_size(self, max_size_mb: int) -> None:
        """Validate audio file size.

        Business rule: Audio files must not exceed a maximum size
        to prevent memory issues and ensure reasonable processing time.

        Args:
            max_size_mb: Maximum allowed file size in megabytes

        Raises:
            InvalidAudioError: If file size exceeds maximum
        """
        if not isinstance(max_size_mb, int) or max_size_mb <= 0:
            raise ValueError(f"max_size_mb must be a positive integer, got {max_size_mb}")

        size_mb = len(self.bytes) / (1024 * 1024)
        if size_mb > max_size_mb:
            raise InvalidAudioError(
                f"Audio file too large: {size_mb:.2f}MB exceeds maximum of {max_size_mb}MB"
            )

    def get_size_bytes(self) -> int:
        """Get audio file size in bytes.

        Returns:
            File size in bytes
        """
        return len(self.bytes)

    def get_size_mb(self) -> float:
        """Get audio file size in megabytes.

        Returns:
            File size in megabytes
        """
        return len(self.bytes) / (1024 * 1024)

    def get_extension(self) -> str:
        """Extract file extension from filename.

        Returns:
            File extension (e.g., 'wav', 'mp3') or empty string if no extension
        """
        if "." in self.filename:
            return self.filename.rsplit(".", 1)[1].lower()
        return ""

    def validate_format(self, allowed_formats: list[str]) -> None:
        """Validate audio file format.

        Business rule: Only specific audio formats are supported
        for emotion recognition.

        Args:
            allowed_formats: List of allowed file extensions (e.g., ['wav', 'mp3'])

        Raises:
            InvalidAudioError: If file format is not allowed
        """
        if not allowed_formats:
            raise ValueError("allowed_formats cannot be empty")

        extension = self.get_extension()
        if not extension:
            raise InvalidAudioError(f"Audio file '{self.filename}' has no extension")

        if extension not in allowed_formats:
            raise InvalidAudioError(
                f"Audio format '{extension}' not supported. " f"Allowed formats: {allowed_formats}"
            )

    def __str__(self) -> str:
        """String representation."""
        return f"RawAudio(filename='{self.filename}', size={self.get_size_mb():.2f}MB)"
