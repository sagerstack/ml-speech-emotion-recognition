"""
Pytest configuration and fixtures for ML Speech Emotion Recognition API tests.

This module provides common fixtures, test configuration, and utilities
for unit, integration, and end-to-end tests.
"""

import asyncio
import io
import json
import logging
import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional
from unittest.mock import MagicMock, Mock

import boto3
import librosa
import numpy as np
import pytest
import pytest_asyncio
import soundfile as sf
from fastapi.testclient import TestClient
from moto import mock_aws

# Ensure the backend package is importable when running tests from repo root
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app
from app.services.audio_service import AudioProcessor, AudioFeatures, AudioMetadata
from app.utils.config import Settings, get_settings
from app.utils.logging import get_logger, setup_logging

# Configure logging for tests
setup_logging()
logger = get_logger(__name__)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def test_environment() -> None:
    """Set up test environment variables and configuration."""
    # Set test environment variables
    os.environ["DEBUG"] = "true"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["SAGEMAKER_ENDPOINT_NAME"] = "test-endpoint"
    os.environ["SECRET_KEY"] = "test-secret-key-for-jwt"
    os.environ["S3_BUCKET_NAME"] = "your-s3-bucket-name"  # Default for tests

    # Disable actual AWS services during testing
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def test_settings() -> Settings:
    """Get test settings instance."""
    return Settings(
        debug=True,
        app_name="Test ML Speech Emotion Recognition API",
        aws_region="us-east-1",
        sagemaker_endpoint_name="test-emotion-endpoint",
        secret_key="test-secret-key-for-jwt-testing",
        max_upload_size_mb=10,
        max_audio_duration_seconds=30,
        cors_origins=["http://localhost:3000", "http://localhost:8501"]
    )


@pytest.fixture
def test_client() -> TestClient:
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_s3_client() -> Generator[boto3.client, None, None]:
    """Create mocked S3 client for testing."""
    with mock_aws():
        s3_client = boto3.client("s3", region_name="us-east-1")
        # Create test bucket
        s3_client.create_bucket(Bucket="test-audio-bucket")
        yield s3_client


@pytest.fixture
def mock_sagemaker_runtime() -> Generator[MagicMock, None, None]:
    """Create mocked SageMaker runtime client."""
    with mock_aws():
        runtime_client = MagicMock()
        runtime_client.invoke_endpoint.return_value = {
            "Body": io.BytesIO(json.dumps({
                "predictions": [
                    {"label": "happy", "confidence": 0.85},
                    {"label": "neutral", "confidence": 0.10},
                    {"label": "sad", "confidence": 0.05}
                ]
            }).encode())
        }
        yield runtime_client


@pytest.fixture
def audio_processor() -> AudioProcessor:
    """Create audio processor instance for testing."""
    return AudioProcessor()


@pytest.fixture
def sample_audio_file() -> bytes:
    """Create a sample WAV audio file for testing."""
    # Generate a simple sine wave audio file
    sample_rate = 22050
    duration = 2.0  # 2 seconds
    frequency = 440  # A4 note

    # Generate time array
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    # Generate sine wave
    audio_data = np.sin(2 * np.pi * frequency * t)

    # Add some harmonics to make it more speech-like
    audio_data += 0.3 * np.sin(4 * np.pi * frequency * t)  # First harmonic
    audio_data += 0.1 * np.sin(6 * np.pi * frequency * t)  # Second harmonic

    # Normalize
    audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8

    # Convert to bytes
    audio_buffer = io.BytesIO()
    sf.write(audio_buffer, audio_data, sample_rate, format='WAV')
    audio_buffer.seek(0)

    return audio_buffer.read()


@pytest.fixture
def sample_mp3_file() -> bytes:
    """Create a sample MP3 audio file for testing."""
    # Create WAV first then convert (simplified approach)
    wav_data = librosa.tone(440, sr=22050, duration=2.0)

    # For testing purposes, we'll use WAV data as MP3
    # In real implementation, you'd convert to MP3
    audio_buffer = io.BytesIO()
    sf.write(audio_buffer, wav_data, 22050, format='WAV')
    audio_buffer.seek(0)

    return audio_buffer.read()


@pytest.fixture
def corrupted_audio_file() -> bytes:
    """Create a corrupted audio file for testing error handling."""
    return b"This is not a valid audio file"


@pytest.fixture
def large_audio_file() -> bytes:
    """Create a large audio file (exceeding size limit) for testing."""
    # Generate audio that exceeds the size limit but not duration limit
    # Use high sample rate and stereo to increase file size while keeping duration short
    sample_rate = 96000  # High sample rate
    duration = 20  # Short duration to avoid duration validation
    frequency = 440

    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Create stereo audio (2 channels) to double the file size
    audio_data = np.array([np.sin(2 * np.pi * frequency * t),
                          np.sin(2 * np.pi * frequency * t * 0.9)]).T

    audio_buffer = io.BytesIO()
    sf.write(audio_buffer, audio_data, sample_rate, format='WAV')
    audio_buffer.seek(0)
    file_bytes = audio_buffer.read()

    # If still not large enough, add some noise to increase size
    while len(file_bytes) < 12 * 1024 * 1024:  # Target > 12MB to exceed 10MB limit
        audio_buffer = io.BytesIO()
        # Add more channels or increase bit depth if needed
        multi_channel_data = np.tile(audio_data, (1, 4))  # 8 channels total
        sf.write(audio_buffer, multi_channel_data, sample_rate, format='WAV')
        audio_buffer.seek(0)
        file_bytes = audio_buffer.read()
        if len(file_bytes) > 50 * 1024 * 1024:  # Safety break
            break

    return file_bytes


@pytest.fixture
def sample_audio_metadata() -> AudioMetadata:
    """Create sample audio metadata for testing."""
    return AudioMetadata(
        duration=2.5,
        sample_rate=22050,
        channels=1,
        format="wav",
        file_size_bytes=110250
    )


@pytest.fixture
def sample_audio_features(sample_audio_metadata: AudioMetadata) -> AudioFeatures:
    """Create sample audio features for testing."""
    # Generate sample feature data
    n_frames = 87  # Typical number of frames for 2.5s audio

    return AudioFeatures(
        mfcc=np.random.randn(13, n_frames),
        chroma=np.random.randn(12, n_frames),
        spectral_centroid=np.random.randn(1, n_frames),
        spectral_rolloff=np.random.randn(1, n_frames),
        zero_crossing_rate=np.random.randn(1, n_frames),
        rms=np.random.randn(1, n_frames),
        metadata=sample_audio_metadata
    )


@pytest.fixture
def emotion_prediction_response() -> Dict[str, Any]:
    """Sample emotion prediction response from SageMaker."""
    return {
        "predictions": [
            {"label": "happy", "confidence": 0.85},
            {"label": "neutral", "confidence": 0.10},
            {"label": "sad", "confidence": 0.05}
        ],
        "processed_at": "2024-01-01T12:00:00Z",
        "model_version": "v1.0.0",
        "audio_metadata": {
            "duration": 2.5,
            "sample_rate": 22050,
            "channels": 1
        }
    }


@pytest.fixture
def temp_audio_dir() -> Generator[Path, None, None]:
    """Create temporary directory for audio files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_redis() -> MagicMock:
    """Create mocked Redis client."""
    redis_mock = MagicMock()
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.exists.return_value = False
    return redis_mock


@pytest.fixture
def correlation_id() -> str:
    """Generate correlation ID for request tracking."""
    return str(uuid.uuid4())


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Create authentication headers for testing."""
    return {
        "Authorization": "Bearer test-token",
        "Content-Type": "application/json",
        "X-Correlation-ID": str(uuid.uuid4())
    }


@pytest.fixture
def multipart_audio_data(sample_audio_file: bytes) -> Dict[str, Any]:
    """Create multipart form data for audio upload testing."""
    return {
        "file": ("test_audio.wav", sample_audio_file, "audio/wav"),
        "user_id": "test-user-123"
    }


@pytest.fixture
def error_responses() -> Dict[str, Dict[str, Any]]:
    """Sample error responses for testing."""
    return {
        "invalid_audio": {
            "detail": "Invalid audio file format",
            "error_code": "INVALID_AUDIO",
            "timestamp": "2024-01-01T12:00:00Z"
        },
        "file_too_large": {
            "detail": "Audio file size exceeds maximum allowed limit",
            "error_code": "FILE_TOO_LARGE",
            "timestamp": "2024-01-01T12:00:00Z"
        },
        "processing_error": {
            "detail": "Audio processing failed",
            "error_code": "PROCESSING_ERROR",
            "timestamp": "2024-01-01T12:00:00Z"
        },
        "aws_error": {
            "detail": "AWS service error",
            "error_code": "AWS_ERROR",
            "timestamp": "2024-01-01T12:00:00Z"
        }
    }


@pytest.fixture(autouse=True)
def cleanup_test_files() -> Generator[None, None, None]:
    """Clean up test files after each test."""
    yield
    # Clean up any temporary files created during tests
    temp_patterns = [
        "/tmp/test_audio_*",
        "/tmp/temp_audio_*",
        "/tmp/prediction_*"
    ]

    for pattern in temp_patterns:
        import glob
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
            except OSError:
                pass


# Mock external services
@pytest.fixture
def mock_aws_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock AWS credentials for testing."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


# Async fixtures
@pytest_asyncio.fixture
async def async_test_client() -> AsyncGenerator[TestClient, None]:
    """Create async test client."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Create mocked WebSocket connection."""
    websocket = MagicMock()
    websocket.send_text = MagicMock()
    websocket.receive_json = MagicMock(return_value={"type": "ping"})
    websocket.accept = MagicMock()
    return websocket


# Performance testing fixtures
@pytest.fixture
def performance_test_data() -> Dict[str, Any]:
    """Data for performance testing."""
    return {
        "concurrent_requests": 50,
        "max_response_time_ms": 5000,
        "success_rate_threshold": 0.95,
        "memory_limit_mb": 512
    }


# Logging test fixtures
@pytest.fixture
def log_capture() -> Generator[List[str], None, None]:
    """Capture log messages for testing."""
    messages = []

    class TestHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            messages.append(self.format(record))

    handler = TestHandler()
    logger = logging.getLogger()
    logger.addHandler(handler)

    yield messages

    logger.removeHandler(handler)


# Custom markers
def pytest_configure(config) -> None:
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "aws: marks tests that require AWS services"
    )
    config.addinivalue_line(
        "markers", "audio: marks tests that require audio processing"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
