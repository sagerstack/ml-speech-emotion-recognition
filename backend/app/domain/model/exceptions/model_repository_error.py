"""Base exception for model repository operations."""


class ModelRepositoryError(Exception):
    """Base exception for all model repository errors.

    This is the base class for exceptions that occur when accessing
    or interacting with model repositories (local file system, SageMaker, etc.).
    """

    def __init__(self, message: str) -> None:
        """Initialize model repository error.

        Args:
            message: Error message describing what went wrong
        """
        self.message = message
        super().__init__(self.message)
