"""
Factory classes for generating test data using factory-boy.

This module provides factories for creating test instances of models,
API responses, and other data structures used throughout the test suite.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import factory
import numpy as np
from faker import Faker

from app.services.audio_service import AudioFeatures, AudioMetadata

fake = Faker()


class AudioMetadataFactory(factory.Factory):
    """Factory for creating AudioMetadata instances."""

    class Meta:
        model = AudioMetadata

    duration = factory.Faker("pyfloat", left_digits=1, right_digits=2, min_value=0.5, max_value=30.0)
    sample_rate = 22050
    channels = 1
    format = factory.Iterator(["wav", "mp3", "flac", "m4a"])
    file_size_bytes = factory.Faker("pyint", min_value=1000, max_value=25000000)


class AudioFeaturesFactory(factory.Factory):
    """Factory for creating AudioFeatures instances."""

    class Meta:
        model = AudioFeatures

    mfcc = factory.LazyAttribute(lambda _: np.random.randn(13, 87))
    chroma = factory.LazyAttribute(lambda _: np.random.randn(12, 87))
    spectral_centroid = factory.LazyAttribute(lambda _: np.random.randn(1, 87))
    spectral_rolloff = factory.LazyAttribute(lambda _: np.random.randn(1, 87))
    zero_crossing_rate = factory.Lakerbute(lambda _: np.random.randn(1, 87))
    rms = factory.LazyAttribute(lambda _: np.random.randn(1, 87))
    metadata = factory.SubFactory(AudioMetadataFactory)


class EmotionPredictionFactory(factory.Factory):
    """Factory for creating emotion prediction responses."""

    class Meta:
        model = dict

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Create emotion prediction response."""
        emotions = ["happy", "sad", "angry", "fear", "disgust", "neutral", "surprise"]

        # Generate random confidence scores that sum to 1
        confidences = np.random.dirichlet(np.ones(len(emotions)))

        predictions = [
            {"label": emotion, "confidence": float(conf)}
            for emotion, conf in zip(emotions, confidences)
        ]

        # Sort by confidence
        predictions.sort(key=lambda x: x["confidence"], reverse=True)

        return {
            "predictions": predictions,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "model_version": "v1.0.0",
            "audio_metadata": {
                "duration": kwargs.get("duration", fake.pyfloat(left_digits=1, right_digits=2, min_value=0.5, max_value=30.0)),
                "sample_rate": 22050,
                "channels": 1
            }
        }


class APIResponseFactory(factory.Factory):
    """Factory for creating standard API responses."""

    class Meta:
        model = dict

    @classmethod
    def success_response(cls, data: Any = None, message: str = "Success"):
        """Create success response."""
        return {
            "success": True,
            "message": message,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": str(uuid.uuid4())
        }

    @classmethod
    def error_response(cls, message: str, error_code: str, details: Dict[str, Any] = None):
        """Create error response."""
        return {
            "success": False,
            "message": message,
            "error_code": error_code,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": str(uuid.uuid4())
        }


class UserFactory(factory.Factory):
    """Factory for creating user data."""

    class Meta:
        model = dict

    user_id = factory.LazyAttribute(lambda _: str(uuid.uuid4()))
    email = factory.Faker("email")
    name = factory.Faker("name")
    created_at = factory.LazyAttribute(lambda _: datetime.now(timezone.utc).isoformat())
    last_login = factory.LazyAttribute(lambda _: datetime.now(timezone.utc).isoformat())
    is_active = True
    subscription_tier = factory.Iterator(["free", "pro", "enterprise"])


class AudioUploadRequestFactory(factory.Factory):
    """Factory for creating audio upload request data."""

    class Meta:
        model = dict

    file_name = factory.Faker("file_name", extension="wav")
    file_size = factory.Faker("pyint", min_value=1000, max_value=25000000)
    content_type = factory.Iterator(["audio/wav", "audio/mp3", "audio/flac", "audio/m4a"])
    user_id = factory.LazyAttribute(lambda _: str(uuid.uuid4()))
    uploaded_at = factory.LazyAttribute(lambda _: datetime.now(timezone.utc).isoformat())


class ProcessingJobFactory(factory.Factory):
    """Factory for creating audio processing job data."""

    class Meta:
        model = dict

    job_id = factory.LazyAttribute(lambda _: str(uuid.uuid4()))
    user_id = factory.LazyAttribute(lambda _: str(uuid.uuid4()))
    status = factory.Iterator(["pending", "processing", "completed", "failed"])
    created_at = factory.LazyAttribute(lambda _: datetime.now(timezone.utc).isoformat())
    started_at = factory.LazyAttribute(lambda _: datetime.now(timezone.utc).isoformat())
    completed_at = factory.LazyAttribute(lambda _: datetime.now(timezone.utc).isoformat())
    file_name = factory.Faker("file_name", extension="wav")
    duration = factory.Faker("pyfloat", left_digits=1, right_digits=2, min_value=0.5, max_value=30.0)

    @classmethod
    def pending_job(cls):
        """Create a pending processing job."""
        return cls(
            status="pending",
            started_at=None,
            completed_at=None
        )

    @classmethod
    def processing_job(cls):
        """Create a processing job."""
        return cls(
            status="processing",
            completed_at=None
        )

    @classmethod
    def completed_job(cls):
        """Create a completed processing job."""
        return cls(
            status="completed",
            result=EmotionPredictionFactory()
        )

    @classmethod
    def failed_job(cls, error_message: str = "Processing failed"):
        """Create a failed processing job."""
        return cls(
            status="failed",
            error_message=error_message
        )


class MetricsDataFactory(factory.Factory):
    """Factory for creating metrics data."""

    class Meta:
        model = dict

    timestamp = factory.LazyAttribute(lambda _: datetime.now(timezone.utc).isoformat())
    request_count = factory.Faker("pyint", min_value=0, max_value=1000)
    error_count = factory.Faker("pyint", min_value=0, max_value=100)
    avg_response_time_ms = factory.Faker("pyfloat", left_digits=3, right_digits=2, min_value=50, max_value=5000)
    active_users = factory.Faker("pyint", min_value=0, max_value=100)
    total_audio_processed = factory.Faker("pyint", min_value=0, max_value=500)


class WebSocketMessageFactory(factory.Factory):
    """Factory for creating WebSocket messages."""

    class Meta:
        model = dict

    @classmethod
    def ping_message(cls):
        """Create ping message."""
        return {
            "type": "ping",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def pong_message(cls):
        """Create pong message."""
        return {
            "type": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def prediction_update(cls, job_id: str, status: str, progress: float = None):
        """Create prediction update message."""
        message = {
            "type": "prediction_update",
            "job_id": job_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if progress is not None:
            message["progress"] = progress

        return message

    @classmethod
    def prediction_complete(cls, job_id: str, result: Dict[str, Any]):
        """Create prediction complete message."""
        return {
            "type": "prediction_complete",
            "job_id": job_id,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def error_message(cls, error_message: str, error_code: str):
        """Create error message."""
        return {
            "type": "error",
            "error": error_message,
            "error_code": error_code,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class S3EventFactory(factory.Factory):
    """Factory for creating S3 event data."""

    class Meta:
        model = dict

    @classmethod
    def upload_event(cls, bucket_name: str, key: str):
        """Create S3 upload event."""
        return {
            "eventVersion": "2.1",
            "eventSource": "aws:s3",
            "awsRegion": "us-east-1",
            "eventTime": datetime.now(timezone.utc).isoformat(),
            "eventName": "ObjectCreated:Put",
            "s3": {
                "bucket": {"name": bucket_name},
                "object": {
                    "key": key,
                    "size": factory.Faker("pyint", min_value=1000, max_value=25000000),
                    "eTag": factory.Faker("md5")
                }
            }
        }


class SageMakerResponseFactory(factory.Factory):
    """Factory for creating SageMaker response data."""

    class Meta:
        model = dict

    @classmethod
    def successful_inference(cls, predictions: List[Dict[str, Any]]):
        """Create successful SageMaker inference response."""
        return {
            "predictions": predictions,
            "model_name": "emotion-recognition-v1",
            "model_version": "1.0.0",
            "inference_time": 0.123,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def failed_inference(cls, error_message: str):
        """Create failed SageMaker inference response."""
        return {
            "error": error_message,
            "error_type": "ModelError",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


# Test data generators
class TestDataGenerator:
    """Utility class for generating complex test data scenarios."""

    @staticmethod
    def create_batch_predictions(count: int = 10) -> List[Dict[str, Any]]:
        """Create a batch of emotion predictions."""
        return [EmotionPredictionFactory() for _ in range(count)]

    @staticmethod
    def create_time_series_metrics(hours: int = 24) -> List[Dict[str, Any]]:
        """Create time series metrics data."""
        metrics = []
        base_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)

        for i in range(hours):
            timestamp = base_time.replace(hour=base_time.hour - (hours - i))
            metrics.append({
                **MetricsDataFactory(),
                "timestamp": timestamp.isoformat()
            })

        return metrics

    @staticmethod
    def create_user_session(user_id: str = None) -> Dict[str, Any]:
        """Create user session data."""
        return {
            "session_id": str(uuid.uuid4()),
            "user_id": user_id or str(uuid.uuid4()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "ip_address": fake.ipv4(),
            "user_agent": fake.user_agent(),
            "request_count": factory.Faker("pyint", min_value=1, max_value=100)
        }

    @staticmethod
    def create_error_scenario(error_type: str) -> Dict[str, Any]:
        """Create specific error scenario data."""
        scenarios = {
            "invalid_format": {
                "error_code": "INVALID_AUDIO_FORMAT",
                "message": "Unsupported audio format",
                "details": {"supported_formats": ["wav", "mp3", "flac", "m4a"]}
            },
            "file_too_large": {
                "error_code": "FILE_TOO_LARGE",
                "message": "Audio file exceeds size limit",
                "details": {"max_size_mb": 25, "actual_size_mb": 30}
            },
            "processing_failed": {
                "error_code": "PROCESSING_FAILED",
                "message": "Audio processing failed",
                "details": {"stage": "feature_extraction", "error": "Corrupted audio data"}
            },
            "aws_error": {
                "error_code": "AWS_SERVICE_ERROR",
                "message": "AWS service temporarily unavailable",
                "details": {"service": "sagemaker", "region": "us-east-1"}
            }
        }

        return scenarios.get(error_type, scenarios["processing_failed"])