"""Domain exceptions for model operations."""

from app.domain.model.exceptions.inference_error import InferenceError
from app.domain.model.exceptions.invalid_audio_error import InvalidAudioError
from app.domain.model.exceptions.model_not_found_error import ModelNotFoundError
from app.domain.model.exceptions.prediction_failed_error import PredictionFailedError

__all__ = [
    "InferenceError",
    "ModelNotFoundError",
    "InvalidAudioError",
    "PredictionFailedError",
]
