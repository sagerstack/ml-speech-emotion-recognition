"""Exception for prediction failures."""

from app.domain.model.exceptions.inference_error import InferenceError


class PredictionFailedError(InferenceError):
    """Exception raised when model prediction fails.

    This occurs when the model cannot generate a valid prediction,
    which may be due to:
    - Feature extraction failure
    - Model execution error
    - Invalid model output
    - Numerical instability
    """

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        """Initialize prediction failed error.

        Args:
            message: Error message describing the prediction failure
            original_error: Optional original exception that caused the failure
        """
        self.original_error = original_error
        super().__init__(message)
