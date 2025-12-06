"""
Inference API endpoints (v2 - Clean Architecture).

This module provides inference endpoints using clean architecture:
- Use cases handle business logic
- Dependency injection wires dependencies
- API layer converts between HTTP and domain models
- No direct access to infrastructure (model loading, feature extraction)

Endpoints:
- GET /v2/inference/versions - List all available model versions
- GET /v2/inference/{version}/info - Get info for specific model version
- GET /v2/inference/info - Get info for latest model version
- POST /v2/inference - Inference using latest model
- POST /v2/inference/latest - Inference using latest model (deprecated, use /v2/inference)
"""

import time
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from prometheus_client import Counter, Histogram

from app.domain.model.exceptions.invalid_audio_error import InvalidAudioError
from app.domain.model.exceptions.model_not_found_error import ModelNotFoundError
from app.domain.model.exceptions.prediction_failed_error import PredictionFailedError
from app.infrastructure.config.feature_flags import FeatureFlags, get_feature_flags
from app.infrastructure.di.providers import (
    get_model_info_use_case,
    get_model_versions_use_case,
    get_run_inference_use_case,
)
from app.use_cases.model.get_model_info import GetModelInfoUseCase
from app.use_cases.model.get_model_versions import GetModelVersionsUseCase
from app.use_cases.model.run_inference import RunInferenceUseCase
from app.utils.file_validation import validate_audio_file
from app.infrastructure.observability.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Prometheus metrics for v2 inference
INFERENCE_REQUESTS_V2 = Counter(
    "inference_requests_v2_total",
    "Total v2 inference requests",
    ["version", "success", "api_version"],
)

INFERENCE_DURATION_V2 = Histogram(
    "inference_duration_v2_seconds", "v2 inference request duration", ["version", "api_version"]
)

# Prometheus metrics for v2 model info endpoints
MODEL_INFO_REQUESTS_V2 = Counter(
    "model_info_requests_v2_total",
    "Total v2 model info requests",
    ["endpoint", "success"],
)

MODEL_VERSIONS_REQUESTS_V2 = Counter(
    "model_versions_requests_v2_total",
    "Total v2 model versions requests",
    ["success"],
)


@router.get("/versions")
async def get_model_versions(
    get_versions_use_case: GetModelVersionsUseCase = Depends(get_model_versions_use_case),
) -> dict[str, Any]:
    """
    Get all available model versions (v2 API - Clean Architecture).

    This endpoint demonstrates clean architecture principles:
    1. Uses dependency injection for use cases
    2. Delegates business logic to use cases
    3. Converts between domain entities and API models

    Args:
        get_versions_use_case: Injected use case (via DI)

    Returns:
        {
            "versions": ["v4", "v3", "v2", "v1"],
            "latest": "v4",
            "count": 4
        }

    Raises:
        HTTPException: 500 for unexpected errors
    """
    try:
        logger.info("v2 get model versions request received")

        # Execute use case (business logic)
        result = get_versions_use_case.execute()

        # Record success metrics
        MODEL_VERSIONS_REQUESTS_V2.labels(success=True).inc()

        logger.info(
            "v2 get model versions completed successfully",
            count=result["count"],
            latest=result["latest"],
        )

        return result

    except Exception as e:
        # Catch-all for unexpected errors
        MODEL_VERSIONS_REQUESTS_V2.labels(success=False).inc()
        logger.error("Unexpected error getting model versions", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/{version}/info")
async def get_model_info_by_version(
    version: str,
    get_info_use_case: GetModelInfoUseCase = Depends(get_model_info_use_case),
) -> dict[str, Any]:
    """
    Get information for a specific model version (v2 API - Clean Architecture).

    This endpoint demonstrates clean architecture principles:
    1. Uses dependency injection for use cases
    2. Delegates business logic to use cases
    3. Converts between domain entities and API models

    Args:
        version: Model version (e.g., "v4", "4")
        get_info_use_case: Injected use case (via DI)

    Returns:
        {
            "version": "v4",
            "model_type": "UltraEnsembleModel",
            "feature_dimension": 210,
            "available": true
        }

    Raises:
        HTTPException: 404 if model not found, 500 for unexpected errors
    """
    try:
        logger.info("v2 get model info request received", version=version)

        # Execute use case (business logic)
        model_info = get_info_use_case.execute(version)

        if model_info is None:
            MODEL_INFO_REQUESTS_V2.labels(endpoint="version_info", success=False).inc()
            logger.warning("Model not found", version=version)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model version {version} not found",
            )

        # Record success metrics
        MODEL_INFO_REQUESTS_V2.labels(endpoint="version_info", success=True).inc()

        # Convert domain entity to API response
        response = {
            "version": str(model_info.version),
            "model_type": model_info.model_type,
            "feature_dimension": model_info.feature_dimension,
            "available": True,
        }

        # Add optional metadata fields if available
        if model_info.model_name is not None:
            response["model_name"] = model_info.model_name
        if model_info.sklearn_version is not None:
            response["sklearn_version"] = model_info.sklearn_version
        if model_info.created_date is not None:
            response["created_date"] = model_info.created_date
        if model_info.dataset is not None:
            response["dataset"] = model_info.dataset
        if model_info.classes is not None:
            response["classes"] = model_info.classes
        if model_info.num_classes is not None:
            response["num_classes"] = model_info.num_classes
        if model_info.training_samples is not None:
            response["training_samples"] = model_info.training_samples
        if model_info.validation_dataset is not None:
            response["validation_dataset"] = model_info.validation_dataset
        if model_info.feature_extraction is not None:
            response["feature_extraction"] = model_info.feature_extraction
        if model_info.notes is not None:
            response["notes"] = model_info.notes

        logger.info(
            "v2 get model info completed successfully",
            version=str(model_info.version),
            model_type=model_info.model_type,
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        # Catch-all for unexpected errors
        MODEL_INFO_REQUESTS_V2.labels(endpoint="version_info", success=False).inc()
        logger.error("Unexpected error getting model info", error=str(e), version=version)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/info")
async def get_latest_model_info(
    get_info_use_case: GetModelInfoUseCase = Depends(get_model_info_use_case),
) -> dict[str, Any]:
    """
    Get information for the latest model version (v2 API - Clean Architecture).

    This endpoint demonstrates clean architecture principles:
    1. Uses dependency injection for use cases
    2. Delegates business logic to use cases
    3. Converts between domain entities and API models

    Args:
        get_info_use_case: Injected use case (via DI)

    Returns:
        {
            "version": "v4",
            "model_type": "UltraEnsembleModel",
            "feature_dimension": 210,
            "available": true,
            "is_latest": true
        }

    Raises:
        HTTPException: 404 if no models found, 500 for unexpected errors
    """
    try:
        logger.info("v2 get latest model info request received")

        # Execute use case for latest version (v4)
        model_info = get_info_use_case.execute("v4")

        if model_info is None:
            MODEL_INFO_REQUESTS_V2.labels(endpoint="latest_info", success=False).inc()
            logger.warning("Latest model not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Latest model not found",
            )

        # Record success metrics
        MODEL_INFO_REQUESTS_V2.labels(endpoint="latest_info", success=True).inc()

        # Convert domain entity to API response (with is_latest flag)
        response = {
            "version": str(model_info.version),
            "model_type": model_info.model_type,
            "feature_dimension": model_info.feature_dimension,
            "available": True,
            "is_latest": True,
        }

        # Add optional metadata fields if available
        if model_info.model_name is not None:
            response["model_name"] = model_info.model_name
        if model_info.sklearn_version is not None:
            response["sklearn_version"] = model_info.sklearn_version
        if model_info.created_date is not None:
            response["created_date"] = model_info.created_date
        if model_info.dataset is not None:
            response["dataset"] = model_info.dataset
        if model_info.classes is not None:
            response["classes"] = model_info.classes
        if model_info.num_classes is not None:
            response["num_classes"] = model_info.num_classes
        if model_info.training_samples is not None:
            response["training_samples"] = model_info.training_samples
        if model_info.validation_dataset is not None:
            response["validation_dataset"] = model_info.validation_dataset
        if model_info.feature_extraction is not None:
            response["feature_extraction"] = model_info.feature_extraction
        if model_info.notes is not None:
            response["notes"] = model_info.notes

        logger.info(
            "v2 get latest model info completed successfully",
            version=str(model_info.version),
            model_type=model_info.model_type,
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        # Catch-all for unexpected errors
        MODEL_INFO_REQUESTS_V2.labels(endpoint="latest_info", success=False).inc()
        logger.error("Unexpected error getting latest model info", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post("/")
async def infer_latest(
    file: UploadFile = File(...),
    audio_features: bool = Query(
        default=False,
        description="Include audio features data (mel spectrogram, chroma, MFCCs, pitch contour). Requires ENABLE_INFERENCE_AUDIO_FEATURES=true"
    ),
    run_inference_use_case: RunInferenceUseCase = Depends(get_run_inference_use_case),
    feature_flags: FeatureFlags = Depends(get_feature_flags),
) -> dict[str, Any]:
    """
    Infer emotion using the latest model version (v2 API - Clean Architecture).

    This endpoint demonstrates clean architecture principles:
    1. Uses dependency injection for use cases
    2. No direct access to models or feature extraction
    3. Converts between API models and domain entities
    4. Delegates business logic to use cases

    Monitoring is always enabled for v2 API, ensuring comprehensive data collection
    for drift detection and model performance tracking.

    Args:
        file: Audio file (WAV, MP3, M4A)
        audio_features: Include audio features data in response (requires feature flag)
        run_inference_use_case: Injected use case (via DI)
        feature_flags: Feature flags service (via DI)

    Returns:
        {
            "version": "v4",
            "prediction": {
                "emotion": "happy",
                "confidence": 0.92,
                "all_probabilities": {
                    "angry": 0.01,
                    "disgust": 0.02,
                    "fear": 0.03,
                    "happy": 0.92,
                    "neutral": 0.01,
                    "sad": 0.01
                },
                "prediction_id": "uuid-string"  # Always included
            },
            "processing_time_ms": 234,
            "audio_features": {  # Only if audio_features=true and feature enabled
                "mel_spectrogram": {...},
                "chroma": {...},
                "mfccs": {...},
                "pitch_contour": {...}
            }
        }

    Raises:
        HTTPException: 404 if no models found, 400 for invalid audio, 500 for errors
    """
    start_time = time.time()
    version_used = "unknown"

    # Check if audio_features should be included based on feature flag
    should_include_features = feature_flags.should_include_audio_features(requested=audio_features)

    # Monitoring is always enabled for v2 API
    monitoring_enabled = True

    logger.info(
        "v2 inference request received",
        filename=file.filename,
        content_type=file.content_type,
        audio_features=audio_features,
        feature_enabled=feature_flags.inference_audio_features_enabled,
    )

    try:
        # Read audio bytes
        audio_bytes = await file.read()

        # Validate file (API layer responsibility)
        is_valid, error_message = validate_audio_file(
            audio_bytes, file.content_type, max_size_mb=30
        )

        if not is_valid:
            logger.warning(
                "File validation failed",
                filename=file.filename,
                error=error_message
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File validation failed: {error_message}",
            )

        # Execute use case (business logic)
        # Use case handles: audio validation, feature extraction, model loading, prediction, monitoring
        inference = run_inference_use_case.execute(
            audio_bytes=audio_bytes,
            filename=file.filename or "unknown.wav",
            model_version="v4",  # Latest version
            audio_features=should_include_features,
            enable_monitoring=monitoring_enabled,
            api_version="v2",  # v2 API endpoint
        )

        # Track version for metrics
        version_used = str(inference.model_version)

        # Record success metrics
        INFERENCE_REQUESTS_V2.labels(version=version_used, success=True, api_version="v2").inc()
        INFERENCE_DURATION_V2.labels(version=version_used, api_version="v2").observe(time.time() - start_time)

        # Convert domain entity to API response
        response = {
            "version": str(inference.model_version),
            "prediction": {
                "emotion": inference.emotion.value,
                "confidence": inference.confidence.value,
                "all_probabilities": {
                    emotion.value: prob for emotion, prob in inference.all_probabilities.items()
                },
            },
            "processing_time_ms": round(inference.processing_time_ms, 2),
        }

        # Include prediction_id if monitoring is enabled
        if inference.prediction_id is not None:
            response["prediction"]["prediction_id"] = inference.prediction_id

        # Include audio_features data if present
        if hasattr(inference, "audio_features") and inference.audio_features is not None:
            response["audio_features"] = inference.audio_features

        logger.info(
            "v2 inference completed successfully",
            filename=file.filename,
            version=version_used,
            emotion=inference.emotion.value,
            confidence=round(inference.confidence.value, 4),
            processing_time_ms=round(inference.processing_time_ms, 2),
            monitoring_enabled=monitoring_enabled,
            prediction_id=inference.prediction_id,
        )

        return response

    except InvalidAudioError as e:
        # Domain exception for invalid audio
        INFERENCE_REQUESTS_V2.labels(version=version_used, success=False, api_version="v2").inc()
        logger.warning("Invalid audio", error=str(e), filename=file.filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid audio: {str(e)}"
        )

    except ModelNotFoundError as e:
        # Domain exception for missing model
        INFERENCE_REQUESTS_V2.labels(version=version_used, success=False, api_version="v2").inc()
        logger.error("Model not found", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Model not found: {str(e)}"
        )

    except PredictionFailedError as e:
        # Domain exception for prediction failure
        INFERENCE_REQUESTS_V2.labels(version=version_used, success=False, api_version="v2").inc()
        logger.error("Prediction failed", error=str(e), filename=file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Prediction failed: {str(e)}"
        )

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise

    except Exception as e:
        # Catch-all for unexpected errors
        INFERENCE_REQUESTS_V2.labels(version=version_used, success=False, api_version="v2").inc()
        logger.error("Unexpected error", error=str(e), filename=file.filename)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post("/latest")
async def infer_latest_deprecated(
    file: UploadFile = File(...),
    audio_features: bool = Query(
        default=False,
        description="Include audio features data (mel spectrogram, chroma, MFCCs, pitch contour). Requires ENABLE_INFERENCE_AUDIO_FEATURES=true"
    ),
    run_inference_use_case: RunInferenceUseCase = Depends(get_run_inference_use_case),
    feature_flags: FeatureFlags = Depends(get_feature_flags),
) -> dict[str, Any]:
    """
    Infer emotion using the latest model version (v2 API - DEPRECATED).

    DEPRECATED: This endpoint is deprecated. Use POST /v2/inference instead.
    This endpoint is maintained for backward compatibility only.

    Monitoring is always enabled for v2 API.

    Args:
        file: Audio file (WAV, MP3, M4A)
        audio_features: Include audio features data in response (requires feature flag)
        run_inference_use_case: Injected use case (via DI)
        feature_flags: Feature flags service (via DI)

    Returns:
        Same response format as POST /v2/inference

    Raises:
        HTTPException: 404 if no models found, 400 for invalid audio, 500 for errors
    """
    # Delegate to the main inference endpoint
    return await infer_latest(file, audio_features, run_inference_use_case, feature_flags)
