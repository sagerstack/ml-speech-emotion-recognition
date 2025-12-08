"""Exception for SageMaker authentication errors."""

from app.domain.model.exceptions.sagemaker_inference_error import SageMakerInferenceError


class SageMakerAuthenticationError(SageMakerInferenceError):
    """SageMaker authentication/authorization error (403).

    Raised when the IAM credentials used to invoke the SageMaker endpoint
    do not have sufficient permissions. This is a permanent error - do NOT retry.

    AWS Error Codes that map to this exception:
    - AccessDeniedException
    - UnauthorizedException
    - InvalidSignatureException
    - InvalidAccessKeyId
    - SignatureDoesNotMatch

    Required IAM permissions:
    - sagemaker:InvokeEndpoint
    """

    def __init__(self, endpoint_name: str, aws_error_code: str | None = None) -> None:
        """Initialize authentication error.

        Args:
            endpoint_name: Name of the SageMaker endpoint
            aws_error_code: AWS error code (if available)
        """
        message = "Insufficient permissions to invoke SageMaker endpoint"
        if aws_error_code:
            message += f" (AWS error: {aws_error_code})"
        super().__init__(message, endpoint_name)
        self.aws_error_code = aws_error_code
