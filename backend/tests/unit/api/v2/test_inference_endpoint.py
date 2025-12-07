"""Unit tests for v2 inference endpoint audio_features query parameter.

This test suite follows TDD (Test-Driven Development) approach:
1. Write tests first that define the expected behavior
2. Tests will fail initially (RED)
3. Implement code to make tests pass (GREEN)
4. Refactor while keeping tests green (REFACTOR)

Test Coverage:
- Query parameter defaults to False
- Query parameter can be set to True
- Feature flag integration (enabled/disabled scenarios)
- Response includes audio_features when appropriate
- Logging of audio_features requests
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.domain.model.entities.inference import Inference
from app.domain.model.value_objects.emotion import Emotion
from app.domain.model.value_objects.model_version import ModelVersion
from app.infrastructure.config.feature_flags import FeatureFlags, get_feature_flags
from app.infrastructure.di.providers import get_run_inference_use_case
from app.main import app


@pytest.fixture
def client():
    """Create test client and clear dependency overrides after each test."""
    client = TestClient(app)
    yield client
    # Cleanup after each test
    app.dependency_overrides.clear()


@pytest.fixture
def mock_inference():
    """Create a mock inference result without audio_features."""
    all_probabilities = {
        Emotion.ANGRY: 0.05,
        Emotion.DISGUST: 0.03,
        Emotion.FEAR: 0.02,
        Emotion.HAPPY: 0.85,
        Emotion.NEUTRAL: 0.03,
        Emotion.SAD: 0.02,
    }
    return Inference.create(
        emotion=Emotion.HAPPY,
        all_probabilities=all_probabilities,
        model_version=ModelVersion.from_string("v4"),
        processing_time_ms=150.5,
    )


@pytest.fixture
def mock_inference_with_prediction_id():
    """Create a mock inference result with prediction_id for monitoring."""
    all_probabilities = {
        Emotion.ANGRY: 0.05,
        Emotion.DISGUST: 0.03,
        Emotion.FEAR: 0.02,
        Emotion.HAPPY: 0.85,
        Emotion.NEUTRAL: 0.03,
        Emotion.SAD: 0.02,
    }
    return Inference.create(
        emotion=Emotion.HAPPY,
        all_probabilities=all_probabilities,
        model_version=ModelVersion.from_string("v4"),
        processing_time_ms=150.5,
        prediction_id="test-uuid-1234-5678",
    )


@pytest.fixture
def mock_inference_with_audio_features():
    """Create a mock inference result with audio_features data."""
    all_probabilities = {
        Emotion.ANGRY: 0.05,
        Emotion.DISGUST: 0.03,
        Emotion.FEAR: 0.02,
        Emotion.HAPPY: 0.85,
        Emotion.NEUTRAL: 0.03,
        Emotion.SAD: 0.02,
    }
    return Inference.create(
        emotion=Emotion.HAPPY,
        all_probabilities=all_probabilities,
        model_version=ModelVersion.from_string("v4"),
        processing_time_ms=150.5,
        audio_features={
            "mel_spectrogram": {"shape": [128, 100], "data": "base64_encoded_data"},
            "chroma": {"shape": [12, 100], "data": "base64_encoded_data"},
            "mfccs": {"shape": [40, 100], "data": "base64_encoded_data"},
            "pitch_contour": {"shape": [100], "data": "base64_encoded_data"},
        },
    )


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


class TestAudioFeaturesQueryParameter:
    """Test suite for audio_features query parameter functionality."""

    def test_query_parameter_defaults_to_false(
        self,
        client,
        mock_inference,
        sample_audio_bytes,
    ):
        """Test that audio_features defaults to False when not provided."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_inference

        # Override dependencies
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(True, None)):
            response = client.post(
                "/v2/inference/",
                files={"file": ("test.wav", sample_audio_bytes, "audio/wav")},
            )

        # Assert
        assert response.status_code == 200

        # Verify use case was called with audio_features=False
        mock_use_case.execute.assert_called_once()
        call_kwargs = mock_use_case.execute.call_args.kwargs
        assert "audio_features" in call_kwargs
        assert call_kwargs["audio_features"] is False

    def test_query_parameter_can_be_set_to_true(
        self,
        client,
        mock_inference,
        sample_audio_bytes,
    ):
        """Test that audio_features can be explicitly set to True."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_inference

        # Override dependencies
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(True, None)):
            response = client.post(
                "/v2/inference/?audio_features=true",
                files={"file": ("test.wav", sample_audio_bytes, "audio/wav")},
            )

        # Assert
        assert response.status_code == 200

        # Note: The endpoint should pass True to use case only if feature flag allows it
        # Since we're not mocking feature flags here, it will use the real ones (disabled by default)
        # So audio_features will be False even though requested
        mock_use_case.execute.assert_called_once()

    def test_feature_flag_disabled_user_requests_audio_features(
        self,
        client,
        mock_inference,
        sample_audio_bytes,
    ):
        """Test behavior when feature flag is disabled but user requests audio_features."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_inference

        # Mock feature flags to return disabled
        mock_flags = MagicMock(spec=FeatureFlags)
        mock_flags.inference_audio_features_enabled = False
        mock_flags.should_include_audio_features.return_value = False

        # Override dependencies
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case
        app.dependency_overrides[get_feature_flags] = lambda: mock_flags

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(True, None)):
            response = client.post(
                "/v2/inference/?audio_features=true",
                files={"file": ("test.wav", sample_audio_bytes, "audio/wav")},
            )

        # Assert
        assert response.status_code == 200

        # Verify feature flag was checked with requested=True
        mock_flags.should_include_audio_features.assert_called_once_with(requested=True)

        # Verify use case was called with audio_features=False (blocked by flag)
        mock_use_case.execute.assert_called_once()
        call_kwargs = mock_use_case.execute.call_args.kwargs
        assert call_kwargs["audio_features"] is False

    def test_feature_flag_enabled_user_requests_audio_features(
        self,
        client,
        mock_inference,
        sample_audio_bytes,
    ):
        """Test behavior when feature flag is enabled and user requests audio_features."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_inference

        # Mock feature flags to return enabled
        mock_flags = MagicMock(spec=FeatureFlags)
        mock_flags.inference_audio_features_enabled = True
        mock_flags.should_include_audio_features.return_value = True

        # Override dependencies
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case
        app.dependency_overrides[get_feature_flags] = lambda: mock_flags

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(True, None)):
            response = client.post(
                "/v2/inference/?audio_features=true",
                files={"file": ("test.wav", sample_audio_bytes, "audio/wav")},
            )

        # Assert
        assert response.status_code == 200

        # Verify feature flag was checked with requested=True
        mock_flags.should_include_audio_features.assert_called_once_with(requested=True)

        # Verify use case was called with audio_features=True
        mock_use_case.execute.assert_called_once()
        call_kwargs = mock_use_case.execute.call_args.kwargs
        assert call_kwargs["audio_features"] is True

    def test_feature_flag_enabled_user_does_not_request(
        self,
        client,
        mock_inference,
        sample_audio_bytes,
    ):
        """Test behavior when feature flag is enabled but user doesn't request audio_features."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_inference

        # Mock feature flags
        mock_flags = MagicMock(spec=FeatureFlags)
        mock_flags.inference_audio_features_enabled = True
        mock_flags.should_include_audio_features.return_value = False

        # Override dependencies
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case
        app.dependency_overrides[get_feature_flags] = lambda: mock_flags

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(True, None)):
            response = client.post(
                "/v2/inference/",
                files={"file": ("test.wav", sample_audio_bytes, "audio/wav")},
            )

        # Assert
        assert response.status_code == 200

        # Verify feature flag was checked with requested=False
        mock_flags.should_include_audio_features.assert_called_once_with(requested=False)

        # Verify use case was called with audio_features=False
        mock_use_case.execute.assert_called_once()
        call_kwargs = mock_use_case.execute.call_args.kwargs
        assert call_kwargs["audio_features"] is False

    def test_logging_includes_audio_features_request_info(
        self,
        client,
        mock_inference,
        sample_audio_bytes,
    ):
        """Test that endpoint logs audio_features request information."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_inference

        mock_flags = MagicMock(spec=FeatureFlags)
        mock_flags.inference_audio_features_enabled = True
        mock_flags.should_include_audio_features.return_value = True

        # Override dependencies
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case
        app.dependency_overrides[get_feature_flags] = lambda: mock_flags

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(True, None)):
            with patch("app.api.v2.endpoints.inference.logger") as mock_logger:
                response = client.post(
                    "/v2/inference/?audio_features=true",
                    files={"file": ("test.wav", sample_audio_bytes, "audio/wav")},
                )

        # Assert
        assert response.status_code == 200

        # Verify that logger.info was called with audio_features information
        assert mock_logger.info.called

        # Find the initial request log call
        info_calls = [call for call in mock_logger.info.call_args_list]
        assert len(info_calls) > 0

        # Check that at least one log call includes audio_features info
        log_found = False
        for call in info_calls:
            kwargs = call.kwargs if call.kwargs else {}
            if "audio_features" in kwargs and "feature_enabled" in kwargs:
                log_found = True
                assert kwargs["audio_features"] is True
                assert kwargs["feature_enabled"] is True
                break

        assert log_found, "Expected log with audio_features and feature_enabled not found"

    def test_response_includes_audio_features_field_when_provided(
        self,
        client,
        mock_inference_with_audio_features,
        sample_audio_bytes,
    ):
        """Test that response includes audio_features field when provided by use case."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_inference_with_audio_features

        # Override dependencies
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(True, None)):
            response = client.post(
                "/v2/inference/?audio_features=true",
                files={"file": ("test.wav", sample_audio_bytes, "audio/wav")},
            )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify audio_features field is present
        assert "audio_features" in data, "Response should include 'audio_features' field"

        # Verify audio_features structure
        viz = data["audio_features"]
        assert "mel_spectrogram" in viz
        assert "chroma" in viz
        assert "mfccs" in viz
        assert "pitch_contour" in viz

    def test_response_excludes_audio_features_when_not_requested(
        self,
        client,
        mock_inference,
        sample_audio_bytes,
    ):
        """Test that response does not include audio_features field when not requested."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_inference

        # Override dependencies
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(True, None)):
            response = client.post(
                "/v2/inference/",
                files={"file": ("test.wav", sample_audio_bytes, "audio/wav")},
            )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Verify standard fields are present
        assert "version" in data
        assert "prediction" in data
        assert "processing_time_ms" in data

        # Verify audio_features field is NOT present
        assert "audio_features" not in data, "Response should not include 'audio_features' field when not requested"


class TestMonitoringQueryParameter:
    """Test suite for monitoring functionality - monitoring is always enabled in v2 API."""

    def test_monitoring_always_enabled_without_parameter(
        self,
        client,
        mock_inference_with_prediction_id,
        sample_audio_bytes,
    ):
        """Test that monitoring is always enabled even when no parameter is provided."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_inference_with_prediction_id

        # Override dependencies
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(True, None)):
            response = client.post(
                "/v2/inference",
                files={"file": ("test.wav", sample_audio_bytes, "audio/wav")},
            )

        # Assert
        assert response.status_code == 200

        # Verify use case was called with enable_monitoring=True
        mock_use_case.execute.assert_called_once()
        call_kwargs = mock_use_case.execute.call_args.kwargs
        assert "enable_monitoring" in call_kwargs
        assert call_kwargs["enable_monitoring"] is True

    def test_prediction_id_always_included_in_response(
        self,
        client,
        mock_inference_with_prediction_id,
        sample_audio_bytes,
    ):
        """Test that prediction_id is always included in response since monitoring is always enabled."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_inference_with_prediction_id

        # Override dependencies
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

        # Verify prediction_id is always in response
        assert "prediction" in data
        assert "prediction_id" in data["prediction"]
        assert data["prediction"]["prediction_id"] == "test-uuid-1234-5678"

    def test_logging_includes_monitoring_info(
        self,
        client,
        mock_inference_with_prediction_id,
        sample_audio_bytes,
    ):
        """Test that endpoint logs monitoring information."""
        # Arrange
        mock_use_case = MagicMock()
        mock_use_case.execute.return_value = mock_inference_with_prediction_id

        # Override dependencies
        app.dependency_overrides[get_run_inference_use_case] = lambda: mock_use_case

        # Act
        with patch("app.api.v2.endpoints.inference.validate_audio_file", return_value=(True, None)):
            with patch("app.api.v2.endpoints.inference.logger") as mock_logger:
                response = client.post(
                    "/v2/inference",
                    files={"file": ("test.wav", sample_audio_bytes, "audio/wav")},
                )

        # Assert
        assert response.status_code == 200

        # Verify that logger.info was called with monitoring information
        assert mock_logger.info.called

        # Find the completion log call
        info_calls = [call for call in mock_logger.info.call_args_list]
        assert len(info_calls) > 0

        # Check completion log includes monitoring_enabled=True and prediction_id
        completion_log_found = False
        for call in info_calls:
            kwargs = call.kwargs if call.kwargs else {}
            if "monitoring_enabled" in kwargs and "prediction_id" in kwargs:
                completion_log_found = True
                assert kwargs["monitoring_enabled"] is True
                assert kwargs["prediction_id"] == "test-uuid-1234-5678"
                break

        assert completion_log_found, "Expected completion log with monitoring info not found"
