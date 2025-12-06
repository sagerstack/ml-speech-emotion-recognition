"""Exception for model not found errors."""

from app.domain.model.exceptions.inference_error import InferenceError


class ModelNotFoundError(InferenceError):
    """Exception raised when a requested model version is not found.

    This typically occurs when trying to load a model version that
    doesn't exist or hasn't been deployed yet.
    """

    def __init__(self, model_version: str) -> None:
        """Initialize model not found error.

        Args:
            model_version: The model version that was not found
        """
        self.model_version = model_version
        message = f"Model version '{model_version}' not found"
        super().__init__(message)
