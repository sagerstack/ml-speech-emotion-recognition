"""Base exception for SageMaker inference operations."""

from app.domain.model.exceptions.model_repository_error import ModelRepositoryError


class SageMakerInferenceError(ModelRepositoryError):
    """Base exception for all SageMaker inference errors.

    This is the base class for all SageMaker-specific errors that occur
    during model inference operations when using AWS SageMaker endpoints.

    Hierarchy:
        Exception -> ModelRepositoryError -> SageMakerInferenceError
            -> SageMakerEndpointNotFoundError
            -> SageMakerTimeoutError
            -> SageMakerThrottlingError
            -> SageMakerInvalidResponseError
            -> SageMakerAuthenticationError
    """

    def __init__(self, message: str, endpoint_name: str | None = None) -> None:
        """Initialize SageMaker inference error.

        Args:
            message: Error message describing what went wrong
            endpoint_name: SageMaker endpoint name (optional)
        """
        self.endpoint_name = endpoint_name
        if endpoint_name:
            message = f"[Endpoint: {endpoint_name}] {message}"
        super().__init__(message)
