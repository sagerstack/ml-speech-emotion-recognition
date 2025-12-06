"""Domain entities for model operations."""

from app.domain.model.entities.inference import Inference
from app.domain.model.entities.model_info import ModelInfo
from app.domain.model.entities.raw_audio import RawAudio

__all__ = [
    "RawAudio",
    "ModelInfo",
    "Inference",
]
