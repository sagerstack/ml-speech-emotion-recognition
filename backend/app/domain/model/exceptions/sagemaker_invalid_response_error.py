"""Exception for SageMaker invalid response errors."""

from app.domain.model.exceptions.sagemaker_inference_error import SageMakerInferenceError


class SageMakerInvalidResponseError(SageMakerInferenceError):
    """SageMaker returned malformed/invalid response.

    Raised when the SageMaker endpoint returns a response that cannot be parsed
    or does not match the expected format. This may indicate:
    - Model container is returning wrong format
    - Response parsing error
    - Model is not properly deployed

    This is typically a permanent error (model/container issue), not transient.
    """

    def __init__(self, endpoint_name: str, reason: str) -> None:
        """Initialize invalid response error.

        Args:
            endpoint_name: Name of the SageMaker endpoint
            reason: Description of why the response is invalid
        """
        message = f"Invalid response from SageMaker endpoint: {reason}"
        super().__init__(message, endpoint_name)
        self.reason = reason
