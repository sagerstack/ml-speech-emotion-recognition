"""Exception for SageMaker throttling errors."""

from app.domain.model.exceptions.sagemaker_inference_error import SageMakerInferenceError


class SageMakerThrottlingError(SageMakerInferenceError):
    """SageMaker rate limit/throttling error (429).

    Raised when too many requests are sent to a SageMaker endpoint
    and AWS throttles the requests. This is a transient error - retry
    with exponential backoff.

    AWS Error Codes that map to this exception:
    - ThrottlingException
    - TooManyRequestsException
    - ServiceUnavailable (503) with throttling
    """

    def __init__(self, endpoint_name: str, retry_after_seconds: int | None = None) -> None:
        """Initialize throttling error.

        Args:
            endpoint_name: Name of the SageMaker endpoint
            retry_after_seconds: Suggested time to wait before retrying (if available)
        """
        message = "SageMaker endpoint is throttling requests (rate limit exceeded)"
        if retry_after_seconds:
            message += f". Retry after {retry_after_seconds} seconds"
        super().__init__(message, endpoint_name)
        self.retry_after_seconds = retry_after_seconds
