"""End-to-end test for v2/inference/latest endpoint.

This test verifies the complete inference workflow using the v2 clean architecture API:
1. Load a real audio file from the CREMA-D dataset
2. Send it to the v2/inference/latest endpoint
3. Verify the response structure and data types
4. Verify that the prediction is valid and contains expected fields
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(scope="module")
def sample_audio_file():
    """Load the first audio file from the CREMA-D dataset.

    File: 1001_DFA_ANG_XX.wav
    - Actor: 1001
    - Series: DFA (Dialogue-based emotional acting)
    - Emotion: ANG (Angry)
    - Level: XX (Unspecified intensity)
    """
    # Path relative to backend directory
    audio_path = Path(__file__).parents[3] / "data" / "AudioWAV" / "1001_DFA_ANG_XX.wav"

    if not audio_path.exists():
        pytest.skip(f"Audio file not found: {audio_path}")

    return audio_path


@pytest.mark.e2e
@pytest.mark.audio
@pytest.mark.api
def test_v2_inference_latest_endpoint_with_real_audio(client: TestClient, sample_audio_file: Path):
    """Test v2/inference/latest endpoint with real CREMA-D audio file.

    This E2E test verifies:
    1. Endpoint accepts audio file upload
    2. Returns 200 OK status
    3. Response contains all required fields
    4. Prediction emotion is one of the valid emotions
    5. Confidence score is between 0 and 1
    6. All emotion probabilities are present and sum to ~1.0
    7. Processing time is reported
    """
    # Arrange: Read audio file
    with open(sample_audio_file, "rb") as audio_file:
        audio_bytes = audio_file.read()

    # Act: Send POST request to v2/inference/latest
    response = client.post(
        "/v2/inference/latest",
        files={"file": ("1001_DFA_ANG_XX.wav", audio_bytes, "audio/wav")}
    )

    # Assert: Response status
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    # Assert: Response structure
    data = response.json()
    assert "version" in data, "Response missing 'version' field"
    assert "prediction" in data, "Response missing 'prediction' field"
    assert "processing_time_ms" in data, "Response missing 'processing_time_ms' field"

    # Assert: Version field
    assert data["version"] == "v4", f"Expected version 'v4', got {data['version']}"

    # Assert: Prediction structure
    prediction = data["prediction"]
    assert "emotion" in prediction, "Prediction missing 'emotion' field"
    assert "confidence" in prediction, "Prediction missing 'confidence' field"
    assert "all_probabilities" in prediction, "Prediction missing 'all_probabilities' field"

    # Assert: Valid emotion
    valid_emotions = {"angry", "disgust", "fear", "happy", "neutral", "sad"}
    predicted_emotion = prediction["emotion"]
    assert predicted_emotion in valid_emotions, (
        f"Invalid emotion '{predicted_emotion}', expected one of {valid_emotions}"
    )

    # Assert: Confidence score range
    confidence = prediction["confidence"]
    assert isinstance(confidence, float), f"Confidence should be float, got {type(confidence)}"
    assert 0.0 <= confidence <= 1.0, f"Confidence {confidence} not in range [0, 1]"

    # Assert: All emotion probabilities
    all_probabilities = prediction["all_probabilities"]
    assert isinstance(all_probabilities, dict), "all_probabilities should be a dict"
    assert len(all_probabilities) == 6, f"Expected 6 emotions, got {len(all_probabilities)}"

    # Verify all valid emotions are present
    for emotion in valid_emotions:
        assert emotion in all_probabilities, f"Missing emotion '{emotion}' in probabilities"
        prob = all_probabilities[emotion]
        assert isinstance(prob, float), f"Probability for {emotion} should be float, got {type(prob)}"
        assert 0.0 <= prob <= 1.0, f"Probability for {emotion} is {prob}, not in range [0, 1]"

    # Assert: Probabilities sum to approximately 1.0
    total_prob = sum(all_probabilities.values())
    assert 0.99 <= total_prob <= 1.01, (
        f"Probabilities sum to {total_prob}, expected ~1.0"
    )

    # Assert: Confidence matches highest probability
    max_prob_emotion = max(all_probabilities.items(), key=lambda x: x[1])
    assert max_prob_emotion[0] == predicted_emotion, (
        f"Predicted emotion '{predicted_emotion}' doesn't match highest probability emotion '{max_prob_emotion[0]}'"
    )
    assert abs(max_prob_emotion[1] - confidence) < 0.0001, (
        f"Confidence {confidence} doesn't match max probability {max_prob_emotion[1]}"
    )

    # Assert: Processing time
    processing_time_ms = data["processing_time_ms"]
    assert isinstance(processing_time_ms, (int, float)), (
        f"processing_time_ms should be numeric, got {type(processing_time_ms)}"
    )
    assert processing_time_ms > 0, f"processing_time_ms should be positive, got {processing_time_ms}"
    assert processing_time_ms < 10000, (
        f"processing_time_ms {processing_time_ms}ms seems too high (>10s)"
    )

    # Log the results for visibility
    print(f"\n✅ E2E Test Passed - v2/inference/latest")
    print(f"   Audio File: {sample_audio_file.name}")
    print(f"   Predicted Emotion: {predicted_emotion}")
    print(f"   Confidence: {confidence:.4f}")
    print(f"   Processing Time: {processing_time_ms:.2f}ms")
    print(f"   Model Version: {data['version']}")
    print(f"   All Probabilities:")
    for emotion, prob in sorted(all_probabilities.items(), key=lambda x: x[1], reverse=True):
        print(f"     - {emotion}: {prob:.4f}")


@pytest.mark.e2e
@pytest.mark.api
def test_v2_inference_latest_endpoint_invalid_file(client: TestClient):
    """Test v2/inference/latest endpoint with invalid file.

    Verifies that the endpoint properly handles invalid input.
    """
    # Arrange: Create invalid audio data
    invalid_audio = b"not a valid audio file"

    # Act: Send POST request with invalid audio
    response = client.post(
        "/v2/inference/latest",
        files={"file": ("invalid.wav", invalid_audio, "audio/wav")}
    )

    # Assert: Should return 400 Bad Request
    assert response.status_code == 400, (
        f"Expected 400 for invalid audio, got {response.status_code}"
    )

    # Assert: Error message present
    data = response.json()
    assert "detail" in data, "Error response should contain 'detail' field"
    assert isinstance(data["detail"], str), "Error detail should be a string"
    assert len(data["detail"]) > 0, "Error detail should not be empty"

    print(f"\n✅ Invalid file handling test passed")
    print(f"   Status Code: {response.status_code}")
    print(f"   Error Detail: {data['detail']}")


@pytest.mark.e2e
@pytest.mark.api
def test_v2_inference_latest_endpoint_missing_file(client: TestClient):
    """Test v2/inference/latest endpoint without uploading a file.

    Verifies that the endpoint requires a file to be uploaded.
    """
    # Act: Send POST request without file
    response = client.post("/v2/inference/latest")

    # Assert: Should return 422 Unprocessable Entity
    assert response.status_code == 422, (
        f"Expected 422 for missing file, got {response.status_code}"
    )

    print(f"\n✅ Missing file handling test passed")
    print(f"   Status Code: {response.status_code}")
