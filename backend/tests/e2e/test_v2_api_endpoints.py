"""
End-to-End tests for v2 Model API Endpoints.

This test suite validates the complete API flow for v2 model endpoints:
- POST /v1/infer/local/2 - Inference with v2 model
- File upload handling
- Response structure validation
- Error handling through API layer
- Integration with FastAPI test client

Focus: API flow correctness, NOT model accuracy.
"""

import io
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def crema_d_audio_path():
    """Path to CREMA-D dataset."""
    return Path("/Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition/data/AudioWAV")


@pytest.fixture
def crema_d_sample(crema_d_audio_path):
    """Load a real CREMA-D audio sample."""
    audio_files = list(crema_d_audio_path.glob("*.wav"))

    if not audio_files:
        pytest.skip("CREMA-D audio files not available")

    audio_file = audio_files[0]

    with open(audio_file, 'rb') as f:
        audio_bytes = f.read()

    return audio_bytes, audio_file.name


@pytest.mark.e2e
class TestV2InferenceEndpoint:
    """Test POST /v1/infer/local/2 endpoint."""

    def test_v2_inference_endpoint_returns_200(self, client, sample_audio_file):
        """Test that v2 inference endpoint returns 200 OK."""
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)

        assert response.status_code == 200, \
            f"Expected 200, got {response.status_code}: {response.text}"

    def test_v2_inference_response_structure(self, client, sample_audio_file):
        """Test that response has correct structure."""
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)
        data = response.json()

        # Check top-level fields
        assert "version" in data, "Response should have version field"
        assert "prediction" in data, "Response should have prediction field"
        assert "model_info" in data, "Response should have model_info field"
        assert "processing_time_ms" in data, "Response should have processing_time_ms field"

    def test_v2_inference_prediction_structure(self, client, sample_audio_file):
        """Test that prediction object has correct structure."""
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)
        data = response.json()

        prediction = data["prediction"]

        # Check prediction fields
        assert "emotion" in prediction, "Prediction should have emotion field"
        assert "confidence" in prediction, "Prediction should have confidence field"
        assert "all_probabilities" in prediction, \
            "Prediction should have all_probabilities field"

    def test_v2_inference_model_info_structure(self, client, sample_audio_file):
        """Test that model_info object has correct structure."""
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)
        data = response.json()

        model_info = data["model_info"]

        assert "type" in model_info, "model_info should have type field"
        assert "features_used" in model_info, "model_info should have features_used field"

    def test_v2_inference_version_correct(self, client, sample_audio_file):
        """Test that response version is '2'."""
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)
        data = response.json()

        assert data["version"] == "2", \
            f"Version should be '2', got {data['version']}"

    def test_v2_inference_emotion_valid(self, client, sample_audio_file):
        """Test that predicted emotion is one of the 6 valid classes."""
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)
        data = response.json()

        emotion = data["prediction"]["emotion"]
        valid_emotions = ["angry", "disgust", "fear", "happy", "neutral", "sad"]

        assert emotion in valid_emotions, \
            f"Emotion '{emotion}' should be one of {valid_emotions}"

    def test_v2_inference_confidence_valid_range(self, client, sample_audio_file):
        """Test that confidence is in valid [0, 1] range."""
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)
        data = response.json()

        confidence = data["prediction"]["confidence"]

        assert isinstance(confidence, (int, float)), "Confidence should be numeric"
        assert 0.0 <= confidence <= 1.0, \
            f"Confidence {confidence} should be in range [0, 1]"

    def test_v2_inference_all_probabilities_valid(self, client, sample_audio_file):
        """Test that all_probabilities contains emotion classes.

        Note: v2 model uses SVC with probability=False, so it only returns
        the predicted class with confidence 1.0. This is expected behavior.
        """
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)
        data = response.json()

        all_probs = data["prediction"]["all_probabilities"]

        # v2 model doesn't have probability enabled, so it only returns the predicted class
        assert isinstance(all_probs, dict), "all_probabilities should be a dict"
        assert len(all_probs) >= 1, "Should have at least one probability"

        # The predicted emotion should be in all_probabilities
        predicted_emotion = data["prediction"]["emotion"]
        assert predicted_emotion in all_probs, \
            f"Predicted emotion {predicted_emotion} should be in all_probabilities"

        # Check all probabilities are valid
        for emotion, prob in all_probs.items():
            assert isinstance(prob, (int, float)), \
                f"Probability for {emotion} should be numeric"
            assert 0.0 <= prob <= 1.0, \
                f"Probability for {emotion} ({prob}) should be in [0, 1]"

    def test_v2_inference_probabilities_sum_to_one(self, client, sample_audio_file):
        """Test that all probabilities sum to approximately 1.0."""
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)
        data = response.json()

        all_probs = data["prediction"]["all_probabilities"]
        prob_sum = sum(all_probs.values())

        assert 0.99 <= prob_sum <= 1.01, \
            f"Probabilities should sum to ~1.0, got {prob_sum}"

    def test_v2_inference_model_type_correct(self, client, sample_audio_file):
        """Test that model type is Pipeline."""
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)
        data = response.json()

        model_type = data["model_info"]["type"]
        assert model_type == "Pipeline (StandardScaler + RFE + SVC)", \
            f"Model type should be Pipeline, got {model_type}"

    def test_v2_inference_features_used_correct(self, client, sample_audio_file):
        """Test that features_used is 78."""
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)
        data = response.json()

        features_used = data["model_info"]["features_used"]
        assert features_used == 78, \
            f"Features used should be 78, got {features_used}"

    def test_v2_inference_processing_time_reasonable(self, client, sample_audio_file):
        """Test that processing time is reasonable (< 10 seconds)."""
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)
        data = response.json()

        processing_time_ms = data["processing_time_ms"]

        assert isinstance(processing_time_ms, (int, float)), \
            "Processing time should be numeric"
        assert processing_time_ms > 0, "Processing time should be positive"
        assert processing_time_ms < 10000, \
            f"Processing time {processing_time_ms}ms should be < 10000ms (10s)"


@pytest.mark.e2e
@pytest.mark.audio
class TestV2RealAudioEndpoint:
    """Test endpoint with real CREMA-D audio files."""

    def test_v2_inference_with_real_crema_d_audio(self, client, crema_d_sample):
        """Test inference with real CREMA-D audio file."""
        audio_bytes, filename = crema_d_sample

        files = {
            'file': (filename, io.BytesIO(audio_bytes), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)

        assert response.status_code == 200, \
            f"Real audio should return 200, got {response.status_code}"

        data = response.json()
        assert "prediction" in data, "Should have prediction for real audio"
        assert data["prediction"]["emotion"] in \
               ["angry", "disgust", "fear", "happy", "neutral", "sad"], \
            "Should predict valid emotion for real audio"

    def test_v2_inference_multiple_real_files(self, client, crema_d_audio_path):
        """Test inference with multiple real audio files."""
        audio_files = list(crema_d_audio_path.glob("*.wav"))[:3]

        if len(audio_files) < 2:
            pytest.skip("Need at least 2 CREMA-D audio files")

        for audio_file in audio_files:
            with open(audio_file, 'rb') as f:
                audio_bytes = f.read()

            files = {
                'file': (audio_file.name, io.BytesIO(audio_bytes), 'audio/wav')
            }

            response = client.post('/v1/infer/local/2', files=files)

            assert response.status_code == 200, \
                f"File {audio_file.name} should return 200"

            data = response.json()
            assert "prediction" in data, \
                f"File {audio_file.name} should have prediction"
            assert data["prediction"]["emotion"] in \
                   ["angry", "disgust", "fear", "happy", "neutral", "sad"]


@pytest.mark.e2e
class TestV2ErrorHandling:
    """Test error handling through API endpoints."""

    def test_v2_inference_with_corrupted_file(self, client, corrupted_audio_file):
        """Test that corrupted file returns appropriate error."""
        files = {
            'file': ('corrupted.wav', io.BytesIO(corrupted_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)

        # Should return error status (400 or 500)
        assert response.status_code in [400, 500], \
            f"Corrupted file should return error, got {response.status_code}"

    def test_v2_inference_with_empty_file(self, client):
        """Test that empty file returns appropriate error."""
        files = {
            'file': ('empty.wav', io.BytesIO(b''), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)

        # Should return error status
        assert response.status_code in [400, 422, 500], \
            f"Empty file should return error, got {response.status_code}"

    def test_v2_inference_without_file(self, client):
        """Test that request without file returns 422 validation error."""
        response = client.post('/v1/infer/local/2')

        assert response.status_code == 422, \
            f"Request without file should return 422, got {response.status_code}"

    def test_v2_inference_with_invalid_file_type(self, client):
        """Test that invalid file type is handled appropriately."""
        files = {
            'file': ('test.txt', io.BytesIO(b'This is text, not audio'), 'text/plain')
        }

        response = client.post('/v1/infer/local/2', files=files)

        # Should return error status (400 or 422)
        assert response.status_code in [400, 422, 500], \
            f"Invalid file type should return error, got {response.status_code}"


@pytest.mark.e2e
class TestV2FileFormatSupport:
    """Test support for different audio file formats."""

    def test_v2_inference_with_wav_file(self, client, sample_audio_file):
        """Test inference with WAV file."""
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/2', files=files)
        assert response.status_code == 200, "WAV file should work"

    def test_v2_inference_with_different_extensions(self, client, sample_audio_file):
        """Test that different filename extensions are accepted."""
        extensions = [
            ('test.wav', 'audio/wav'),
            ('test.mp3', 'audio/mpeg'),
            ('test.m4a', 'audio/mp4'),
        ]

        for filename, content_type in extensions:
            files = {
                'file': (filename, io.BytesIO(sample_audio_file), content_type)
            }

            response = client.post('/v1/infer/local/2', files=files)

            # Should at least not crash (might return 200 or error depending on actual content)
            assert response.status_code in [200, 400, 500], \
                f"Extension {filename} should be handled"


@pytest.mark.e2e
class TestV2EndpointConsistency:
    """Test endpoint consistency and reliability."""

    def test_v2_multiple_requests_same_audio(self, client, sample_audio_file):
        """Test that multiple requests with same audio produce consistent results."""
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        responses = []
        for _ in range(3):
            response = client.post('/v1/infer/local/2', files=files)
            assert response.status_code == 200
            responses.append(response.json())

        # All responses should have same emotion
        emotions = [r["prediction"]["emotion"] for r in responses]
        assert len(set(emotions)) == 1, \
            f"Emotion should be consistent, got {emotions}"

        # All responses should have same confidence
        confidences = [r["prediction"]["confidence"] for r in responses]
        assert len(set(confidences)) == 1, \
            f"Confidence should be consistent, got {confidences}"

    def test_v2_concurrent_requests_work(self, client, sample_audio_file):
        """Test that endpoint can handle multiple sequential requests."""
        for i in range(5):
            files = {
                'file': (f'test_{i}.wav', io.BytesIO(sample_audio_file), 'audio/wav')
            }

            response = client.post('/v1/infer/local/2', files=files)

            assert response.status_code == 200, \
                f"Request {i} should succeed"

            data = response.json()
            assert "prediction" in data, f"Request {i} should have prediction"


@pytest.mark.e2e
class TestV2ModelInfoEndpoints:
    """Test model info endpoints for v2."""

    def test_get_model_info_v2(self, client):
        """Test GET /v1/models/local/2/info endpoint."""
        response = client.get('/v1/models/local/2/info')

        assert response.status_code == 200, \
            f"Model info should return 200, got {response.status_code}"

        data = response.json()

        # Check required fields
        assert "version" in data, "Should have version field"
        assert "model_type" in data, "Should have model_type field"
        assert "feature_dimension" in data, "Should have feature_dimension field"
        assert "classes" in data, "Should have classes field"

        # Check values
        assert data["version"] == "2", "Version should be '2'"
        assert data["model_type"] == "Pipeline (StandardScaler + RFE + SVC)", \
            "Model type should be Pipeline"
        assert data["feature_dimension"] == 78, "Feature dimension should be 78"
        assert len(data["classes"]) == 6, "Should have 6 classes"

    def test_list_models_includes_v2(self, client):
        """Test GET /v1/models/local/list includes v2."""
        response = client.get('/v1/models/local/list')

        assert response.status_code == 200, \
            f"Model list should return 200, got {response.status_code}"

        data = response.json()

        assert "versions" in data, "Should have versions field"
        assert "total_models" in data, "Should have total_models field"
        assert "latest_version" in data, "Should have latest_version field"

        # Check v2 is in the list
        version_numbers = [v["version"] for v in data["versions"]]
        assert "2" in version_numbers, "v2 should be in versions list"

        # Find v2 in the list
        v2_info = next((v for v in data["versions"] if v["version"] == "2"), None)
        assert v2_info is not None, "v2 info should be in list"
        assert v2_info["model_type"] == "Pipeline (StandardScaler + RFE + SVC)"
        assert v2_info["feature_dimension"] == 78


@pytest.mark.e2e
class TestV2VsV1ComparisonEndpoint:
    """Test comparison between v1 and v2 endpoints."""

    def test_same_audio_different_versions_both_work(self, client, sample_audio_file):
        """Test that same audio works with both v1 and v2 endpoints."""
        files_v1 = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }
        files_v2 = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response_v1 = client.post('/v1/infer/local/1', files=files_v1)
        response_v2 = client.post('/v1/infer/local/2', files=files_v2)

        # Both should succeed
        assert response_v1.status_code == 200, "v1 endpoint should work"
        assert response_v2.status_code == 200, "v2 endpoint should work"

        # Both should have valid predictions
        data_v1 = response_v1.json()
        data_v2 = response_v2.json()

        valid_emotions = ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        assert data_v1["prediction"]["emotion"] in valid_emotions
        assert data_v2["prediction"]["emotion"] in valid_emotions

    def test_v2_uses_different_features_than_v1(self, client, sample_audio_file):
        """Test that v2 uses different feature count than v1."""
        files_v1 = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }
        files_v2 = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response_v1 = client.post('/v1/infer/local/1', files=files_v1)
        response_v2 = client.post('/v1/infer/local/2', files=files_v2)

        data_v1 = response_v1.json()
        data_v2 = response_v2.json()

        # Different feature dimensions
        assert data_v1["model_info"]["features_used"] == 162, "v1 should use 162 features"
        assert data_v2["model_info"]["features_used"] == 78, "v2 should use 78 features"

    def test_v2_has_different_model_type_than_v1(self, client, sample_audio_file):
        """Test that v2 has different model type than v1."""
        files_v1 = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }
        files_v2 = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response_v1 = client.post('/v1/infer/local/1', files=files_v1)
        response_v2 = client.post('/v1/infer/local/2', files=files_v2)

        data_v1 = response_v1.json()
        data_v2 = response_v2.json()

        # Different model types
        assert data_v1["model_info"]["type"] == "DecisionTreeClassifier"
        assert data_v2["model_info"]["type"] == "Pipeline (StandardScaler + RFE + SVC)"


@pytest.mark.e2e
class TestV2LatestEndpoint:
    """Test latest model endpoint (when v2 is latest)."""

    def test_latest_endpoint_returns_v2_or_higher(self, client, sample_audio_file):
        """Test POST /v1/infer/local/latest endpoint returns v2 or higher."""
        files = {
            'file': ('test.wav', io.BytesIO(sample_audio_file), 'audio/wav')
        }

        response = client.post('/v1/infer/local/latest', files=files)

        assert response.status_code == 200, \
            f"Latest endpoint should work, got {response.status_code}"

        data = response.json()

        # Should have same structure as versioned endpoint
        assert "version" in data
        assert "prediction" in data
        assert "model_info" in data

        # Version should be 2 or higher
        version = int(data["version"])
        assert version >= 2, \
            f"Latest version should be >= 2, got {version}"
