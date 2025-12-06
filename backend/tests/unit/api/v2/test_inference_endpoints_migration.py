"""Unit tests for v2 inference endpoint migrations (v1 to v2).

This test suite follows TDD (Test-Driven Development) approach:
1. Write tests first that define the expected behavior
2. Tests will fail initially (RED)
3. Implement code to make tests pass (GREEN)
4. Refactor while keeping tests green (REFACTOR)

Test Coverage:
- GET /v2/inference/versions - List all available model versions
- GET /v2/inference/{version}/info - Get info for specific version
- GET /v2/inference/info - Get info for latest version
- POST /v2/inference - Renamed from POST /v2/inference/latest
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.domain.model.entities.inference import Inference
from app.domain.model.entities.model_info import ModelInfo
from app.domain.model.value_objects.emotion import Emotion
from app.domain.model.value_objects.model_version import ModelVersion
from app.infrastructure.di.providers import (
    get_model_info_use_case,
    get_model_versions_use_case,
    get_run_inference_use_case,
)
from app.main import app


@pytest.fixture
def client():
    """Create test client and clear dependency overrides after each test."""
    client = TestClient(app)
    yield client
    # Cleanup after each test
    app.dependency_overrides.clear()


@pytest.fixture
def sample_audio_bytes():
    """Create sample audio bytes for testing."""
    # Minimal valid WAV file header (44 bytes)
    wav_header = (
        b"RIFF" + b"\x24\x00\x00\x00" +  # ChunkSize (36 bytes)
        b"WAVE" +
        b"fmt " + b"\x10\x00\x00\x00" +  # Subchunk1Size (16 bytes)
        b"\x01\x00" +  # AudioFormat (PCM)
        b"\x01\x00" +  # NumChannels (1)
        b"\x44\xac\x00\x00" +  # SampleRate (44100)
        b"\x88\x58\x01\x00" +  # ByteRate
        b"\x02\x00" +  # BlockAlign
        b"\x10\x00" +  # BitsPerSample (16)
        b"data" + b"\x00\x00\x00\x00"  # Subchunk2Size (0 bytes of data)
    )
    return wav_header


class TestGetModelVersionsEndpoint:
    """Test suite for GET /v2/inference/versions endpoint."""

    def test_get_versions_success(self, client):
        """Test successful retrieval of model versions."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = {
            "versions": ["v4", "v3", "v2", "v1"],
            "latest": "v4",
            "count": 4,
        }

        # Override dependency
        app.dependency_overrides[get_model_versions_use_case] = lambda: mock_use_case

        # Act
        response = client.get("/v2/inference/versions")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert "latest" in data
        assert "count" in data
        assert data["versions"] == ["v4", "v3", "v2", "v1"]
        assert data["latest"] == "v4"
        assert data["count"] == 4

        # Verify use case was called
        mock_use_case.execute.assert_called_once()

    def test_get_versions_empty_list(self, client):
        """Test retrieval when no models exist."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = {
            "versions": [],
            "latest": None,
            "count": 0,
        }

        # Override dependency
        app.dependency_overrides[get_model_versions_use_case] = lambda: mock_use_case

        # Act
        response = client.get("/v2/inference/versions")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["versions"] == []
        assert data["latest"] is None
        assert data["count"] == 0

    def test_get_versions_single_version(self, client):
        """Test retrieval with single version."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = {
            "versions": ["v1"],
            "latest": "v1",
            "count": 1,
        }

        # Override dependency
        app.dependency_overrides[get_model_versions_use_case] = lambda: mock_use_case

        # Act
        response = client.get("/v2/inference/versions")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["versions"] == ["v1"]
        assert data["latest"] == "v1"
        assert data["count"] == 1

    def test_get_versions_error_handling(self, client):
        """Test error handling when use case raises exception."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = Exception("Database connection failed")

        # Override dependency
        app.dependency_overrides[get_model_versions_use_case] = lambda: mock_use_case

        # Act
        response = client.get("/v2/inference/versions")

        # Assert
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]


class TestGetModelInfoByVersionEndpoint:
    """Test suite for GET /v2/inference/{version}/info endpoint."""

    def test_get_model_info_success(self, client):
        """Test successful retrieval of model info by version."""
        # Arrange
        mock_use_case = MagicMock()
        mock_info = ModelInfo(
            version=ModelVersion.from_string("v4"),
            model_type="Ultra Ensemble (Stacking + Extra Trees + Gradient Boosting + Majority Voting)",
            feature_dimension=210,
            model_name="Ultra Ensemble Model v4",
            sklearn_version="1.6.1",
            created_date="2024-12-03",
            dataset="CREMA-D",
            classes=["angry", "disgust", "fear", "happy", "neutral", "sad"],
            num_classes=6,
            training_samples="~5,581",
            validation_dataset="RAVDESS",
            feature_extraction="Enhanced features: MFCC (20) + Deltas (40) + Prosodic (8) + Mel Spectrogram (128) + Chroma (12) + ZCR (1) + RMS (1)",
            notes="Trained on CREMA-D dataset (75% train split). Validated on RAVDESS for cross-dataset generalization testing. Includes audio trimming (top_db=20) for consistent feature extraction.",
        )
        mock_use_case.execute.return_value = mock_info

        # Override dependency
        app.dependency_overrides[get_model_info_use_case] = lambda: mock_use_case

        # Act
        response = client.get("/v2/inference/v4/info")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "v4"
        assert data["model_type"] == "Ultra Ensemble (Stacking + Extra Trees + Gradient Boosting + Majority Voting)"
        assert data["feature_dimension"] == 210
        assert data["available"] is True
        # Verify all new metadata fields are present
        assert data["model_name"] == "Ultra Ensemble Model v4"
        assert data["sklearn_version"] == "1.6.1"
        assert data["created_date"] == "2024-12-03"
        assert data["dataset"] == "CREMA-D"
        assert data["classes"] == ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        assert data["num_classes"] == 6
        assert data["training_samples"] == "~5,581"
        assert data["validation_dataset"] == "RAVDESS"
        assert data["feature_extraction"] == "Enhanced features: MFCC (20) + Deltas (40) + Prosodic (8) + Mel Spectrogram (128) + Chroma (12) + ZCR (1) + RMS (1)"
        assert data["notes"] == "Trained on CREMA-D dataset (75% train split). Validated on RAVDESS for cross-dataset generalization testing. Includes audio trimming (top_db=20) for consistent feature extraction."

        # Verify use case was called with correct version
        mock_use_case.execute.assert_called_once_with("v4")

    def test_get_model_info_version_without_prefix(self, client):
        """Test retrieval with version number without 'v' prefix."""
        # Arrange
        mock_use_case = MagicMock()
        mock_info = ModelInfo(
            version=ModelVersion.from_string("v3"),
            model_type="LSTM",
            feature_dimension=180,
        )
        mock_use_case.execute.return_value = mock_info

        # Override dependency
        app.dependency_overrides[get_model_info_use_case] = lambda: mock_use_case

        # Act
        response = client.get("/v2/inference/3/info")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "v3"

        # Verify use case was called (could be "3" or "v3" depending on endpoint logic)
        mock_use_case.execute.assert_called_once()

    def test_get_model_info_not_found(self, client):
        """Test retrieval of non-existent model version."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = None

        # Override dependency
        app.dependency_overrides[get_model_info_use_case] = lambda: mock_use_case

        # Act
        response = client.get("/v2/inference/v999/info")

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_model_info_error_handling(self, client):
        """Test error handling when use case raises exception."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = Exception("Failed to load model metadata")

        # Override dependency
        app.dependency_overrides[get_model_info_use_case] = lambda: mock_use_case

        # Act
        response = client.get("/v2/inference/v4/info")

        # Assert
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_get_model_info_backward_compatibility(self, client):
        """Test backward compatibility when metadata fields are missing."""
        # Arrange
        mock_use_case = MagicMock()
        # Create ModelInfo with only required fields (no optional metadata)
        mock_info = ModelInfo(
            version=ModelVersion.from_string("v3"),
            model_type="LSTM",
            feature_dimension=180,
        )
        mock_use_case.execute.return_value = mock_info

        # Override dependency
        app.dependency_overrides[get_model_info_use_case] = lambda: mock_use_case

        # Act
        response = client.get("/v2/inference/v3/info")

        # Assert
        assert response.status_code == 200
        data = response.json()
        # Required fields should always be present
        assert data["version"] == "v3"
        assert data["model_type"] == "LSTM"
        assert data["feature_dimension"] == 180
        assert data["available"] is True
        # Optional fields should not be in response when they are None
        assert "model_name" not in data
        assert "sklearn_version" not in data
        assert "created_date" not in data
        assert "dataset" not in data
        assert "classes" not in data
        assert "num_classes" not in data
        assert "training_samples" not in data
        assert "validation_dataset" not in data
        assert "feature_extraction" not in data
        assert "notes" not in data


class TestGetLatestModelInfoEndpoint:
    """Test suite for GET /v2/inference/info endpoint (latest version)."""

    def test_get_latest_model_info_success(self, client):
        """Test successful retrieval of latest model info."""
        # Arrange
        mock_use_case = MagicMock()
        mock_info = ModelInfo(
            version=ModelVersion.from_string("v4"),
            model_type="Ultra Ensemble (Stacking + Extra Trees + Gradient Boosting + Majority Voting)",
            feature_dimension=210,
            model_name="Ultra Ensemble Model v4",
            sklearn_version="1.6.1",
            created_date="2024-12-03",
            dataset="CREMA-D",
            classes=["angry", "disgust", "fear", "happy", "neutral", "sad"],
            num_classes=6,
            training_samples="~5,581",
            validation_dataset="RAVDESS",
            feature_extraction="Enhanced features: MFCC (20) + Deltas (40) + Prosodic (8) + Mel Spectrogram (128) + Chroma (12) + ZCR (1) + RMS (1)",
            notes="Trained on CREMA-D dataset (75% train split). Validated on RAVDESS for cross-dataset generalization testing. Includes audio trimming (top_db=20) for consistent feature extraction.",
        )
        mock_use_case.execute.return_value = mock_info

        # Override dependency
        app.dependency_overrides[get_model_info_use_case] = lambda: mock_use_case

        # Act
        response = client.get("/v2/inference/info")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "v4"
        assert data["model_type"] == "Ultra Ensemble (Stacking + Extra Trees + Gradient Boosting + Majority Voting)"
        assert data["feature_dimension"] == 210
        assert data["available"] is True
        assert data["is_latest"] is True
        # Verify all new metadata fields are present
        assert data["model_name"] == "Ultra Ensemble Model v4"
        assert data["sklearn_version"] == "1.6.1"
        assert data["created_date"] == "2024-12-03"
        assert data["dataset"] == "CREMA-D"
        assert data["classes"] == ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        assert data["num_classes"] == 6
        assert data["training_samples"] == "~5,581"
        assert data["validation_dataset"] == "RAVDESS"
        assert data["feature_extraction"] == "Enhanced features: MFCC (20) + Deltas (40) + Prosodic (8) + Mel Spectrogram (128) + Chroma (12) + ZCR (1) + RMS (1)"
        assert data["notes"] == "Trained on CREMA-D dataset (75% train split). Validated on RAVDESS for cross-dataset generalization testing. Includes audio trimming (top_db=20) for consistent feature extraction."

        # Verify use case was called with "v4" (latest version)
        mock_use_case.execute.assert_called_once_with("v4")

    def test_get_latest_model_info_no_models(self, client):
        """Test retrieval when no models exist."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = None

        # Override dependency
        app.dependency_overrides[get_model_info_use_case] = lambda: mock_use_case

        # Act
        response = client.get("/v2/inference/info")

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_latest_model_info_error_handling(self, client):
        """Test error handling when use case raises exception."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = Exception("Failed to get latest model")

        # Override dependency
        app.dependency_overrides[get_model_info_use_case] = lambda: mock_use_case

        # Act
        response = client.get("/v2/inference/info")

        # Assert
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]


class TestPostInferenceEndpoint:
    """Test suite for POST /v2/inference endpoint (renamed from /latest)."""

    def test_post_inference_success(self, client, sample_audio_bytes):
        """Test successful inference with new endpoint path."""
        # Arrange
        all_probabilities = {
            Emotion.ANGRY: 0.05,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.02,
            Emotion.HAPPY: 0.85,
            Emotion.NEUTRAL: 0.03,
            Emotion.SAD: 0.02,
        }
        mock_inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=150.5,
        )

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_inference

        # Override dependency
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(True, None)):
            response = client.post(
                "/v2/inference",
                files={"file": ("test.wav", sample_audio_bytes, "audio/wav")},
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "v4"
        assert data["prediction"]["emotion"] == "happy"
        assert data["prediction"]["confidence"] == 0.85

    def test_post_inference_with_audio_features(self, client, sample_audio_bytes):
        """Test inference with audio_features query parameter."""
        # Arrange
        all_probabilities = {
            Emotion.ANGRY: 0.05,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.02,
            Emotion.HAPPY: 0.85,
            Emotion.NEUTRAL: 0.03,
            Emotion.SAD: 0.02,
        }
        mock_inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=150.5,
        )

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_inference

        # Override dependency
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(True, None)):
            response = client.post(
                "/v2/inference?audio_features=true",
                files={"file": ("test.wav", sample_audio_bytes, "audio/wav")},
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "v4"
        assert data["prediction"]["emotion"] == "happy"

    def test_post_inference_invalid_audio(self, client, sample_audio_bytes):
        """Test inference with invalid audio file."""
        # Arrange
        mock_use_case = MagicMock()

        # Override dependency
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(False, "Invalid file format")):
            response = client.post(
                "/v2/inference",
                files={"file": ("test.txt", b"not audio", "text/plain")},
            )

        # Assert
        assert response.status_code == 400
        assert "validation failed" in response.json()["detail"].lower()

    def test_post_inference_error_handling(self, client, sample_audio_bytes):
        """Test error handling when inference fails."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.side_effect = Exception("Model inference failed")

        # Override dependency
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(True, None)):
            response = client.post(
                "/v2/inference",
                files={"file": ("test.wav", sample_audio_bytes, "audio/wav")},
            )

        # Assert
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_old_endpoint_still_works(self, client, sample_audio_bytes):
        """Test that old /latest endpoint still works for backward compatibility."""
        # Arrange
        all_probabilities = {
            Emotion.ANGRY: 0.05,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.02,
            Emotion.HAPPY: 0.85,
            Emotion.NEUTRAL: 0.03,
            Emotion.SAD: 0.02,
        }
        mock_inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=150.5,
        )

        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_inference

        # Override dependency
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(True, None)):
            response = client.post(
                "/v2/inference/latest",
                files={"file": ("test.wav", sample_audio_bytes, "audio/wav")},
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "v4"
        assert data["prediction"]["emotion"] == "happy"
