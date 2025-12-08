"""Integration tests for SageMaker model repository with mocked boto3.

These tests verify the end-to-end flow with mocked AWS services:
- Feature extraction in backend
- SageMaker endpoint invocation (mocked)
- Response parsing and mapping
- Error handling
"""

import json
from unittest.mock import Mock, patch

import numpy as np
import pytest
from botocore.exceptions import ClientError

from app.domain.model.exceptions.sagemaker_endpoint_not_found_error import (
    SageMakerEndpointNotFoundError,
)
from app.domain.model.value_objects.emotion import Emotion
from app.domain.model.value_objects.model_version import ModelVersion
from app.infrastructure.model.sagemaker_emotion_model_adapter import (
    SageMakerEmotionModelAdapter,
)
from app.infrastructure.model.sagemaker_model_repository import SageMakerModelRepository


class TestSageMakerIntegration:
    """Integration tests for SageMaker integration."""

    @pytest.fixture
    def mock_sagemaker_runtime_client(self):
        """Mock SageMaker Runtime client for invoke_endpoint."""
        with patch("app.infrastructure.model.sagemaker_emotion_model_adapter.boto3") as mock_boto3:
            mock_client = Mock()
            mock_boto3.client.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def mock_sagemaker_control_client(self):
        """Mock SageMaker client for control plane operations."""
        with patch("app.infrastructure.model.sagemaker_model_repository.boto3") as mock_boto3:
            mock_client = Mock()
            mock_boto3.client.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def valid_features(self):
        """Create valid feature array (180 features)."""
        np.random.seed(42)
        return np.random.rand(180).astype(np.float64)

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

    def test_full_inference_flow(
        self,
        mock_sagemaker_runtime_client,
        mock_sagemaker_control_client,
        valid_features,
        valid_sagemaker_response,
    ):
        """Test complete inference flow: load model -> predict."""
        # Mock endpoint status (control plane)
        mock_sagemaker_control_client.describe_endpoint.return_value = {
            "EndpointStatus": "InService",
            "EndpointName": "ml-ser-endpoint4",
        }

        # Mock inference response (runtime)
        mock_response = {
            "Body": Mock(read=Mock(return_value=json.dumps(valid_sagemaker_response).encode()))
        }
        mock_sagemaker_runtime_client.invoke_endpoint.return_value = mock_response

        # Create repository and load model
        repository = SageMakerModelRepository(
            endpoint_name="ml-ser-endpoint4",
            region="us-east-1",
        )

        version = ModelVersion.from_string("v5")
        model = repository.load_model(version)

        # Run prediction
        result = model.predict_emotion_probabilities(valid_features)

        # Verify result
        assert isinstance(result, dict)
        assert len(result) == 6
        assert result[Emotion.HAPPY] == 0.87
        assert result[Emotion.ANGRY] == 0.03

        # Verify SageMaker was called correctly
        mock_sagemaker_runtime_client.invoke_endpoint.assert_called_once()
        call_args = mock_sagemaker_runtime_client.invoke_endpoint.call_args

        # Verify request payload
        request_body = json.loads(call_args.kwargs["Body"])
        assert "features" in request_body
        assert len(request_body["features"]) == 180
        assert isinstance(request_body["features"][0], float)

        # Verify endpoint name
        assert call_args.kwargs["EndpointName"] == "ml-ser-endpoint4"
        assert call_args.kwargs["ContentType"] == "application/json"

    def test_repository_caches_adapter(
        self, mock_sagemaker_control_client, mock_sagemaker_runtime_client
    ):
        """Test repository caches adapter instance."""
        mock_sagemaker_control_client.describe_endpoint.return_value = {
            "EndpointStatus": "InService",
            "EndpointName": "ml-ser-endpoint4",
        }

        repository = SageMakerModelRepository(endpoint_name="ml-ser-endpoint4")
        version = ModelVersion.from_string("v5")

        # Load model twice
        model1 = repository.load_model(version)
        model2 = repository.load_model(version)

        # Should return same instance
        assert model1 is model2

    def test_endpoint_not_found_during_load(
        self, mock_sagemaker_control_client, mock_sagemaker_runtime_client
    ):
        """Test error when endpoint doesn't exist."""
        error_response = {
            "Error": {
                "Code": "ValidationError",
                "Message": "Could not find endpoint",
            }
        }
        mock_sagemaker_control_client.describe_endpoint.side_effect = ClientError(
            error_response, "DescribeEndpoint"
        )

        repository = SageMakerModelRepository(endpoint_name="ml-ser-endpoint4")
        version = ModelVersion.from_string("v5")

        with pytest.raises(Exception):  # ModelNotFoundError
            repository.load_model(version)

    def test_request_payload_format(
        self,
        mock_sagemaker_runtime_client,
        mock_sagemaker_control_client,
        valid_features,
        valid_sagemaker_response,
    ):
        """Test that request payload is correctly formatted for SageMaker."""
        mock_sagemaker_control_client.describe_endpoint.return_value = {
            "EndpointStatus": "InService",
            "EndpointName": "ml-ser-endpoint4",
        }

        mock_response = {
            "Body": Mock(read=Mock(return_value=json.dumps(valid_sagemaker_response).encode()))
        }
        mock_sagemaker_runtime_client.invoke_endpoint.return_value = mock_response

        # Create adapter and predict
        adapter = SageMakerEmotionModelAdapter(
            endpoint_name="ml-ser-endpoint4", region="us-east-1"
        )
        adapter.predict_emotion_probabilities(valid_features)

        # Extract request body
        call_args = mock_sagemaker_runtime_client.invoke_endpoint.call_args
        request_body_str = call_args.kwargs["Body"]
        request_body = json.loads(request_body_str)

        # Verify format matches expected SageMaker input
        assert "features" in request_body
        assert isinstance(request_body["features"], list)
        assert len(request_body["features"]) == 180
        assert all(isinstance(f, (int, float)) for f in request_body["features"])

        # Verify no other unexpected fields
        assert set(request_body.keys()) == {"features"}

    def test_response_parsing_with_all_emotions(
        self, mock_sagemaker_runtime_client, mock_sagemaker_control_client, valid_features
    ):
        """Test response parsing includes all 6 emotions."""
        mock_sagemaker_control_client.describe_endpoint.return_value = {
            "EndpointStatus": "InService",
            "EndpointName": "ml-ser-endpoint4",
        }

        sagemaker_response = {
            "emotion": "neutral",
            "confidence": 0.45,
            "probabilities": {
                "angry": 0.10,
                "disgust": 0.05,
                "fear": 0.15,
                "happy": 0.20,
                "neutral": 0.45,
                "sad": 0.05,
            },
            "model_version": "v5",
        }

        mock_response = {
            "Body": Mock(read=Mock(return_value=json.dumps(sagemaker_response).encode()))
        }
        mock_sagemaker_runtime_client.invoke_endpoint.return_value = mock_response

        adapter = SageMakerEmotionModelAdapter(
            endpoint_name="ml-ser-endpoint4", region="us-east-1"
        )
        result = adapter.predict_emotion_probabilities(valid_features)

        # Verify all emotions present
        expected_emotions = {
            Emotion.ANGRY,
            Emotion.DISGUST,
            Emotion.FEAR,
            Emotion.HAPPY,
            Emotion.NEUTRAL,
            Emotion.SAD,
        }
        assert set(result.keys()) == expected_emotions

        # Verify values match
        assert result[Emotion.ANGRY] == 0.10
        assert result[Emotion.DISGUST] == 0.05
        assert result[Emotion.FEAR] == 0.15
        assert result[Emotion.HAPPY] == 0.20
        assert result[Emotion.NEUTRAL] == 0.45
        assert result[Emotion.SAD] == 0.05

        # Verify probabilities sum to 1.0
        assert abs(sum(result.values()) - 1.0) < 0.01

    def test_model_info_retrieval(self, mock_sagemaker_control_client, mock_sagemaker_runtime_client):
        """Test retrieving model metadata from SageMaker endpoint."""
        from datetime import datetime

        creation_time = datetime(2025, 1, 1, 12, 0, 0)
        mock_sagemaker_control_client.describe_endpoint.return_value = {
            "EndpointStatus": "InService",
            "EndpointName": "ml-ser-endpoint4",
            "EndpointArn": "arn:aws:sagemaker:us-east-1:123456789:endpoint/ml-ser-endpoint4",
            "CreationTime": creation_time,
        }

        mock_sagemaker_control_client.list_tags.return_value = {
            "Tags": [
                {"Key": "model_type", "Value": "UltraEnsembleModel"},
                {"Key": "feature_dimension", "Value": "180"},
                {"Key": "sklearn_version", "Value": "1.7.2"},
            ]
        }

        repository = SageMakerModelRepository(endpoint_name="ml-ser-endpoint4")
        version = ModelVersion.from_string("v5")
        model_info = repository.get_model_info(version)

        assert model_info is not None
        assert model_info.model_type == "UltraEnsembleModel"
        assert model_info.feature_dimension == 180
        assert model_info.sklearn_version == "1.7.2"
        assert "InService" in model_info.notes
