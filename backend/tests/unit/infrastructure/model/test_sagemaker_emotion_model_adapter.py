"""Unit tests for SageMakerEmotionModelAdapter."""

import json
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
from botocore.exceptions import ClientError, EndpointConnectionError, ReadTimeoutError

from app.domain.model.exceptions.prediction_failed_error import PredictionFailedError
from app.domain.model.exceptions.sagemaker_authentication_error import (
    SageMakerAuthenticationError,
)
from app.domain.model.exceptions.sagemaker_endpoint_not_found_error import (
    SageMakerEndpointNotFoundError,
)
from app.domain.model.exceptions.sagemaker_invalid_response_error import (
    SageMakerInvalidResponseError,
)
from app.domain.model.exceptions.sagemaker_throttling_error import (
    SageMakerThrottlingError,
)
from app.domain.model.exceptions.sagemaker_timeout_error import SageMakerTimeoutError
from app.domain.model.value_objects.emotion import Emotion
from app.infrastructure.model.sagemaker_emotion_model_adapter import (
    SageMakerEmotionModelAdapter,
)


class TestSageMakerEmotionModelAdapter:
    """Test suite for SageMakerEmotionModelAdapter."""

    @pytest.fixture
    def mock_boto3_client(self):
        """Mock boto3 SageMaker Runtime client."""
        with patch("app.infrastructure.model.sagemaker_emotion_model_adapter.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def adapter(self, mock_boto3_client):
        """Create SageMakerEmotionModelAdapter instance."""
        return SageMakerEmotionModelAdapter(
            endpoint_name="ml-ser-endpoint4",
            region="us-east-1",
            timeout_seconds=30,
            max_retries=3,
        )

    @pytest.fixture
    def valid_features(self):
        """Create valid feature array (210 features for v6 model)."""
        return np.random.rand(210).astype(np.float64)

    @pytest.fixture
    def valid_sagemaker_response(self):
        """Create valid SageMaker response."""
        return {
            "emotion": "happy",
            "confidence": 0.87,
            "probabilities": {
                "angry": 0.03,
                "disgust": 0.02,
                "fear": 0.01,
                "happy": 0.87,
                "neutral": 0.05,
                "sad": 0.02,
            },
            "model_version": "v5",
        }

    def test_adapter_initialization(self, mock_boto3_client):
        """Test adapter initializes correctly."""
        adapter = SageMakerEmotionModelAdapter(
            endpoint_name="test-endpoint",
            region="us-west-2",
            timeout_seconds=60,
            max_retries=5,
        )

        assert adapter.endpoint_name == "test-endpoint"
        assert adapter.region == "us-west-2"
        assert adapter.timeout_seconds == 60
        assert adapter.max_retries == 5
        assert adapter.client is not None

    def test_predict_emotion_probabilities_success(
        self, adapter, mock_boto3_client, valid_features, valid_sagemaker_response
    ):
        """Test successful prediction."""
        # Mock SageMaker response
        mock_response = {
            "Body": Mock(read=Mock(return_value=json.dumps(valid_sagemaker_response).encode()))
        }
        mock_boto3_client.invoke_endpoint.return_value = mock_response

        # Run prediction
        result = adapter.predict_emotion_probabilities(valid_features)

        # Verify result
        assert isinstance(result, dict)
        assert len(result) == 6  # 6 emotions
        assert all(isinstance(k, Emotion) for k in result.keys())
        assert all(isinstance(v, float) for v in result.values())
        assert all(0.0 <= v <= 1.0 for v in result.values())
        assert abs(sum(result.values()) - 1.0) < 0.01  # Sum ~1.0

        # Verify happy has highest probability
        assert result[Emotion.HAPPY] == 0.87

    def test_predict_with_2d_features(
        self, adapter, mock_boto3_client, valid_features, valid_sagemaker_response
    ):
        """Test prediction with 2D feature array."""
        # Reshape to 2D
        features_2d = valid_features.reshape(1, -1)

        # Mock SageMaker response
        mock_response = {
            "Body": Mock(read=Mock(return_value=json.dumps(valid_sagemaker_response).encode()))
        }
        mock_boto3_client.invoke_endpoint.return_value = mock_response

        # Run prediction
        result = adapter.predict_emotion_probabilities(features_2d)

        # Should work with 2D input
        assert isinstance(result, dict)
        assert len(result) == 6

    def test_predict_with_invalid_feature_count(self, adapter, mock_boto3_client):
        """Test prediction fails with wrong number of features."""
        invalid_features = np.random.rand(100).astype(np.float64)  # Wrong count

        with pytest.raises(PredictionFailedError) as exc_info:
            adapter.predict_emotion_probabilities(invalid_features)

        assert "Expected 210 features, got 100" in str(exc_info.value)

    def test_predict_with_invalid_shape(self, adapter, mock_boto3_client):
        """Test prediction fails with invalid shape."""
        invalid_features = np.random.rand(10, 18).astype(np.float64)  # 3D array

        with pytest.raises(PredictionFailedError) as exc_info:
            adapter.predict_emotion_probabilities(invalid_features)

        assert "Expected single sample" in str(exc_info.value)

    def test_endpoint_not_found_error(self, adapter, mock_boto3_client, valid_features):
        """Test endpoint not found error."""
        error_response = {
            "Error": {
                "Code": "ValidationError",
                "Message": "Could not find endpoint ml-ser-endpoint4",
            }
        }
        mock_boto3_client.invoke_endpoint.side_effect = ClientError(
            error_response, "InvokeEndpoint"
        )

        with pytest.raises(SageMakerEndpointNotFoundError) as exc_info:
            adapter.predict_emotion_probabilities(valid_features)

        assert "ml-ser-endpoint4" in str(exc_info.value)

    def test_authentication_error(self, adapter, mock_boto3_client, valid_features):
        """Test authentication error."""
        error_response = {
            "Error": {
                "Code": "AccessDeniedException",
                "Message": "User is not authorized to perform: sagemaker:InvokeEndpoint",
            }
        }
        mock_boto3_client.invoke_endpoint.side_effect = ClientError(
            error_response, "InvokeEndpoint"
        )

        with pytest.raises(SageMakerAuthenticationError) as exc_info:
            adapter.predict_emotion_probabilities(valid_features)

        assert "Insufficient permissions" in str(exc_info.value)

    def test_timeout_error(self, adapter, mock_boto3_client, valid_features):
        """Test timeout error."""
        mock_boto3_client.invoke_endpoint.side_effect = ReadTimeoutError(
            endpoint_url="https://runtime.sagemaker.us-east-1.amazonaws.com"
        )

        with pytest.raises(SageMakerTimeoutError) as exc_info:
            adapter.predict_emotion_probabilities(valid_features)

        assert "timed out after 30 seconds" in str(exc_info.value)

    def test_connection_timeout_error(self, adapter, mock_boto3_client, valid_features):
        """Test connection timeout error."""
        mock_boto3_client.invoke_endpoint.side_effect = EndpointConnectionError(
            endpoint_url="https://runtime.sagemaker.us-east-1.amazonaws.com"
        )

        with pytest.raises(SageMakerTimeoutError) as exc_info:
            adapter.predict_emotion_probabilities(valid_features)

        assert "timed out" in str(exc_info.value).lower()

    def test_throttling_error_with_retry(self, adapter, mock_boto3_client, valid_features):
        """Test throttling error exhausts retries."""
        error_response = {
            "Error": {
                "Code": "ThrottlingException",
                "Message": "Rate exceeded",
            }
        }
        mock_boto3_client.invoke_endpoint.side_effect = ClientError(
            error_response, "InvokeEndpoint"
        )

        with pytest.raises(SageMakerThrottlingError) as exc_info:
            adapter.predict_emotion_probabilities(valid_features)

        # Should retry 3 times (max_retries=3), so 4 total attempts
        assert mock_boto3_client.invoke_endpoint.call_count == 4
        assert "throttling requests" in str(exc_info.value).lower()

    def test_throttling_error_with_eventual_success(
        self, adapter, mock_boto3_client, valid_features, valid_sagemaker_response
    ):
        """Test throttling error eventually succeeds."""
        error_response = {
            "Error": {
                "Code": "ThrottlingException",
                "Message": "Rate exceeded",
            }
        }

        # First 2 calls fail, third succeeds
        mock_boto3_client.invoke_endpoint.side_effect = [
            ClientError(error_response, "InvokeEndpoint"),
            ClientError(error_response, "InvokeEndpoint"),
            {
                "Body": Mock(
                    read=Mock(return_value=json.dumps(valid_sagemaker_response).encode())
                )
            },
        ]

        result = adapter.predict_emotion_probabilities(valid_features)

        # Should succeed after retries
        assert isinstance(result, dict)
        assert mock_boto3_client.invoke_endpoint.call_count == 3

    def test_invalid_json_response(self, adapter, mock_boto3_client, valid_features):
        """Test invalid JSON response."""
        mock_response = {"Body": Mock(read=Mock(return_value=b"invalid json{}"))}
        mock_boto3_client.invoke_endpoint.return_value = mock_response

        with pytest.raises(SageMakerInvalidResponseError) as exc_info:
            adapter.predict_emotion_probabilities(valid_features)

        assert "not valid JSON" in str(exc_info.value)

    def test_missing_probabilities_field(self, adapter, mock_boto3_client, valid_features):
        """Test response missing probabilities field."""
        invalid_response = {"emotion": "happy", "confidence": 0.87}
        mock_response = {
            "Body": Mock(read=Mock(return_value=json.dumps(invalid_response).encode()))
        }
        mock_boto3_client.invoke_endpoint.return_value = mock_response

        with pytest.raises(SageMakerInvalidResponseError) as exc_info:
            adapter.predict_emotion_probabilities(valid_features)

        assert "missing 'probabilities' field" in str(exc_info.value).lower()

    def test_missing_emotion_in_probabilities(
        self, adapter, mock_boto3_client, valid_features
    ):
        """Test response missing an emotion in probabilities."""
        invalid_response = {
            "probabilities": {
                "angry": 0.1,
                "disgust": 0.1,
                "fear": 0.1,
                "happy": 0.6,
                "neutral": 0.1,
                # Missing 'sad'
            }
        }
        mock_response = {
            "Body": Mock(read=Mock(return_value=json.dumps(invalid_response).encode()))
        }
        mock_boto3_client.invoke_endpoint.return_value = mock_response

        with pytest.raises(SageMakerInvalidResponseError) as exc_info:
            adapter.predict_emotion_probabilities(valid_features)

        assert "Missing probability for emotion 'sad'" in str(exc_info.value)

    def test_invalid_probability_value(self, adapter, mock_boto3_client, valid_features):
        """Test response with invalid probability value."""
        invalid_response = {
            "probabilities": {
                "angry": 0.1,
                "disgust": 0.1,
                "fear": 0.1,
                "happy": 1.5,  # Invalid (>1.0)
                "neutral": 0.1,
                "sad": 0.1,
            }
        }
        mock_response = {
            "Body": Mock(read=Mock(return_value=json.dumps(invalid_response).encode()))
        }
        mock_boto3_client.invoke_endpoint.return_value = mock_response

        with pytest.raises(SageMakerInvalidResponseError) as exc_info:
            adapter.predict_emotion_probabilities(valid_features)

        assert "must be in [0,1]" in str(exc_info.value)

    def test_serialize_features(self, adapter, valid_features):
        """Test feature serialization."""
        correlation_id = "test-correlation-id"
        features_list = adapter._serialize_features(valid_features, correlation_id)

        assert isinstance(features_list, list)
        assert len(features_list) == 210
        assert all(isinstance(f, float) for f in features_list)

    def test_serialize_features_2d(self, adapter, valid_features):
        """Test feature serialization with 2D input."""
        correlation_id = "test-correlation-id"
        features_2d = valid_features.reshape(1, -1)
        features_list = adapter._serialize_features(features_2d, correlation_id)

        assert isinstance(features_list, list)
        assert len(features_list) == 210

    def test_parse_response(self, adapter, valid_sagemaker_response):
        """Test response parsing."""
        correlation_id = "test-correlation-id"
        probabilities = adapter._parse_response(valid_sagemaker_response, correlation_id)

        assert isinstance(probabilities, np.ndarray)
        assert len(probabilities) == 6
        assert probabilities[3] == 0.87  # Happy (index 3 in mapping)

    def test_map_to_emotions(self, adapter):
        """Test mapping probabilities to emotions."""
        probabilities = np.array([0.03, 0.02, 0.01, 0.87, 0.05, 0.02])
        result = adapter._map_to_emotions(probabilities)

        assert isinstance(result, dict)
        assert len(result) == 6
        assert result[Emotion.HAPPY] == 0.87
        assert result[Emotion.ANGRY] == 0.03
