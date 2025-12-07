"""Base exception for inference operations."""


class InferenceError(Exception):
    """Base exception for all inference-related errors.

    This is the root exception for all domain-specific errors
    that occur during model inference operations.
    """

    def __init__(self, message: str) -> None:
        """Initialize inference error.

        Args:
            message: Error message describing what went wrong
        """
        self.message = message
        super().__init__(self.message)
