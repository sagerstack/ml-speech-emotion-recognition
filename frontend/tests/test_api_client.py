"""
Tests for the Streamlit frontend API client
Focus on HTTP status code handling and appropriate user messages
"""

import pytest
import responses
import requests
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json
import tempfile
import os
import sys

# Add the streamlit_app directory to Python path
streamlit_app_path = Path(__file__).parent.parent / "streamlit_app"
sys.path.insert(0, str(streamlit_app_path))

# Mock streamlit before importing any modules that use it
mock_stlit = Mock()
mock_stlit.error = Mock()
mock_stlit.success = Mock()
mock_stlit.info = Mock()
mock_stlit.warning = Mock()
mock_stlit.session_state = Mock()
sys.modules['streamlit'] = mock_stlit

from utils.api_client import APIClient
from tests.fixtures.mock_responses import MockAPIResponses, HTTP_STATUS_MESSAGES, get_status_message


def create_mock_audio_file(filename="test_audio.wav", content_type="audio/wav"):
    """Create a proper mock audio file with actual data"""
    # Create a simple WAV file content (minimal header + sine wave data)
    import struct
    import numpy as np

    # Generate simple sine wave audio data
    sample_rate = 22050
    duration = 0.5  # Short duration for testing
    frequency = 440
    samples = int(sample_rate * duration)

    t = np.linspace(0, duration, samples, False)
    audio_data = np.sin(2 * np.pi * frequency * t) * 0.3

    # Convert to 16-bit PCM
    audio_int16 = (audio_data * 32767).astype(np.int16)

    # Create WAV file bytes
    wav_data = bytearray()

    # RIFF header
    wav_data.extend(b'RIFF')
    wav_data.extend(struct.pack('<I', 36 + len(audio_int16) * 2))
    wav_data.extend(b'WAVE')

    # fmt chunk
    wav_data.extend(b'fmt ')
    wav_data.extend(struct.pack('<I', 16))  # chunk size
    wav_data.extend(struct.pack('<H', 1))   # PCM format
    wav_data.extend(struct.pack('<H', 1))   # mono
    wav_data.extend(struct.pack('<I', sample_rate))  # sample rate
    wav_data.extend(struct.pack('<I', sample_rate * 2))  # byte rate
    wav_data.extend(struct.pack('<H', 2))   # block align
    wav_data.extend(struct.pack('<H', 16))  # bits per sample

    # data chunk
    wav_data.extend(b'data')
    wav_data.extend(struct.pack('<I', len(audio_int16) * 2))
    wav_data.extend(audio_int16.tobytes())

    # Create mock file object
    mock_file = Mock()
    mock_file.name = filename
    mock_file.type = content_type
    mock_file.read = Mock(return_value=bytes(wav_data))
    mock_file.seek = Mock(return_value=0)
    mock_file.getvalue = Mock(return_value=bytes(wav_data))

    return mock_file


class TestAPIClient:
    """Test cases for APIClient class"""

    @pytest.fixture
    def api_client(self):
        """Create APIClient instance for testing"""
        return APIClient("http://localhost:8000")

    @pytest.fixture
    def api_client_custom_url(self):
        """Create APIClient instance with custom URL"""
        return APIClient("http://custom-api:5000")

    def test_init_default_url(self):
        """Test APIClient initialization with default URL"""
        client = APIClient()
        assert client.base_url == "http://localhost:8000"
        assert hasattr(client, 'session')

    def test_init_custom_url(self):
        """Test APIClient initialization with custom URL"""
        custom_url = "http://custom-api:5000"
        client = APIClient(custom_url)
        assert client.base_url == custom_url

    def test_init_url_trailing_slash(self):
        """Test URL normalization (removing trailing slash)"""
        client = APIClient("http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"

    @responses.activate
    def test_health_check_success(self, api_client):
        """Test successful health check (200 OK)"""
        mock_response = MockAPIResponses.health_check_response(200)
        responses.add(
            responses.GET,
            "http://localhost:8000/health",
            json=mock_response["json"],
            status=mock_response["status_code"]
        )

        result = api_client.health_check()

        assert result["status"] == "healthy"
        assert "timestamp" in result
        assert "version" in result
        assert "checks" in result

    @responses.activate
    def test_health_check_custom_url(self, api_client_custom_url):
        """Test health check with custom URL"""
        mock_response = MockAPIResponses.health_check_response(200)
        responses.add(
            responses.GET,
            "http://custom-api:5000/health",
            json=mock_response["json"],
            status=mock_response["status_code"]
        )

        result = api_client_custom_url.health_check()

        assert result["status"] == "healthy"

    @responses.activate
    def test_health_check_service_unavailable(self, api_client):
        """Test health check with service unavailable (503)"""
        mock_response = MockAPIResponses.health_check_response(503)
        responses.add(
            responses.GET,
            "http://localhost:8000/health",
            json=mock_response["json"],
            status=mock_response["status_code"]
        )

        result = api_client.health_check()

        assert result["status"] == "error"
        assert "message" in result

    @responses.activate
    def test_health_check_server_error(self, api_client):
        """Test health check with server error (500)"""
        mock_response = MockAPIResponses.health_check_response(500)
        responses.add(
            responses.GET,
            "http://localhost:8000/health",
            json=mock_response["json"],
            status=mock_response["status_code"]
        )

        result = api_client.health_check()

        assert result["status"] == "error"

    @patch('requests.Session.get')
    def test_health_check_connection_error(self, mock_get, api_client):
        """Test health check with connection error"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        result = api_client.health_check()

        assert result["status"] == "error"
        assert "Connection failed" in result["message"]

    @patch('requests.Session.get')
    def test_health_check_timeout(self, mock_get, api_client):
        """Test health check with timeout"""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")

        result = api_client.health_check()

        assert result["status"] == "error"
        assert "timeout" in result["message"].lower()

    @responses.activate
    def test_predict_emotion_success(self, api_client, sample_audio_file):
        """Test successful emotion prediction"""
        mock_response = MockAPIResponses.prediction_response(200)
        responses.add(
            responses.POST,
            "http://localhost:8000/predict",
            json=mock_response["json"],
            status=mock_response["status_code"]
        )

        # Create proper mock file object with actual audio data
        mock_file = create_mock_audio_file()

        result = api_client.predict_emotion(mock_file)

        assert result is not None
        assert result["emotion"] == "happy"
        assert result["confidence"] == 0.85
        assert "probabilities" in result
        assert "processing_time" in result

    @responses.activate
    def test_predict_emotion_unsupported_format(self, api_client, sample_audio_file):
        """Test emotion prediction with unsupported format (400)"""
        mock_response = MockAPIResponses.prediction_response(400)
        responses.add(
            responses.POST,
            "http://localhost:8000/predict",
            json=mock_response["json"],
            status=mock_response["status_code"]
        )

        mock_file = create_mock_audio_file("test.xyz", "application/octet-stream")

        # Reset the global mock error call count
        mock_stlit.error.reset_mock()

        result = api_client.predict_emotion(mock_file)
        assert result is None
        mock_stlit.error.assert_called_once()

    @responses.activate
    def test_predict_emotion_file_too_large(self, api_client, sample_large_audio_file):
        """Test emotion prediction with file too large (413)"""
        mock_response = MockAPIResponses.prediction_response(413)
        responses.add(
            responses.POST,
            "http://localhost:8000/predict",
            json=mock_response["json"],
            status=mock_response["status_code"]
        )

        mock_file = create_mock_audio_file("large_audio.wav", "audio/wav")

        # Reset the global mock error call count
        mock_stlit.error.reset_mock()

        result = api_client.predict_emotion(mock_file)
        assert result is None
        mock_stlit.error.assert_called_once()

    @responses.activate
    def test_predict_emotion_server_error(self, api_client, sample_audio_file):
        """Test emotion prediction with server error (500)"""
        mock_response = MockAPIResponses.prediction_response(500)
        responses.add(
            responses.POST,
            "http://localhost:8000/predict",
            json=mock_response["json"],
            status=mock_response["status_code"]
        )

        mock_file = create_mock_audio_file()

        # Reset the global mock error call count
        mock_stlit.error.reset_mock()

        result = api_client.predict_emotion(mock_file)
        assert result is None
        mock_stlit.error.assert_called_once()

    @patch('requests.Session.post')
    def test_predict_emotion_timeout(self, mock_post, api_client, sample_audio_file):
        """Test emotion prediction with timeout"""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        mock_file = create_mock_audio_file()

        # Reset the global mock error call count
        mock_stlit.error.reset_mock()

        result = api_client.predict_emotion(mock_file)
        assert result is None
        mock_stlit.error.assert_called_once_with("Request timed out. The audio file might be too large or the server is busy.")

    @responses.activate
    def test_predict_emotion_invalid_json(self, api_client, sample_audio_file):
        """Test emotion prediction with invalid JSON response"""
        responses.add(
            responses.POST,
            "http://localhost:8000/predict",
            body="Invalid JSON response",
            status=200
        )

        mock_file = create_mock_audio_file()

        # Reset the global mock error call count
        mock_stlit.error.reset_mock()

        result = api_client.predict_emotion(mock_file)
        assert result is None
        # Check that error was called (the exact message may vary)
        mock_stlit.error.assert_called_once()

    @responses.activate
    def test_get_supported_formats_success(self, api_client):
        """Test getting supported formats successfully"""
        mock_response = MockAPIResponses.supported_formats_response(200)
        responses.add(
            responses.GET,
            "http://localhost:8000/info",
            json=mock_response["json"],
            status=mock_response["status_code"]
        )

        result = api_client.get_supported_formats()

        assert isinstance(result, list)
        assert "wav" in result
        assert "mp3" in result
        assert "flac" in result
        assert "m4a" in result

    @responses.activate
    def test_get_supported_formats_error(self, api_client):
        """Test getting supported formats with error (returns defaults)"""
        responses.add(
            responses.GET,
            "http://localhost:8000/info",
            json={"error": "Service unavailable"},
            status=500
        )

        result = api_client.get_supported_formats()

        # Should return default formats
        assert isinstance(result, list)
        assert result == ["wav", "mp3", "flac", "m4a"]

    def test_get_supported_formats_connection_error(self, api_client):
        """Test getting supported formats with connection error"""
        # Don't mock any response, will cause connection error
        result = api_client.get_supported_formats()

        # Should return default formats
        assert isinstance(result, list)
        assert result == ["wav", "mp3", "flac", "m4a"]

    @responses.activate
    def test_get_model_info_success(self, api_client):
        """Test getting model info successfully"""
        mock_response = MockAPIResponses.model_info_response(200)
        responses.add(
            responses.GET,
            "http://localhost:8000/model/info",
            json=mock_response["json"],
            status=mock_response["status_code"]
        )

        result = api_client.get_model_info()

        assert result["model_name"] == "emotion-recognition-v1"
        assert "version" in result
        assert "supported_emotions" in result
        assert "accuracy" in result

    @responses.activate
    def test_get_model_info_error(self, api_client):
        """Test getting model info with error"""
        responses.add(
            responses.GET,
            "http://localhost:8000/model/info",
            json={"error": "Model unavailable"},
            status=500
        )

        result = api_client.get_model_info()

        assert result["status"] == "unavailable"

    def test_get_model_info_connection_error(self, api_client):
        """Test getting model info with connection error"""
        # Don't mock any response, will cause connection error
        result = api_client.get_model_info()

        assert result["status"] == "unavailable"

    @responses.activate
    def test_test_endpoint_available(self, api_client):
        """Test endpoint availability check - endpoint exists"""
        responses.add(
            responses.GET,
            "http://localhost:8000/health",
            json={"status": "healthy"},
            status=200
        )

        result = api_client.test_endpoint("health")

        assert result is True

    @responses.activate
    def test_test_endpoint_not_found(self, api_client):
        """Test endpoint availability check - endpoint doesn't exist"""
        responses.add(
            responses.GET,
            "http://localhost:8000/nonexistent",
            status=404
        )

        result = api_client.test_endpoint("nonexistent")

        assert result is False

    @responses.activate
    def test_test_endpoint_server_error(self, api_client):
        """Test endpoint availability check - server error"""
        responses.add(
            responses.GET,
            "http://localhost:8000/error",
            status=500
        )

        result = api_client.test_endpoint("error")

        assert result is True  # Endpoint exists but has error

    def test_test_endpoint_connection_error(self, api_client):
        """Test endpoint availability check - connection error"""
        # Don't mock any response, will cause connection error
        result = api_client.test_endpoint("nonexistent")

        assert result is False


class TestHTTPStatusMessages:
    """Test HTTP status code to user message mapping"""

    def test_get_status_message_200(self):
        """Test success message for 200 OK"""
        message = get_status_message(200)
        assert message["type"] == "success"
        assert "✅" in message["message"]
        assert "successful" in message["message"].lower()

    def test_get_status_message_400(self):
        """Test error message for 400 Bad Request"""
        message = get_status_message(400)
        assert message["type"] == "error"
        assert "❌" in message["message"]
        assert "bad request" in message["message"].lower()

    def test_get_status_message_404(self):
        """Test error message for 404 Not Found"""
        message = get_status_message(404)
        assert message["type"] == "error"
        assert "❌" in message["message"]
        assert "not found" in message["message"].lower()

    def test_get_status_message_500(self):
        """Test error message for 500 Internal Server Error"""
        message = get_status_message(500)
        assert message["type"] == "error"
        assert "❌" in message["message"]
        assert "server error" in message["message"].lower()

    def test_get_status_message_503(self):
        """Test error message for 503 Service Unavailable"""
        message = get_status_message(503)
        assert message["type"] == "error"
        assert "❌" in message["message"]
        assert "unavailable" in message["message"].lower()

    def test_get_status_message_connection_error(self):
        """Test error message for connection error"""
        message = get_status_message("connection_error")
        assert message["type"] == "error"
        assert "❌" in message["message"]
        assert "connection failed" in message["message"].lower()

    def test_get_status_message_timeout(self):
        """Test error message for timeout"""
        message = get_status_message("timeout")
        assert message["type"] == "error"
        assert "❌" in message["message"]
        assert "timeout" in message["message"].lower()

    def test_get_status_message_unknown(self):
        """Test error message for unknown error"""
        message = get_status_message(999)
        assert message["type"] == "error"
        assert "❌" in message["message"]
        assert "unknown error" in message["message"].lower()


class TestAPIIntegration:
    """Integration tests for API client with realistic scenarios"""

    @pytest.fixture
    def api_client(self):
        """Create APIClient instance for testing"""
        return APIClient("http://localhost:8000")

    @pytest.fixture
    def api_client_custom_url(self):
        """Create APIClient instance with custom URL for testing"""
        return APIClient("http://custom-api:5000")

    @pytest.fixture
    def mock_streamlit_error(self):
        """Reset streamlit.error mock for testing error display"""
        mock_stlit.error.reset_mock()
        return mock_stlit.error

    @responses.activate
    def test_complete_workflow_success(self, api_client, sample_audio_file, mock_streamlit_error):
        """Test complete successful workflow: health check -> prediction"""
        # Mock health check
        health_response = MockAPIResponses.health_check_response(200)
        responses.add(
            responses.GET,
            "http://localhost:8000/health",
            json=health_response["json"],
            status=200
        )

        # Mock prediction
        prediction_response = MockAPIResponses.prediction_response(200)
        responses.add(
            responses.POST,
            "http://localhost:8000/predict",
            json=prediction_response["json"],
            status=200
        )

        # Test health check
        health_result = api_client.health_check()
        assert health_result["status"] == "healthy"

        # Test prediction
        mock_file = create_mock_audio_file()

        prediction_result = api_client.predict_emotion(mock_file)
        assert prediction_result is not None
        assert prediction_result["emotion"] == "happy"

        # Ensure no error messages were displayed
        mock_streamlit_error.assert_not_called()

    @responses.activate
    def test_workflow_with_api_failure(self, api_client, sample_audio_file, mock_streamlit_error):
        """Test workflow when API is unavailable"""
        # Mock health check failure
        responses.add(
            responses.GET,
            "http://localhost:8000/health",
            json={"error": "Service unavailable"},
            status=503
        )

        # Mock prediction failure
        responses.add(
            responses.POST,
            "http://localhost:8000/predict",
            json={"detail": "Service unavailable"},
            status=503
        )

        # Test health check
        health_result = api_client.health_check()
        assert health_result["status"] == "error"

        # Test prediction
        mock_file = create_mock_audio_file()

        prediction_result = api_client.predict_emotion(mock_file)
        assert prediction_result is None

        # Verify error message was displayed
        mock_streamlit_error.assert_called()

    def test_custom_api_url_workflow(self, api_client_custom_url):
        """Test workflow with custom API URL"""
        # Test that the client uses the custom URL
        assert api_client_custom_url.base_url == "http://custom-api:5000"

        # Test endpoint construction
        expected_health_url = "http://custom-api:5000/health"
        expected_predict_url = "http://custom-api:5000/predict"

        # The client should construct URLs correctly
        assert api_client_custom_url.base_url + "/health" == expected_health_url
        assert api_client_custom_url.base_url + "/predict" == expected_predict_url