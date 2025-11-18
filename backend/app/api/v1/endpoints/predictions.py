"""
Prediction API endpoints for ML Speech Emotion Recognition.

This module provides endpoints for uploading audio files and getting
emotion predictions from the ML model.
"""

import io
import json
import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services.audio_service import audio_processor, AudioProcessingError
from app.utils.config import get_settings
from app.utils.logging import get_logger

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


@router.post("/predict")
async def predict_emotion(
    file: UploadFile = File(...),
    user_id: str = None
) -> Dict[str, Any]:
    """
    Upload audio file and get emotion prediction.

    Args:
        file: Audio file to process
        user_id: Optional user ID for tracking

    Returns:
        Dictionary containing prediction results

    Raises:
        HTTPException: If audio processing fails
    """
    correlation_id = str(uuid.uuid4())
    logger.info(
        "Prediction request received",
        filename=file.filename,
        content_type=file.content_type,
        user_id=user_id,
        correlation_id=correlation_id
    )

    try:
        # Read file content first
        file_content = await file.read()

        # Validate file size first (before any audio processing)
        # Check both settings limit and hardcoded audio service limit (25MB)
        max_size_mb = min(settings.max_upload_size_mb, 25)  # Use the smaller limit
        if len(file_content) > max_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum allowed size of {max_size_mb}MB"
            )

        # Validate file type
        if file.content_type not in ["audio/wav", "audio/mp3", "audio/flac", "audio/m4a"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file type: {file.content_type}"
            )

        # Process audio file (duration and other validation happens here)
        features = audio_processor.process_audio_file(file_content, file.filename)

        # Mock prediction (in real implementation, this would call SageMaker)
        prediction_result = _mock_emotion_prediction(features)

        logger.info(
            "Prediction completed successfully",
            filename=file.filename,
            correlation_id=correlation_id,
            prediction_count=len(prediction_result["predictions"])
        )

        return {
            "success": True,
            "message": "Emotion prediction completed",
            "data": {
                "predictions": prediction_result["predictions"],
                "audio_metadata": {
                    "duration": features.metadata.duration,
                    "sample_rate": features.metadata.sample_rate,
                    "channels": features.metadata.channels,
                    "format": features.metadata.format
                },
                "processing_info": {
                    "correlation_id": correlation_id,
                    "model_version": "v1.0.0",
                    "processed_at": "2024-01-01T12:00:00Z"
                }
            },
            "request_id": correlation_id
        }

    except HTTPException:
        # Re-raise HTTPException without catching it
        raise

    except AudioProcessingError as e:
        logger.error(
            "Audio processing failed",
            filename=file.filename,
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio processing failed: {str(e)}"
        )

    except Exception as e:
        logger.error(
            "Unexpected error during prediction",
            filename=file.filename,
            error=str(e),
            correlation_id=correlation_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during prediction"
        )


@router.get("/health")
async def prediction_health_check() -> Dict[str, Any]:
    """Health check for prediction service."""
    return {
        "status": "healthy",
        "service": "emotion-prediction",
        "model_status": "available",
        "supported_formats": settings.supported_formats
    }


@router.get("/formats")
async def get_supported_formats() -> Dict[str, Any]:
    """Get list of supported audio formats."""
    return {
        "supported_formats": settings.supported_formats,
        "max_file_size_mb": settings.max_upload_size_mb,
        "max_duration_seconds": settings.max_audio_duration_seconds
    }


def _mock_emotion_prediction(features) -> Dict[str, Any]:
    """
    Mock emotion prediction for testing.

    In production, this would call AWS SageMaker endpoint.
    """
    import numpy as np

    # Generate mock predictions based on audio features
    emotions = ["happy", "sad", "angry", "fear", "disgust", "neutral", "surprise"]

    # Use audio feature statistics to generate consistent predictions
    mfcc_mean = np.mean(features.mfcc)
    chroma_mean = np.mean(features.chroma)

    # Generate pseudo-random but consistent confidence scores
    base_confidences = np.random.dirichlet(np.ones(len(emotions)))

    # Adjust based on audio characteristics
    if mfcc_mean > 0:
        base_confidences[0] += 0.1  # Increase happy confidence
    if chroma_mean < 0:
        base_confidences[1] += 0.1  # Increase sad confidence

    # Normalize
    base_confidences = base_confidences / np.sum(base_confidences)

    predictions = [
        {"label": emotion, "confidence": float(conf)}
        for emotion, conf in zip(emotions, base_confidences)
    ]

    # Sort by confidence
    predictions.sort(key=lambda x: x["confidence"], reverse=True)

    return {
        "predictions": predictions,
        "model_version": "v1.0.0",
        "confidence_threshold": 0.1
    }