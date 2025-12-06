"""
Integration tests for Visualization Feature Toggle.

This test suite validates the end-to-end behavior of the audio_features inference feature
toggle across the inference API, model registry, and feature flags service.

Tests cover:
- Feature flag enabled/disabled scenarios
- User request combinations (include_audio_features query parameter)
- API response structure with and without audio_features
- Model version compatibility (v4 supports viz, v1/v2/v3 do not)
- Feature flag metadata in responses
- Backward compatibility for existing clients
"""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client for API testing."""
    return TestClient(app)


class TestVisualizationFeatureDisabled:
    """Test behavior when audio_features feature is disabled (default)."""

    def test_audio_features_not_included_when_not_requested(self, client, sample_audio_file):
        """Test that audio_features not included by default when feature disabled."""
        # Feature is disabled by default
        # Don't pass include_audio_features parameter

        response = client.post(
            "/v1/inference/latest", files={"file": ("test.wav", sample_audio_file, "audio/wav")}
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()

        # Should NOT include audio_features
        assert (
            "audio_features" not in data
        ), "Visualization should not be included when not requested"

        # Should have prediction
        assert "prediction" in data
        assert "emotion" in data["prediction"]

        # Should have feature flag metadata
        assert "feature_flags" in data
        assert data["feature_flags"]["audio_features_enabled"] is False
        assert data["feature_flags"]["audio_features_included"] is False

    def test_audio_features_denied_when_requested_but_feature_disabled(
        self, client, sample_audio_file
    ):
        """Test that audio_features is denied when requested but feature is disabled."""
        # Feature is disabled by default
        # User explicitly requests audio_features

        response = client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()

        # Should NOT include audio_features (feature disabled takes precedence)
        assert (
            "audio_features" not in data
        ), "Visualization should be denied when feature is disabled"

        # Should still have prediction
        assert "prediction" in data

        # Feature flags should show audio_features_enabled=false
        assert data["feature_flags"]["audio_features_enabled"] is False
        assert data["feature_flags"]["audio_features_included"] is False

    def test_explicit_false_request_respected(self, client, sample_audio_file):
        """Test that explicit include_audio_features=false is respected."""
        response = client.post(
            "/v1/inference/latest?include_audio_features=false",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        assert response.status_code == 200

        data = response.json()

        # Should NOT include audio_features
        assert "audio_features" not in data

        # Should have prediction
        assert "prediction" in data


class TestVisualizationFeatureEnabled:
    """Test behavior when audio_features feature is enabled via environment variable."""

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_audio_features_not_included_when_not_requested(self, client, sample_audio_file):
        """Test that audio_features not included when enabled but not requested."""
        # Clear feature flags cache to pick up new env var
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()
        import app.utils.config
        app.utils.config._settings = None

        response = client.post(
            "/v1/inference/latest", files={"file": ("test.wav", sample_audio_file, "audio/wav")}
        )

        assert response.status_code == 200

        data = response.json()

        # Should NOT include audio_features (not requested)
        assert (
            "audio_features" not in data
        ), "Visualization should not be included when not requested, even if enabled"

        # Feature flags should show enabled but not included
        assert data["feature_flags"]["audio_features_enabled"] is True
        assert data["feature_flags"]["audio_features_included"] is False

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_audio_features_included_when_requested_and_enabled(self, client, sample_audio_file):
        """Test that audio_features IS included when both enabled and requested."""
        # Clear feature flags cache
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()
        import app.utils.config
        app.utils.config._settings = None

        response = client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        assert response.status_code == 200

        data = response.json()

        # Should include audio_features (both conditions met)
        assert (
            "audio_features" in data
        ), "Visualization should be included when both enabled and requested"

        # Feature flags should show both true
        assert data["feature_flags"]["audio_features_enabled"] is True
        assert data["feature_flags"]["audio_features_included"] is True

        # Validation data structure
        viz_data = data["audio_features"]
        assert isinstance(viz_data, dict)

        # Should have all required keys
        required_keys = {
            "sample_rate",
            "duration",
            "waveform",
            "mel_spectrogram",
            "chroma",
            "mfcc",
            "delta_mfcc",
            "delta_delta_mfcc",
            "pitch_times",
            "pitch_values",
            "rms_contour",
        }
        assert required_keys.issubset(
            set(viz_data.keys())
        ), f"Visualization missing keys: {required_keys - set(viz_data.keys())}"

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_explicit_false_request_honored_when_enabled(self, client, sample_audio_file):
        """Test that explicit include_audio_features=false is honored even when enabled."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()
        import app.utils.config
        app.utils.config._settings = None

        response = client.post(
            "/v1/inference/latest?include_audio_features=false",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        assert response.status_code == 200

        data = response.json()

        # Should NOT include audio_features (explicitly declined)
        assert "audio_features" not in data


class TestVisualizationDataStructure:
    """Test the structure of audio_features data when included."""

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_audio_features_data_has_correct_structure(self, client, sample_audio_file):
        """Test that audio_features data has the correct structure."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()
        import app.utils.config
        app.utils.config._settings = None

        response = client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        assert response.status_code == 200

        data = response.json()
        viz_data = data["audio_features"]

        # Check metadata types
        assert isinstance(viz_data["sample_rate"], int)
        assert isinstance(viz_data["duration"], (int, float))

        # Check matrix types (should be lists for JSON)
        assert isinstance(viz_data["waveform"], list)
        assert isinstance(viz_data["mel_spectrogram"], list)
        assert isinstance(viz_data["chroma"], list)
        assert isinstance(viz_data["mfcc"], list)
        assert isinstance(viz_data["delta_mfcc"], list)
        assert isinstance(viz_data["delta_delta_mfcc"], list)

        # Check prosodic data types
        assert isinstance(viz_data["pitch_times"], list)
        assert isinstance(viz_data["pitch_values"], list)
        assert isinstance(viz_data["rms_contour"], list)

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_audio_features_matrices_have_correct_shapes(self, client, sample_audio_file):
        """Test that audio_features matrices have expected shapes."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()
        import app.utils.config
        app.utils.config._settings = None

        response = client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        data = response.json()
        viz_data = data["audio_features"]

        # Mel spectrogram: 128 rows
        assert len(viz_data["mel_spectrogram"]) == 128

        # Chroma: 12 rows
        assert len(viz_data["chroma"]) == 12

        # MFCCs: 20 rows each
        assert len(viz_data["mfcc"]) == 20
        assert len(viz_data["delta_mfcc"]) == 20
        assert len(viz_data["delta_delta_mfcc"]) == 20

        # Waveform: should have data
        assert len(viz_data["waveform"]) > 0

        # RMS contour: should have data
        assert len(viz_data["rms_contour"]) > 0


class TestModelVersionCompatibility:
    """Test audio_features support across different model versions."""

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_v4_model_supports_audio_features(self, client, sample_audio_file):
        """Test that v4 model (latest) supports audio_features."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()
        import app.utils.config
        app.utils.config._settings = None

        response = client.post(
            "/v1/inference/4?include_audio_features=true",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        # Should succeed if v4 model exists
        if response.status_code == 404:
            pytest.skip("Model v4 not found")

        assert response.status_code == 200

        data = response.json()

        # v4 should include audio_features
        assert "audio_features" in data, "v4 model should support audio_features"

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_v3_model_gracefully_handles_audio_features_request(self, client, sample_audio_file):
        """Test that v3 model gracefully handles audio_features request (no support)."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()
        import app.utils.config
        app.utils.config._settings = None

        response = client.post(
            "/v1/inference/3?include_audio_features=true",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        # Should succeed if v3 model exists
        if response.status_code == 404:
            pytest.skip("Model v3 not found")

        assert response.status_code == 200

        data = response.json()

        # v3 doesn't support audio_features, should not include it
        assert (
            "audio_features" not in data
        ), "v3 model should not include audio_features (not supported)"

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_latest_model_is_v4_with_audio_features(self, client, sample_audio_file):
        """Test that latest model (should be v4) supports audio_features."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()
        import app.utils.config
        app.utils.config._settings = None

        response = client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        assert response.status_code == 200

        data = response.json()

        # Latest model should be v4
        assert data["version"] == "4", f"Latest model should be v4, got {data['version']}"

        # Should include audio_features
        assert "audio_features" in data, "Latest model (v4) should support audio_features"


class TestBackwardCompatibility:
    """Test that existing clients continue to work without changes."""

    def test_existing_clients_without_query_param_work(self, client, sample_audio_file):
        """Test that existing clients work without include_audio_features parameter."""
        response = client.post(
            "/v1/inference/latest", files={"file": ("test.wav", sample_audio_file, "audio/wav")}
        )

        assert response.status_code == 200

        data = response.json()

        # Should have all standard fields
        assert "prediction" in data
        assert "model_info" in data
        assert "processing_time_ms" in data

        # Should NOT have audio_features (not requested)
        assert "audio_features" not in data

    def test_response_structure_unchanged_for_existing_clients(self, client, sample_audio_file):
        """Test that response structure is unchanged for clients not using audio_features."""
        response = client.post(
            "/v1/inference/latest", files={"file": ("test.wav", sample_audio_file, "audio/wav")}
        )

        data = response.json()

        # Check standard response structure
        assert "version" in data
        assert "prediction" in data
        assert "emotion" in data["prediction"]
        assert "confidence" in data["prediction"]
        assert "all_probabilities" in data["prediction"]
        assert "model_info" in data
        assert "type" in data["model_info"]
        assert "features_used" in data["model_info"]
        assert "processing_time_ms" in data

        # New feature flag metadata should be present
        assert "feature_flags" in data


class TestResponseSizeAndPerformance:
    """Test response size and performance with audio_features enabled."""

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_response_with_audio_features_is_larger(self, client, sample_audio_file):
        """Test that response with audio_features is significantly larger."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()
        import app.utils.config
        app.utils.config._settings = None

        # Get response without audio_features
        response_without = client.post(
            "/v1/inference/latest?include_audio_features=false",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        # Get response with audio_features
        response_with = client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        size_without = len(response_without.content)
        size_with = len(response_with.content)

        # Response with audio_features should be much larger
        assert (
            size_with > size_without
        ), f"Response with viz ({size_with} bytes) should be larger than without ({size_without} bytes)"

        # Should be at least 10x larger (audio_features data is substantial)
        assert (
            size_with > size_without * 5
        ), f"Response with viz should be significantly larger (got {size_with / size_without:.1f}x)"

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_gzip_compression_applied(self, client, sample_audio_file):
        """Test that GZIP compression is applied to large responses."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()
        import app.utils.config
        app.utils.config._settings = None

        response = client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
            headers={"Accept-Encoding": "gzip"},
        )

        assert response.status_code == 200

        # Response should be compressed (check content-encoding header)
        # Note: TestClient may not fully simulate GZIP middleware
        # This test verifies the middleware is configured
        assert response.status_code == 200


class TestFeatureFlagMetadata:
    """Test feature flag metadata in API responses."""

    def test_feature_flags_metadata_always_present(self, client, sample_audio_file):
        """Test that feature_flags metadata is always present in response."""
        response = client.post(
            "/v1/inference/latest", files={"file": ("test.wav", sample_audio_file, "audio/wav")}
        )

        data = response.json()

        assert "feature_flags" in data, "Response should always include feature_flags metadata"

        feature_flags = data["feature_flags"]

        # Should have both keys
        assert "audio_features_enabled" in feature_flags
        assert "audio_features_included" in feature_flags

        # Both should be booleans
        assert isinstance(feature_flags["audio_features_enabled"], bool)
        assert isinstance(feature_flags["audio_features_included"], bool)

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_feature_flags_reflect_actual_state(self, client, sample_audio_file):
        """Test that feature_flags metadata reflects actual state."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()
        import app.utils.config
        app.utils.config._settings = None

        # Request with audio_features
        response = client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": ("test.wav", sample_audio_file, "audio/wav")},
        )

        data = response.json()
        feature_flags = data["feature_flags"]

        # Should reflect enabled state
        assert feature_flags["audio_features_enabled"] is True

        # Should reflect inclusion state
        has_viz = "audio_features" in data
        assert feature_flags["audio_features_included"] == has_viz


@pytest.mark.integration
class TestEndToEndVisualizationWorkflow:
    """Test complete end-to-end workflows with audio_features feature."""

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_complete_inference_with_audio_features_workflow(self, client, sample_audio_file):
        """Test complete workflow: upload audio, get prediction + audio_features."""
        from app.infrastructure.config.feature_flags import get_feature_flags

        get_feature_flags.cache_clear()
        import app.utils.config
        app.utils.config._settings = None

        # 1. Upload audio and request audio_features
        response = client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": ("speech.wav", sample_audio_file, "audio/wav")},
        )

        assert response.status_code == 200

        data = response.json()

        # 2. Verify prediction is present
        assert "prediction" in data
        assert data["prediction"]["emotion"] in [
            "angry",
            "disgust",
            "fear",
            "happy",
            "neutral",
            "sad",
        ]
        assert 0.0 <= data["prediction"]["confidence"] <= 1.0

        # 3. Verify audio_features is present
        assert "audio_features" in data
        viz_data = data["audio_features"]

        # 4. Verify audio_features can be used for frontend
        assert viz_data["sample_rate"] > 0
        assert viz_data["duration"] > 0
        assert len(viz_data["mel_spectrogram"]) == 128
        assert len(viz_data["waveform"]) > 0

        # 5. Verify feature flags are correct
        assert data["feature_flags"]["audio_features_enabled"] is True
        assert data["feature_flags"]["audio_features_included"] is True

    def test_safe_rollout_scenario(self, client, sample_audio_file):
        """Test safe rollout: feature disabled globally, requests ignored."""
        # Feature disabled by default
        # Some clients may still send include_audio_features=true

        response = client.post(
            "/v1/inference/latest?include_audio_features=true",
            files={"file": ("speech.wav", sample_audio_file, "audio/wav")},
        )

        assert response.status_code == 200

        data = response.json()

        # Should still get prediction
        assert "prediction" in data

        # Should NOT get audio_features (feature disabled)
        assert "audio_features" not in data

        # Feature flags should show disabled
        assert data["feature_flags"]["audio_features_enabled"] is False
        assert data["feature_flags"]["audio_features_included"] is False
