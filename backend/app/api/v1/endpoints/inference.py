"""
Inference API endpoints for ML Speech Emotion Recognition.

This module provides endpoints for real-time emotion prediction using
AWS SageMaker deployed models with proper error handling and monitoring.
"""

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
from prometheus_client import Counter

from app.services.audio_service import audio_processor, AudioProcessingError
from app.services.sagemaker_service import get_sagemaker_service, SageMakerServiceError, SageMakerConnectionError, SageMakerPredictionError
from app.utils.config import get_settings
from app.utils.logging import get_logger
from app.utils.file_validation import validate_audio_file

router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)

# Prometheus metrics for inference endpoint
INFERENCE_REQUESTS = Counter(
    'inference_requests_total',
    'Total inference requests',
    ['emotion', 'success']
)

INFERENCE_DURATION = Counter(
    'inference_duration_seconds',
    'Inference request duration',
    ['endpoint']
)

SAGEMAKER_INVOCATIONS = Counter(
    'sagemaker_invocations_total',
    'Total SageMaker endpoint invocations',
    ['endpoint', 'status']
)


@router.post("/infer")
async def infer_emotion(
    file: UploadFile = File(...),
    user_id: str = None
) -> Dict[str, Any]:
    """
    Infer emotion from audio using SageMaker deployed model.

    This endpoint processes uploaded audio files and returns emotion predictions
    from the production SageMaker model endpoint.

    Args:
        file: Audio file to process (WAV, MP3, FLAC, M4A)
        user_id: Optional user ID for tracking and analytics

    Returns:
        Dictionary containing:
        - success: bool - Whether inference was successful
        - message: str - Status message
        - data: dict - Prediction results and metadata
        - request_id: str - Unique request identifier

    Raises:
        HTTPException: For various error conditions (400, 500, 503)
    """
    correlation_id = str(uuid.uuid4())
    inference_start_time = logger.info(
        "Inference request received",
        filename=file.filename,
        content_type=file.content_type,
        user_id=user_id,
        correlation_id=correlation_id
    )

    try:
        # Step 1: Read and validate file content
        file_content = await file.read()

        # Enhanced file validation with magic bytes
        max_size_mb = min(settings.max_upload_size_mb, 25)  # Use the smaller limit
        is_valid, error_message = validate_audio_file(
            file_content,
            file.content_type,
            max_size_mb
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File validation failed: {error_message}"
            )

        logger.info(
            "File validation completed",
            filename=file.filename,
            file_size_bytes=len(file_content),
            correlation_id=correlation_id
        )

        # Step 2: Convert audio to base64 for SageMaker
        try:
            audio_base64, sample_rate = audio_processor.audio_to_base64(
                file_content, file.filename
            )

            logger.info(
                "Audio conversion to base64 completed",
                filename=file.filename,
                sample_rate=sample_rate,
                base64_length=len(audio_base64),
                correlation_id=correlation_id
            )

        except AudioProcessingError as e:
            logger.error(
                "Audio processing failed during base64 conversion",
                filename=file.filename,
                error=str(e),
                correlation_id=correlation_id
            )
            INFERENCE_REQUESTS.labels(emotion='unknown', success='false').inc()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Audio processing failed: {str(e)}"
            )

        # Step 3: Get SageMaker prediction
        try:
            sagemaker_service = get_sagemaker_service()
            prediction_result = await sagemaker_service.predict_emotion(
                audio_base64=audio_base64,
                sample_rate=sample_rate
            )

            SAGEMAKER_INVOCATIONS.labels(
                endpoint=settings.sagemaker_endpoint_name,
                status='success'
            ).inc()

            logger.info(
                "SageMaker prediction completed",
                filename=file.filename,
                predicted_emotion=prediction_result.get('predicted_emotion'),
                confidence=prediction_result.get('confidence'),
                invocation_time=prediction_result.get('invocation_time'),
                correlation_id=correlation_id
            )

        except SageMakerConnectionError as e:
            logger.error(
                "SageMaker connection error",
                filename=file.filename,
                error=str(e),
                correlation_id=correlation_id
            )
            SAGEMAKER_INVOCATIONS.labels(
                endpoint=settings.sagemaker_endpoint_name,
                status='connection_error'
            ).inc()
            INFERENCE_REQUESTS.labels(emotion='unknown', success='false').inc()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SageMaker endpoint is currently unavailable"
            )

        except SageMakerPredictionError as e:
            logger.error(
                "SageMaker prediction error",
                filename=file.filename,
                error=str(e),
                correlation_id=correlation_id
            )
            SAGEMAKER_INVOCATIONS.labels(
                endpoint=settings.sagemaker_endpoint_name,
                status='prediction_error'
            ).inc()
            INFERENCE_REQUESTS.labels(emotion='unknown', success='false').inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Prediction service error: {str(e)}"
            )

        except SageMakerServiceError as e:
            logger.error(
                "SageMaker service error",
                filename=file.filename,
                error=str(e),
                correlation_id=correlation_id
            )
            SAGEMAKER_INVOCATIONS.labels(
                endpoint=settings.sagemaker_endpoint_name,
                status='service_error'
            ).inc()
            INFERENCE_REQUESTS.labels(emotion='unknown', success='false').inc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"SageMaker service error: {str(e)}"
            )

        # Step 4: Prepare response
        predicted_emotion = prediction_result.get('predicted_emotion', 'unknown')
        confidence = prediction_result.get('confidence', 0.0)

        # Update metrics
        INFERENCE_REQUESTS.labels(emotion=predicted_emotion, success='true').inc()
        INFERENCE_DURATION.labels(endpoint=settings.sagemaker_endpoint_name).inc(
            prediction_result.get('invocation_time', 0)
        )

        # Prepare comprehensive response
        response_data = {
            "success": True,
            "message": "Emotion inference completed successfully",
            "data": {
                "predictions": {
                    "primary_emotion": predicted_emotion,
                    "confidence": confidence,
                    "all_emotions": prediction_result.get('all_emotions', {})
                },
                "audio_metadata": {
                    "filename": file.filename,
                    "sample_rate": sample_rate,
                    "file_size_bytes": len(file_content)
                },
                "inference_metadata": {
                    "sagemaker_endpoint": settings.sagemaker_endpoint_name,
                    "aws_region": settings.aws_region,
                    "invocation_time_seconds": prediction_result.get('invocation_time', 0),
                    "response_size_bytes": prediction_result.get('response_size', 0),
                    "model_version": prediction_result.get('model_version', 'unknown')
                },
                "processing_info": {
                    "correlation_id": correlation_id,
                    "user_id": user_id,
                    "processed_at": "2024-01-01T12:00:00Z"
                }
            },
            "request_id": correlation_id
        }

        logger.info(
            "Inference request completed successfully",
            filename=file.filename,
            predicted_emotion=predicted_emotion,
            confidence=confidence,
            total_time=prediction_result.get('invocation_time', 0),
            correlation_id=correlation_id
        )

        return response_data

    except HTTPException:
        # Re-raise HTTPException without catching it
        raise

    except Exception as e:
        logger.error(
            "Unexpected error during inference",
            filename=file.filename,
            error=str(e),
            correlation_id=correlation_id
        )
        INFERENCE_REQUESTS.labels(emotion='unknown', success='false').inc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during inference"
        )


@router.get("/health")
async def inference_health_check() -> Dict[str, Any]:
    """
    Health check for inference service including SageMaker endpoint status.

    Returns:
        Health status of the inference service and SageMaker endpoint
    """
    try:
        sagemaker_service = get_sagemaker_service()
        sagemaker_health = await sagemaker_service.health_check()

        overall_status = "healthy" if sagemaker_health.get("accessible", False) else "unhealthy"

        return {
            "status": overall_status,
            "service": "emotion-inference",
            "version": "1.0.0",
            "sagemaker": sagemaker_health,
            "supported_formats": settings.supported_formats,
            "max_file_size_mb": settings.max_upload_size_mb,
            "max_duration_seconds": settings.max_audio_duration_seconds
        }

    except Exception as e:
        logger.error("Inference health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "service": "emotion-inference",
            "error": str(e)
        }


@router.get("/config")
async def get_inference_config() -> Dict[str, Any]:
    """
    Get inference service configuration.

    Returns:
        Current configuration settings for the inference service
    """
    return {
        "sagemaker": {
            "endpoint_name": settings.sagemaker_endpoint_name,
            "aws_region": settings.aws_region
        },
        "audio": {
            "supported_formats": settings.supported_formats,
            "max_file_size_mb": settings.max_upload_size_mb,
            "max_duration_seconds": settings.max_audio_duration_seconds
        },
        "performance": {
            "max_concurrent_requests": settings.max_concurrent_requests,
            "request_timeout_seconds": settings.request_timeout_seconds
        }
    }