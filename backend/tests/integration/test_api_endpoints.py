"""
Integration tests for API endpoints.

This module tests the integration between different components and the
overall API functionality including request/response handling.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app


class TestRootEndpoint:
    """Integration tests for root endpoint."""

    def test_root_endpoint_success(self, test_client: TestClient) -> None:
        """Test successful root endpoint response."""
        response = test_client.get("/")

        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "ML Speech Emotion Recognition API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
        assert data["docs"] == "/docs"

    def test_root_endpoint_response_headers(self, test_client: TestClient) -> None:
        """Test root endpoint response headers."""
        response = test_client.get("/")

        assert response.status_code == 200
        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]

    def test_root_endpoint_cors_headers(self, test_client: TestClient) -> None:
        """Test CORS headers on root endpoint."""
        response = test_client.options("/", headers={"Origin": "http://localhost:3000"})

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers


class TestHealthEndpoint:
    """Integration tests for health check endpoint."""

    def test_health_check_success(self, test_client: TestClient) -> None:
        """Test successful health check response."""
        response = test_client.get("/health")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "ml-emotion-api"
        assert data["version"] == "1.0.0"

    def test_health_check_response_time(self, test_client: TestClient) -> None:
        """Test health check response time is reasonable."""
        import time
        start_time = time.time()
        response = test_client.get("/health")
        end_time = time.time()

        response_time = end_time - start_time
        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second


class TestPredictionEndpoints:
    """Integration tests for prediction endpoints."""

    def test_prediction_health_check(self, test_client: TestClient) -> None:
        """Test prediction service health check."""
        response = test_client.get("/v1/predictions/health")

        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "emotion-prediction"
        assert data["model_status"] == "available"
        assert "supported_formats" in data

    def test_get_supported_formats(self, test_client: TestClient) -> None:
        """Test getting supported audio formats."""
        response = test_client.get("/v1/predictions/formats")

        assert response.status_code == 200

        data = response.json()
        assert "supported_formats" in data
        assert isinstance(data["supported_formats"], list)
        assert "max_file_size_mb" in data
        assert "max_duration_seconds" in data
        assert data["max_file_size_mb"] == 30
        assert data["max_duration_seconds"] == 30

    def test_predict_emotion_success(self, test_client: TestClient, sample_audio_file: bytes) -> None:
        """Test successful emotion prediction."""
        files = {"file": ("test_audio.wav", sample_audio_file, "audio/wav")}
        data = {"user_id": "test-user-123"}

        response = test_client.post("/v1/predictions/predict", files=files, data=data)

        assert response.status_code == 200

        response_data = response.json()
        assert response_data["success"] is True
        assert "data" in response_data
        assert "request_id" in response_data

        # Check predictions structure
        predictions = response_data["data"]["predictions"]
        assert isinstance(predictions, list)
        assert len(predictions) > 0

        # Check each prediction has required fields
        for prediction in predictions:
            assert "label" in prediction
            assert "confidence" in prediction
            assert isinstance(prediction["confidence"], (int, float))
            assert 0 <= prediction["confidence"] <= 1

        # Check audio metadata
        metadata = response_data["data"]["audio_metadata"]
        assert "duration" in metadata
        assert "sample_rate" in metadata
        assert "channels" in metadata
        assert "format" in metadata

        # Check processing info
        processing_info = response_data["data"]["processing_info"]
        assert "correlation_id" in processing_info
        assert "model_version" in processing_info
        assert "processed_at" in processing_info

    def test_predict_emotion_with_mp3(self, test_client: TestClient, sample_mp3_file: bytes) -> None:
        """Test emotion prediction with MP3 file."""
        files = {"file": ("test_audio.mp3", sample_mp3_file, "audio/mp3")}

        response = test_client.post("/v1/predictions/predict", files=files)

        assert response.status_code == 200

        response_data = response.json()
        assert response_data["success"] is True
        assert "predictions" in response_data["data"]

    def test_predict_emotion_unsupported_format(self, test_client: TestClient) -> None:
        """Test prediction with unsupported file format."""
        files = {"file": ("test.txt", b"This is not audio", "text/plain")}

        response = test_client.post("/v1/predictions/predict", files=files)

        assert response.status_code == 400

        data = response.json()
        assert "Unsupported file type" in data["detail"]

    def test_predict_emotion_file_too_large(self, test_client: TestClient, large_audio_file: bytes) -> None:
        """Test prediction with file exceeding size limit."""
        files = {"file": ("large_audio.wav", large_audio_file, "audio/wav")}

        response = test_client.post("/v1/predictions/predict", files=files)

        assert response.status_code == 413

        data = response.json()
        assert "File size exceeds maximum" in data["detail"]

    def test_predict_emotion_empty_file(self, test_client: TestClient) -> None:
        """Test prediction with empty file."""
        files = {"file": ("empty.wav", b"", "audio/wav")}

        response = test_client.post("/v1/predictions/predict", files=files)

        assert response.status_code == 400

        data = response.json()
        assert "Audio processing failed" in data["detail"]

    def test_predict_emotion_corrupted_file(self, test_client: TestClient, corrupted_audio_file: bytes) -> None:
        """Test prediction with corrupted audio file."""
        files = {"file": ("corrupted.wav", corrupted_audio_file, "audio/wav")}

        response = test_client.post("/v1/predictions/predict", files=files)

        assert response.status_code == 400

        data = response.json()
        assert "Audio processing failed" in data["detail"]

    def test_predict_emotion_no_file(self, test_client: TestClient) -> None:
        """Test prediction without file upload."""
        response = test_client.post("/v1/predictions/predict")

        assert response.status_code == 422  # Validation error

    def test_predict_emotion_with_user_id(self, test_client: TestClient, sample_audio_file: bytes) -> None:
        """Test prediction with user ID tracking."""
        files = {"file": ("test.wav", sample_audio_file, "audio/wav")}
        data = {"user_id": "user-456"}

        response = test_client.post("/v1/predictions/predict", files=files, data=data)

        assert response.status_code == 200

        # The user_id should be processed (logged, but not necessarily returned)
        response_data = response.json()
        assert response_data["success"] is True

    def test_predict_emotion_different_user_ids(self, test_client: TestClient, sample_audio_file: bytes) -> None:
        """Test prediction with different user IDs."""
        user_ids = ["user1", "user2", "user3", None]

        for user_id in user_ids:
            files = {"file": ("test.wav", sample_audio_file, "audio/wav")}
            data = {}
            if user_id:
                data["user_id"] = user_id

            response = test_client.post("/v1/predictions/predict", files=files, data=data)

            assert response.status_code == 200
            response_data = response.json()
            assert response_data["success"] is True

    @patch('app.api.v1.endpoints.predictions.audio_processor.process_audio_file')
    def test_predict_emotion_audio_processing_error(self, mock_process: MagicMock, test_client: TestClient) -> None:
        """Test prediction when audio processing fails."""
        from app.services.audio_service import AudioProcessingError

        mock_process.side_effect = AudioProcessingError("Processing failed")

        files = {"file": ("test.wav", b"fake audio", "audio/wav")}

        response = test_client.post("/v1/predictions/predict", files=files)

        assert response.status_code == 400

        data = response.json()
        assert "Audio processing failed" in data["detail"]

    @patch('app.api.v1.endpoints.predictions.audio_processor.process_audio_file')
    def test_predict_emotion_unexpected_error(self, mock_process: MagicMock, test_client: TestClient) -> None:
        """Test prediction when unexpected error occurs."""
        mock_process.side_effect = Exception("Unexpected error")

        files = {"file": ("test.wav", b"fake audio", "audio/wav")}

        response = test_client.post("/v1/predictions/predict", files=files)

        assert response.status_code == 500

        data = response.json()
        assert "Internal server error" in data["detail"]


class TestAPIIntegration:
    """Integration tests for overall API functionality."""

    def test_api_docs_available(self, test_client: TestClient) -> None:
        """Test that API documentation is available."""
        response = test_client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_api_openapi_spec(self, test_client: TestClient) -> None:
        """Test that OpenAPI specification is available."""
        response = test_client.get("/openapi.json")

        assert response.status_code == 200

        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    def test_api_redoc_available(self, test_client: TestClient) -> None:
        """Test that ReDoc documentation is available."""
        response = test_client.get("/redoc")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_cors_preflight(self, test_client: TestClient) -> None:
        """Test CORS preflight requests."""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }

        response = test_client.options("/v1/predictions/predict", headers=headers)

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_headers_in_response(self, test_client: TestClient, sample_audio_file: bytes) -> None:
        """Test CORS headers in actual responses."""
        headers = {"Origin": "http://localhost:3000"}
        files = {"file": ("test.wav", sample_audio_file, "audio/wav")}

        response = test_client.post("/v1/predictions/predict", files=files, headers=headers)

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_multiple_concurrent_requests(self, test_client: TestClient, sample_audio_file: bytes) -> None:
        """Test handling multiple concurrent requests."""
        import concurrent.futures
        import threading

        def make_request():
            files = {"file": ("test.wav", sample_audio_file, "audio/wav")}
            return test_client.post("/v1/predictions/predict", files=files)

        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [future.result() for future in futures]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["success"] is True

    def test_request_response_consistency(self, test_client: TestClient, sample_audio_file: bytes) -> None:
        """Test that the same input produces consistent responses."""
        files = {"file": ("test.wav", sample_audio_file, "audio/wav")}

        # Make the same request twice
        response1 = test_client.post("/v1/predictions/predict", files=files)
        response2 = test_client.post("/v1/predictions/predict", files=files)

        assert response1.status_code == 200
        assert response2.status_code == 200

        data1 = response1.json()
        data2 = response2.json()

        # Structure should be consistent
        assert data1["success"] == data2["success"]
        assert "data" in data1 and "data" in data2
        assert "predictions" in data1["data"] and "predictions" in data2["data"]

        # Audio metadata should be the same
        metadata1 = data1["data"]["audio_metadata"]
        metadata2 = data2["data"]["audio_metadata"]
        assert metadata1["duration"] == metadata2["duration"]
        assert metadata1["sample_rate"] == metadata2["sample_rate"]

    def test_error_response_format(self, test_client: TestClient) -> None:
        """Test that error responses have consistent format."""
        # Test various error scenarios
        error_scenarios = [
            ("POST", "/v1/predictions/predict", {}),  # No file
            ("POST", "/v1/predictions/predict", {"file": ("test.txt", b"text", "text/plain")}),  # Wrong format
        ]

        for method, endpoint, files in error_scenarios:
            if files:
                response = test_client.post(endpoint, files=files)
            else:
                response = test_client.post(endpoint)

            # Error responses should have consistent structure
            assert response.status_code >= 400

            data = response.json()
            assert "detail" in data  # FastAPI error format


class TestErrorHandling:
    """Integration tests for error handling scenarios."""

    def test_404_not_found(self, test_client: TestClient) -> None:
        """Test 404 error handling."""
        response = test_client.get("/nonexistent-endpoint")

        assert response.status_code == 404

        data = response.json()
        assert "detail" in data

    def test_method_not_allowed(self, test_client: TestClient) -> None:
        """Test method not allowed error."""
        response = test_client.delete("/health")

        assert response.status_code == 405

    def test_validation_error_format(self, test_client: TestClient) -> None:
        """Test validation error format."""
        response = test_client.post("/v1/predictions/predict")

        assert response.status_code == 422

        data = response.json()
        assert "detail" in data
        # Validation errors should provide helpful information
        assert isinstance(data["detail"], list)


class TestPerformance:
    """Integration tests for performance characteristics."""

    def test_health_check_performance(self, test_client: TestClient) -> None:
        """Test health check endpoint performance."""
        import time

        start_time = time.time()
        response = test_client.get("/health")
        end_time = time.time()

        response_time = (end_time - start_time) * 1000  # Convert to milliseconds

        assert response.status_code == 200
        assert response_time < 100  # Should respond within 100ms

    def test_prediction_endpoint_performance(self, test_client: TestClient, sample_audio_file: bytes) -> None:
        """Test prediction endpoint performance."""
        import time

        files = {"file": ("test.wav", sample_audio_file, "audio/wav")}

        start_time = time.time()
        response = test_client.post("/v1/predictions/predict", files=files)
        end_time = time.time()

        response_time = (end_time - start_time) * 1000  # Convert to milliseconds

        assert response.status_code == 200
        # Should process within reasonable time (adjust threshold as needed)
        assert response_time < 5000  # 5 seconds max

    def test_memory_usage_stability(self, test_client: TestClient, sample_audio_file: bytes) -> None:
        """Test that memory usage remains stable across multiple requests."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Make multiple requests
        for _ in range(10):
            files = {"file": ("test.wav", sample_audio_file, "audio/wav")}
            response = test_client.post("/v1/predictions/predict", files=files)
            assert response.status_code == 200

        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024  # 100MB in bytes


@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end integration tests."""

    def test_complete_prediction_workflow(self, test_client: TestClient, sample_audio_file: bytes) -> None:
        """Test complete workflow from health check to prediction."""
        # 1. Check service health
        health_response = test_client.get("/health")
        assert health_response.status_code == 200

        # 2. Check prediction service health
        pred_health_response = test_client.get("/v1/predictions/health")
        assert pred_health_response.status_code == 200

        # 3. Get supported formats
        formats_response = test_client.get("/v1/predictions/formats")
        assert formats_response.status_code == 200

        # 4. Make prediction
        files = {"file": ("test.wav", sample_audio_file, "audio/wav")}
        data = {"user_id": "e2e-test-user"}

        prediction_response = test_client.post("/v1/predictions/predict", files=files, data=data)
        assert prediction_response.status_code == 200

        prediction_data = prediction_response.json()
        assert prediction_data["success"] is True
        assert "predictions" in prediction_data["data"]

        # 5. Verify predictions structure
        predictions = prediction_data["data"]["predictions"]
        assert len(predictions) > 0
        assert all("label" in p and "confidence" in p for p in predictions)

    def test_workflow_with_different_audio_formats(self, test_client: TestClient) -> None:
        """Test workflow with different audio formats."""
        # Test with WAV
        wav_files = {"file": ("test.wav", b"fake wav data", "audio/wav")}
        wav_response = test_client.post("/v1/predictions/predict", files=wav_files)

        # Test with MP3
        mp3_files = {"file": ("test.mp3", b"fake mp3 data", "audio/mp3")}
        mp3_response = test_client.post("/v1/predictions/predict", files=mp3_files)

        # Both should attempt processing (may fail at audio processing stage)
        # but should get past format validation
        assert wav_response.status_code in [200, 400]  # May fail at processing
        assert mp3_response.status_code in [200, 400]

    def test_error_recovery_workflow(self, test_client: TestClient) -> None:
        """Test error recovery in workflow."""
        # 1. Try with invalid file
        invalid_files = {"file": ("invalid.txt", b"not audio", "text/plain")}
        error_response = test_client.post("/v1/predictions/predict", files=invalid_files)
        assert error_response.status_code == 400

        # 2. Try with valid file immediately after
        # This tests that the service recovers gracefully
        valid_files = {"file": ("test.wav", b"fake audio", "audio/wav")}
        valid_response = test_client.post("/v1/predictions/predict", files=valid_files)

        # Should handle the request without issues
        assert valid_response.status_code in [200, 400]  # May fail at processing but not crash