"""
Local Model Inference API endpoints for ML Speech Emotion Recognition.

This module provides endpoints for real-time emotion prediction using
locally deployed versioned ML models with proper error handling and monitoring.

Endpoints:
- POST /v1/infer/local/latest - Inference using latest model
- POST /v1/infer/local/{version} - Inference using specific version
- POST /v1/infer/local/all - Inference using ALL versions (comparison)
- GET /v1/models/local/list - List all available model versions
- GET /v1/models/local/{version}/info - Get model version info
- GET /v1/models/local/latest - Get latest model info
"""

import time
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, File, Path as PathParam, UploadFile, HTTPException, status
from prometheus_client import Counter, Histogram

from app.services.model_registry import get_registry, ModelRegistry
from app.services.audio_service import audio_processor, AudioProcessingError
from app.services.evidently_monitoring import get_monitoring_service
from app.services.prediction_buffer import PredictionRecord
from app.utils.logging import get_logger
from app.utils.file_validation import validate_audio_file

router = APIRouter()
logger = get_logger(__name__)

# Prometheus metrics for local inference
LOCAL_INFERENCE_REQUESTS = Counter(
    'local_inference_requests_total',
    'Total local model inference requests',
    ['version', 'success']
)

LOCAL_INFERENCE_DURATION = Histogram(
    'local_inference_duration_seconds',
    'Local model inference request duration',
    ['version']
)

COMPARISON_REQUESTS = Counter(
    'comparison_requests_total',
    'Total comparison requests across all models',
    ['success']
)


@router.post("/infer/local/latest")
async def infer_latest(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    """
    Infer emotion using the latest model version.

    Args:
        file: Audio file (WAV, MP3, M4A)

    Returns:
        {
            "version": "2",
            "prediction": {
                "emotion": "happy",
                "confidence": 0.92,
                "all_probabilities": {"happy": 0.92, "neutral": 0.05, ...}
            },
            "model_info": {
                "type": "SVM Pipeline",
                "features_used": 78
            },
            "processing_time_ms": 234
        }

    Raises:
        HTTPException: 404 if no models registered, 400 for invalid audio, 500 for processing errors
    """
    start_time = time.time()

    try:
        # Read audio bytes first
        audio_bytes = await file.read()

        # Validate file
        is_valid, error_message = validate_audio_file(
            audio_bytes,
            file.content_type,
            max_size_mb=30
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File validation failed: {error_message}"
            )

        # Get model registry
        registry = get_registry()
        latest_model = registry.get_latest()

        if latest_model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No models registered. Please add models to the models directory."
            )

        # Run inference
        result = registry.predict(
            version=latest_model.version,
            audio_bytes=audio_bytes,
            filename=file.filename,
            include_features=True,
        )

        processing_time = (time.time() - start_time) * 1000  # Convert to ms

        # Record metrics
        LOCAL_INFERENCE_REQUESTS.labels(
            version=latest_model.version,
            success=True
        ).inc()
        LOCAL_INFERENCE_DURATION.labels(version=latest_model.version).observe(time.time() - start_time)

        prediction_id = _log_prediction_for_monitoring(
            result=result,
            filename=file.filename,
            background_tasks=background_tasks,
        )

        return {
            "version": result["model_version"],
            "prediction": {
                "emotion": result["emotion"],
                "confidence": result["confidence"],
                "all_probabilities": result["all_probabilities"],
                "prediction_id": prediction_id  # For user feedback submission
            },
            "model_info": {
                "type": result["model_type"],
                "features_used": result["feature_dimension"]
            },
            "processing_time_ms": round(processing_time, 2)
        }

    except HTTPException:
        raise
    except AudioProcessingError as e:
        LOCAL_INFERENCE_REQUESTS.labels(version="latest", success=False).inc()
        logger.error(f"Audio processing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio processing failed: {str(e)}"
        )
    except ValueError as e:
        LOCAL_INFERENCE_REQUESTS.labels(version="latest", success=False).inc()
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )
    except Exception as e:
        LOCAL_INFERENCE_REQUESTS.labels(version="latest", success=False).inc()
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/infer/local/{version}")
async def infer_version(
    background_tasks: BackgroundTasks,
    version: str = PathParam(..., description="Model version number (e.g., 1, 2, 3)"),
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    """
    Infer emotion using a specific model version.

    Args:
        version: Model version number
        file: Audio file (WAV, MP3, M4A)

    Returns:
        Same format as /infer/local/latest

    Raises:
        HTTPException: 404 if version not found, 400 for invalid audio, 500 for processing errors
    """
    start_time = time.time()

    try:
        # Read audio bytes first
        audio_bytes = await file.read()

        # Validate file
        is_valid, error_message = validate_audio_file(
            audio_bytes,
            file.content_type,
            max_size_mb=30
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File validation failed: {error_message}"
            )

        # Get model registry
        registry = get_registry()
        model_version = registry.get_version(version)

        if model_version is None:
            available_versions = registry.list_versions()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model version {version} not found. Available versions: {available_versions}"
            )

        # Run inference
        result = registry.predict(
            version=version,
            audio_bytes=audio_bytes,
            filename=file.filename,
            include_features=True,
        )

        processing_time = (time.time() - start_time) * 1000

        # Record metrics
        LOCAL_INFERENCE_REQUESTS.labels(version=version, success=True).inc()
        LOCAL_INFERENCE_DURATION.labels(version=version).observe(time.time() - start_time)

        _log_prediction_for_monitoring(
            result=result,
            filename=file.filename,
            background_tasks=background_tasks,
        )

        return {
            "version": result["model_version"],
            "prediction": {
                "emotion": result["emotion"],
                "confidence": result["confidence"],
                "all_probabilities": result["all_probabilities"]
            },
            "model_info": {
                "type": result["model_type"],
                "features_used": result["feature_dimension"]
            },
            "processing_time_ms": round(processing_time, 2)
        }

    except HTTPException:
        raise
    except AudioProcessingError as e:
        LOCAL_INFERENCE_REQUESTS.labels(version=version, success=False).inc()
        logger.error(f"Audio processing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio processing failed: {str(e)}"
        )
    except ValueError as e:
        LOCAL_INFERENCE_REQUESTS.labels(version=version, success=False).inc()
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )
    except Exception as e:
        LOCAL_INFERENCE_REQUESTS.labels(version=version, success=False).inc()
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/infer/local/all")
async def infer_all(
    file: UploadFile = File(...),
) -> Dict[str, Any]:
    """
    Infer emotion using ALL registered model versions for comparison.

    This endpoint runs the same audio file through all available model versions
    and returns a side-by-side comparison of predictions.

    Args:
        file: Audio file (WAV, MP3, M4A)

    Returns:
        {
            "audio_info": {
                "filename": "speech.wav",
                "size_bytes": 156789
            },
            "comparisons": [
                {
                    "version": "1",
                    "prediction": "happy",
                    "confidence": 0.85,
                    "model_type": "DecisionTreeClassifier",
                    "processing_time_ms": 123
                },
                {
                    "version": "2",
                    "prediction": "happy",
                    "confidence": 0.92,
                    "model_type": "SVM Pipeline",
                    "processing_time_ms": 145
                }
            ],
            "consensus": {
                "agreement": true,
                "majority_prediction": "happy",
                "agreement_percentage": 100,
                "total_models": 2
            },
            "total_processing_time_ms": 268
        }

    Raises:
        HTTPException: 404 if no models registered, 400 for invalid audio, 500 for processing errors
    """
    start_time = time.time()

    try:
        # Read audio bytes first
        audio_bytes = await file.read()
        file_size = len(audio_bytes)

        # Validate file
        is_valid, error_message = validate_audio_file(
            audio_bytes,
            file.content_type,
            max_size_mb=30
        )

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File validation failed: {error_message}"
            )

        # Get model registry
        registry = get_registry()
        available_versions = registry.list_versions()

        if not available_versions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No models registered. Please add models to the models directory."
            )

        # Run inference on all models
        comparisons = []
        predictions = []

        for version in available_versions:
            version_start_time = time.time()

            try:
                result = registry.predict(
                    version=version,
                    audio_bytes=audio_bytes,
                    filename=file.filename
                )

                version_processing_time = (time.time() - version_start_time) * 1000

                comparisons.append({
                    "version": version,
                    "prediction": result["emotion"],
                    "confidence": result["confidence"],
                    "model_type": result["model_type"],
                    "all_probabilities": result["all_probabilities"],
                    "processing_time_ms": round(version_processing_time, 2),
                    "success": True
                })

                predictions.append(result["emotion"])

            except Exception as e:
                logger.error(f"Error with model version {version}: {str(e)}")
                comparisons.append({
                    "version": version,
                    "error": str(e),
                    "success": False
                })

        # Calculate consensus
        successful_predictions = [p for p in predictions if p]

        if successful_predictions:
            # Find majority prediction
            from collections import Counter
            prediction_counts = Counter(successful_predictions)
            majority_prediction = prediction_counts.most_common(1)[0][0]
            majority_count = prediction_counts[majority_prediction]

            agreement = len(set(successful_predictions)) == 1
            agreement_percentage = (majority_count / len(successful_predictions)) * 100

            consensus = {
                "agreement": agreement,
                "majority_prediction": majority_prediction,
                "agreement_percentage": round(agreement_percentage, 2),
                "total_models": len(successful_predictions),
                "distribution": dict(prediction_counts)
            }
        else:
            consensus = {
                "agreement": False,
                "majority_prediction": None,
                "agreement_percentage": 0,
                "total_models": 0,
                "distribution": {}
            }

        total_processing_time = (time.time() - start_time) * 1000

        # Record metrics
        COMPARISON_REQUESTS.labels(success=True).inc()

        return {
            "audio_info": {
                "filename": file.filename,
                "size_bytes": file_size
            },
            "comparisons": comparisons,
            "consensus": consensus,
            "total_processing_time_ms": round(total_processing_time, 2)
        }

    except HTTPException:
        raise
    except AudioProcessingError as e:
        COMPARISON_REQUESTS.labels(success=False).inc()
        logger.error(f"Audio processing error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio processing failed: {str(e)}"
        )
    except Exception as e:
        COMPARISON_REQUESTS.labels(success=False).inc()
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/models/local/list")
async def list_models() -> Dict[str, Any]:
    """
    List all available local model versions.

    Returns:
        {
            "total_models": 2,
            "latest_version": "2",
            "versions": [
                {
                    "version": "1",
                    "model_name": "Decision Tree Classifier",
                    "model_type": "DecisionTreeClassifier",
                    "feature_dimension": 162
                },
                {
                    "version": "2",
                    "model_name": "SVM with MFCC Features",
                    "model_type": "Pipeline (StandardScaler + RFE + SVC)",
                    "feature_dimension": 78
                }
            ]
        }
    """
    try:
        registry = get_registry()
        available_versions = registry.list_versions()

        versions_info = []
        for version in available_versions:
            info = registry.get_model_info(version)
            if info:
                versions_info.append({
                    "version": version,
                    "model_name": info.get("model_name"),
                    "model_type": info.get("model_type"),
                    "feature_dimension": info.get("feature_dimension"),
                    "created_date": info.get("created_date")
                })

        return {
            "total_models": len(available_versions),
            "latest_version": registry.latest_version,
            "versions": versions_info
        }

    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {str(e)}"
        )


@router.get("/models/local/{version}/info")
async def get_model_info(
    version: str = PathParam(..., description="Model version number")
) -> Dict[str, Any]:
    """
    Get detailed information about a specific model version.

    Args:
        version: Model version number

    Returns:
        {
            "version": "2",
            "model_type": "Pipeline (StandardScaler + RFE + SVC)",
            "model_name": "SVM with MFCC Features",
            "description": "Support Vector Machine with MFCC-based features...",
            "feature_dimension": 78,
            "feature_extraction": "MFCCs with delta and delta-delta coefficients",
            "classes": ["angry", "disgust", "fear", "happy", "neutral", "sad"],
            "num_classes": 6,
            "created_date": "2024-01-20",
            "dataset": "CREMA-D",
            "notes": "Improved model with feature selection..."
        }

    Raises:
        HTTPException: 404 if version not found
    """
    try:
        registry = get_registry()
        info = registry.get_model_info(version)

        if info is None:
            available_versions = registry.list_versions()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model version {version} not found. Available versions: {available_versions}"
            )

        return info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting model info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get model info: {str(e)}"
        )


@router.get("/models/local/latest")
async def get_latest_model_info() -> Dict[str, Any]:
    """
    Get information about the latest model version.

    Returns:
        Same format as /models/local/{version}/info

    Raises:
        HTTPException: 404 if no models registered
    """
    try:
        registry = get_registry()
        latest_model = registry.get_latest()

        if latest_model is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No models registered. Please add models to the models directory."
            )

        info = registry.get_model_info(latest_model.version)

        if info is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model info not found for version {latest_model.version}"
            )

        return info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest model info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get latest model info: {str(e)}"
        )


def _log_prediction_for_monitoring(
    result: Dict[str, Any], filename: str, background_tasks: BackgroundTasks | None
) -> str:
    """Send prediction details to the monitoring buffer and trigger reports.

    Returns:
        prediction_id: UUID of the logged prediction (for feedback submission)
    """

    try:
        monitoring_service = get_monitoring_service()
        record = PredictionRecord(
            timestamp=datetime.utcnow(),
            model_version=str(result.get("model_version")),
            predicted_emotion=str(result.get("emotion")),
            confidence=float(result.get("confidence", 0.0)),
            probabilities=result.get("all_probabilities", {}),
            features=result.get("features", {}),
            filename=filename,
        )

        buffer_length = monitoring_service.log_prediction(record)

        if background_tasks and monitoring_service.should_generate_report(buffer_length):
            background_tasks.add_task(monitoring_service.generate_report)

        return record.prediction_id

    except Exception as exc:  # pragma: no cover - telemetry shouldn't break inference
        logger.warning("Monitoring logging skipped", error=str(exc))
        return ""  # Return empty string if logging fails
