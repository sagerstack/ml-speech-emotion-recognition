"""Domain exceptions for model operations."""

from app.domain.model.exceptions.inference_error import InferenceError
from app.domain.model.exceptions.invalid_audio_error import InvalidAudioError
from app.domain.model.exceptions.model_not_found_error import ModelNotFoundError
from app.domain.model.exceptions.model_repository_error import ModelRepositoryError
from app.domain.model.exceptions.prediction_failed_error import PredictionFailedError
from app.domain.model.exceptions.sagemaker_authentication_error import (
    SageMakerAuthenticationError,
)
from app.domain.model.exceptions.sagemaker_endpoint_not_found_error import (
    SageMakerEndpointNotFoundError,
)
from app.domain.model.exceptions.sagemaker_inference_error import SageMakerInferenceError
from app.domain.model.exceptions.sagemaker_invalid_response_error import (
    SageMakerInvalidResponseError,
)
from app.domain.model.exceptions.sagemaker_throttling_error import (
    SageMakerThrottlingError,
)
from app.domain.model.exceptions.sagemaker_timeout_error import SageMakerTimeoutError

__all__ = [
    "InferenceError",
    "ModelNotFoundError",
    "InvalidAudioError",
    "PredictionFailedError",
    "ModelRepositoryError",
    "SageMakerInferenceError",
    "SageMakerEndpointNotFoundError",
    "SageMakerTimeoutError",
    "SageMakerThrottlingError",
    "SageMakerInvalidResponseError",
    "SageMakerAuthenticationError",
]
