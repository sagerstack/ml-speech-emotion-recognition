"""Prediction entity for monitoring."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Prediction(BaseModel):
    """Prediction entity representing a model inference result."""

    prediction_id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    predicted_emotion: str
    confidence: float = Field(ge=0.0, le=1.0)
    features: dict[str, Any]
    actual_emotion: str | None = None

    class Config:
        frozen = False
