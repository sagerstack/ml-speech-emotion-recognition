"""Exception for SageMaker endpoint not found errors."""

from app.domain.model.exceptions.sagemaker_inference_error import SageMakerInferenceError


class SageMakerEndpointNotFoundError(SageMakerInferenceError):
    """SageMaker endpoint not found (404).

    Raised when the specified SageMaker endpoint does not exist or is not accessible.
    This is a permanent error - do NOT retry.

    AWS Error Codes that map to this exception:
    - ValidationError with "Could not find endpoint"
    - ResourceNotFoundException
    """

    def __init__(self, endpoint_name: str) -> None:
        """Initialize endpoint not found error.

        Args:
            endpoint_name: Name of the SageMaker endpoint that was not found
        """
        message = f"SageMaker endpoint '{endpoint_name}' not found or not accessible"
        super().__init__(message, endpoint_name)
