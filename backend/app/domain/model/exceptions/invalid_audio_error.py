"""Exception for invalid audio errors."""

from app.domain.model.exceptions.inference_error import InferenceError


class InvalidAudioError(InferenceError):
    """Exception raised when audio file is invalid or cannot be processed.

    This can occur due to:
    - File size exceeding maximum limit
    - Unsupported audio format
    - Corrupted audio data
    - Invalid audio parameters (sample rate, channels, etc.)
    """

    def __init__(self, message: str) -> None:
        """Initialize invalid audio error.

        Args:
            message: Detailed error message describing the validation failure
        """
        super().__init__(message)
