"""Exception for SageMaker timeout errors."""

from app.domain.model.exceptions.sagemaker_inference_error import SageMakerInferenceError


class SageMakerTimeoutError(SageMakerInferenceError):
    """SageMaker inference timeout error.

    Raised when a SageMaker endpoint invocation exceeds the configured timeout.
    This may be transient (network issues) or indicate endpoint performance problems.

    AWS Error Codes that map to this exception:
    - ReadTimeoutError
    - ConnectTimeoutError
    - EndpointConnectionError (connection timeout)
    """

    def __init__(self, endpoint_name: str, timeout_seconds: int) -> None:
        """Initialize timeout error.

        Args:
            endpoint_name: Name of the SageMaker endpoint
            timeout_seconds: Timeout value that was exceeded
        """
        message = f"SageMaker inference timed out after {timeout_seconds} seconds"
        super().__init__(message, endpoint_name)
        self.timeout_seconds = timeout_seconds
