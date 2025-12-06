"""
Utility functions and helpers for testing.

This module provides common helper functions, assertions, and utilities
used across different test modules.
"""

import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import requests
import soundfile as sf
from fastapi.testclient import TestClient


class AudioTestUtils:
    """Utilities for audio-related testing."""

    @staticmethod
    def create_test_audio(
        duration: float = 2.0,
        sample_rate: int = 22050,
        frequency: float = 440.0,
        format: str = "WAV",
    ) -> bytes:
        """Create a test audio file with specified parameters."""
        # Generate time array
        t = np.linspace(0, duration, int(sample_rate * duration), False)

        # Generate sine wave with harmonics
        audio_data = np.sin(2 * np.pi * frequency * t)
        audio_data += 0.3 * np.sin(4 * np.pi * frequency * t)
        audio_data += 0.1 * np.sin(6 * np.pi * frequency * t)

        # Add some noise to make it more realistic
        noise = np.random.normal(0, 0.01, len(audio_data))
        audio_data += noise

        # Normalize
        audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8

        # Convert to bytes
        with tempfile.NamedTemporaryFile(suffix=f".{format.lower()}", delete=False) as temp_file:
            sf.write(temp_file.name, audio_data, sample_rate, format=format)
            with open(temp_file.name, "rb") as f:
                audio_bytes = f.read()
            Path(temp_file.name).unlink()  # Clean up

        return audio_bytes

    @staticmethod
    def create_silent_audio(duration: float = 1.0, sample_rate: int = 22050) -> bytes:
        """Create silent audio for testing."""
        audio_data = np.zeros(int(sample_rate * duration))

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            sf.write(temp_file.name, audio_data, sample_rate, format="WAV")
            with open(temp_file.name, "rb") as f:
                audio_bytes = f.read()
            Path(temp_file.name).unlink()

        return audio_bytes

    @staticmethod
    def create_corrupted_audio() -> bytes:
        """Create corrupted audio data for error testing."""
        return b"This is not valid audio data"

    @staticmethod
    def validate_audio_features(features: dict[str, Any]) -> bool:
        """Validate that audio features have correct structure."""
        required_keys = [
            "mfcc",
            "chroma",
            "spectral_centroid",
            "spectral_rolloff",
            "zero_crossing_rate",
            "rms",
            "metadata",
        ]

        if not all(key in features for key in required_keys):
            return False

        # Validate feature shapes (basic checks)
        if not isinstance(features["mfcc"], list) or len(features["mfcc"]) != 13:
            return False

        if not isinstance(features["chroma"], list) or len(features["chroma"]) != 12:
            return False

        # Validate metadata
        metadata = features.get("metadata", {})
        required_metadata_keys = [
            "duration",
            "sample_rate",
            "channels",
            "format",
            "file_size_bytes",
        ]

        return all(key in metadata for key in required_metadata_keys)


class APITestUtils:
    """Utilities for API testing."""

    @staticmethod
    def make_authenticated_request(
        client: TestClient, method: str, endpoint: str, token: str, **kwargs
    ) -> requests.Response:
        """Make an authenticated API request."""
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"

        return client.request(method, endpoint, headers=headers, **kwargs)

    @staticmethod
    def upload_audio_file(
        client: TestClient,
        endpoint: str,
        audio_data: bytes,
        filename: str,
        additional_data: dict[str, Any] | None = None,
    ) -> requests.Response:
        """Upload an audio file to the API."""
        files = {"file": (filename, audio_data, "audio/wav")}

        if additional_data:
            files.update(additional_data)

        return client.post(endpoint, files=files)

    @staticmethod
    def assert_api_response(
        response: requests.Response,
        expected_status: int = 200,
        expected_success: bool = True,
        check_data_structure: bool = True,
    ) -> dict[str, Any]:
        """Assert common API response properties."""
        assert (
            response.status_code == expected_status
        ), f"Expected {expected_status}, got {response.status_code}"

        data = response.json()

        if expected_success:
            assert data.get("success") is True, "Response should indicate success"
        else:
            assert data.get("success") is False, "Response should indicate failure"

        assert "timestamp" in data, "Response should include timestamp"
        assert "request_id" in data, "Response should include request ID"

        if check_data_structure and expected_success:
            assert "data" in data, "Success response should include data"

        return data

    @staticmethod
    def assert_error_response(
        response: requests.Response, expected_status: int, expected_error_code: str | None = None
    ) -> dict[str, Any]:
        """Assert error response properties."""
        data = APITestUtils.assert_api_response(response, expected_status, expected_success=False)

        if expected_error_code:
            assert (
                data.get("error_code") == expected_error_code
            ), f"Expected error code {expected_error_code}"

        assert "message" in data, "Error response should include message"

        return data


class WebSocketTestUtils:
    """Utilities for WebSocket testing."""

    @staticmethod
    async def send_ping(websocket) -> None:
        """Send ping message through WebSocket."""
        await websocket.send_json({"type": "ping"})

    @staticmethod
    async def wait_for_message(websocket, timeout: float = 5.0) -> dict[str, Any] | None:
        """Wait for WebSocket message with timeout."""
        try:
            return await asyncio.wait_for(websocket.receive_json(), timeout=timeout)
        except TimeoutError:
            return None

    @staticmethod
    def validate_websocket_message(message: dict[str, Any], message_type: str) -> bool:
        """Validate WebSocket message structure."""
        if not isinstance(message, dict):
            return False

        if message.get("type") != message_type:
            return False

        if "timestamp" not in message:
            return False

        return True


class MockUtils:
    """Utilities for creating and configuring mocks."""

    @staticmethod
    def create_mock_s3_client() -> MagicMock:
        """Create a comprehensive mock S3 client."""
        mock_client = MagicMock()

        # Mock upload methods
        mock_client.upload_fileobj.return_value = None
        mock_client.put_object.return_value = {"ETag": "mock-etag"}

        # Mock download methods
        mock_client.download_file.return_value = None
        mock_client.get_object.return_value = {
            "Body": MagicMock(),
            "ContentLength": 1024,
            "LastModified": "2024-01-01T00:00:00Z",
        }

        # Mock bucket operations
        mock_client.head_bucket.return_value = {}
        mock_client.create_bucket.return_value = {"Location": "/test-bucket"}

        # Mock object operations
        mock_client.head_object.return_value = {
            "ContentLength": 1024,
            "LastModified": "2024-01-01T00:00:00Z",
            "ETag": "mock-etag",
        }

        return mock_client

    @staticmethod
    def create_mock_sagemaker_runtime() -> MagicMock:
        """Create a comprehensive mock SageMaker runtime client."""
        mock_client = MagicMock()

        # Mock successful response
        mock_client.invoke_endpoint.return_value = {
            "Body": MagicMock(),
            "ContentType": "application/json",
            "InvokedProductionVariant": "variant-1",
        }

        # Configure the Body mock to return JSON data
        mock_response_data = {
            "predictions": [
                {"label": "happy", "confidence": 0.85},
                {"label": "neutral", "confidence": 0.10},
                {"label": "sad", "confidence": 0.05},
            ]
        }

        mock_client.invoke_endpoint.return_value["Body"].read.return_value = json.dumps(
            mock_response_data
        ).encode()

        return mock_client

    @staticmethod
    def create_mock_redis() -> MagicMock:
        """Create a comprehensive mock Redis client."""
        mock_redis = MagicMock()

        # Mock basic operations
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True
        mock_redis.setex.return_value = True
        mock_redis.delete.return_value = 1
        mock_redis.exists.return_value = False

        # Mock hash operations
        mock_redis.hget.return_value = None
        mock_redis.hset.return_value = 1
        mock_redis.hgetall.return_value = {}
        mock_redis.hdel.return_value = 1

        # Mock list operations
        mock_redis.lpush.return_value = 1
        mock_redis.rpop.return_value = None
        mock_redis.lrange.return_value = []

        # Mock set operations
        mock_redis.sadd.return_value = 1
        mock_redis.srem.return_value = 1
        mock_redis.smembers.return_value = set()

        return mock_redis


class PerformanceTestUtils:
    """Utilities for performance testing."""

    @staticmethod
    async def measure_async_execution_time(func, *args, **kwargs) -> tuple[float, Any]:
        """Measure execution time of async function."""
        start_time = time.time()
        result = await func(*args, **kwargs)
        execution_time = time.time() - start_time
        return execution_time, result

    @staticmethod
    def measure_execution_time(func, *args, **kwargs) -> tuple[float, Any]:
        """Measure execution time of synchronous function."""
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        return execution_time, result

    @staticmethod
    async def run_concurrent_requests(
        client: TestClient, endpoint: str, num_requests: int = 10, **kwargs
    ) -> list[requests.Response]:
        """Run multiple concurrent requests to an endpoint."""

        async def make_request():
            # Note: TestClient is synchronous, so we'll run it in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, client.get, endpoint, **kwargs)

        tasks = [make_request() for _ in range(num_requests)]
        return await asyncio.gather(*tasks)

    @staticmethod
    def calculate_performance_metrics(responses: list[requests.Response]) -> dict[str, Any]:
        """Calculate performance metrics from a list of responses."""
        if not responses:
            return {}

        status_codes = [r.status_code for r in responses]
        response_times = [r.elapsed.total_seconds() for r in responses if hasattr(r, "elapsed")]

        return {
            "total_requests": len(responses),
            "successful_requests": sum(1 for code in status_codes if 200 <= code < 300),
            "failed_requests": sum(1 for code in status_codes if code >= 400),
            "success_rate": sum(1 for code in status_codes if 200 <= code < 300) / len(responses),
            "avg_response_time": np.mean(response_times) if response_times else 0,
            "min_response_time": np.min(response_times) if response_times else 0,
            "max_response_time": np.max(response_times) if response_times else 0,
            "p95_response_time": np.percentile(response_times, 95) if response_times else 0,
            "p99_response_time": np.percentile(response_times, 99) if response_times else 0,
        }


class ValidationUtils:
    """Utilities for data validation in tests."""

    @staticmethod
    def validate_uuid(uuid_string: str) -> bool:
        """Validate UUID string format."""
        import uuid as uuid_lib

        try:
            uuid_lib.UUID(uuid_string)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_iso_timestamp(timestamp: str) -> bool:
        """Validate ISO timestamp format."""
        try:
            from datetime import datetime

            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format."""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    @staticmethod
    def validate_audio_metadata(metadata: dict[str, Any]) -> bool:
        """Validate audio metadata structure."""
        required_fields = ["duration", "sample_rate", "channels", "format", "file_size_bytes"]

        if not all(field in metadata for field in required_fields):
            return False

        # Validate value ranges
        if metadata["duration"] <= 0 or metadata["duration"] > 300:  # 5 minutes max
            return False

        if metadata["sample_rate"] <= 0 or metadata["sample_rate"] > 192000:  # Reasonable range
            return False

        if metadata["channels"] not in [1, 2]:  # Mono or stereo
            return False

        if (
            metadata["file_size_bytes"] <= 0 or metadata["file_size_bytes"] > 100 * 1024 * 1024
        ):  # 100MB max
            return False

        return True


class FileTestUtils:
    """Utilities for file-related testing."""

    @staticmethod
    def create_temp_file(content: bytes, suffix: str = ".tmp") -> Path:
        """Create temporary file with given content."""
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
            temp_file.write(content)
            return Path(temp_file.name)

    @staticmethod
    def cleanup_temp_files(pattern: str = "/tmp/test_*") -> None:
        """Clean up temporary files matching pattern."""
        import glob

        for file_path in glob.glob(pattern):
            try:
                Path(file_path).unlink()
            except OSError:
                pass

    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        import hashlib

        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)

        return hash_sha256.hexdigest()


# Common assertions
def assert_audio_processing_result(
    result: dict[str, Any], expected_keys: list[str] | None = None
) -> None:
    """Assert audio processing result has expected structure."""
    default_keys = [
        "mfcc",
        "chroma",
        "spectral_centroid",
        "spectral_rolloff",
        "zero_crossing_rate",
        "rms",
        "metadata",
    ]
    expected_keys = expected_keys or default_keys

    assert isinstance(result, dict), "Result should be a dictionary"
    assert all(key in result for key in expected_keys), f"Missing keys in result: {expected_keys}"
    assert ValidationUtils.validate_audio_metadata(result["metadata"]), "Invalid metadata structure"


def assert_emotion_prediction(prediction: dict[str, Any]) -> None:
    """Assert emotion prediction has expected structure."""
    assert isinstance(prediction, dict), "Prediction should be a dictionary"
    assert "predictions" in prediction, "Missing predictions key"
    assert isinstance(prediction["predictions"], list), "Predictions should be a list"
    assert len(prediction["predictions"]) > 0, "Should have at least one prediction"

    for pred in prediction["predictions"]:
        assert "label" in pred, "Prediction should have label"
        assert "confidence" in pred, "Prediction should have confidence"
        assert isinstance(pred["confidence"], (int, float)), "Confidence should be numeric"
        assert 0 <= pred["confidence"] <= 1, "Confidence should be between 0 and 1"
