"""
Unit tests for SageMakerService.

Tests the SageMaker client functionality including:
- Initialization and client setup
- Prediction with retry logic
- Health checks
- Endpoint management (disable/reenable)
- Error handling
"""

import json
import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from botocore.exceptions import BotoCoreError, ClientError, ConnectionError, ReadTimeoutError

from app.infrastructure.ml.sagemaker_client import (
    SageMakerConnectionError,
    SageMakerPredictionError,
    SageMakerService,
    SageMakerServiceError,
)


class TestSageMakerServiceInitialization:
    """Test SageMaker service initialization."""

    @patch("app.infrastructure.ml.sagemaker_client.boto3")
    @patch("app.infrastructure.ml.sagemaker_client.get_settings")
    def test_initialization_success(self, mock_get_settings, mock_boto3):
        """Test successful initialization of SageMaker service."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.aws_region = "us-east-1"
        mock_settings.sagemaker_endpoint_name = "test-endpoint"
        mock_get_settings.return_value = mock_settings

        mock_session = Mock()
        mock_boto3.Session.return_value = mock_session
        mock_runtime_client = Mock()
        mock_sagemaker_client = Mock()
        mock_session.client.side_effect = [mock_runtime_client, mock_sagemaker_client]

        # Create service
        service = SageMakerService()

        # Verify initialization
        assert service.settings == mock_settings
        assert service.runtime_client == mock_runtime_client
        assert service.sagemaker_client == mock_sagemaker_client
        mock_boto3.Session.assert_called_once_with(region_name="us-east-1")

    @patch("app.infrastructure.ml.sagemaker_client.boto3")
    @patch("app.infrastructure.ml.sagemaker_client.get_settings")
    def test_initialization_failure(self, mock_get_settings, mock_boto3):
        """Test initialization failure raises SageMakerConnectionError."""
        # Setup mocks
        mock_settings = Mock()
        mock_settings.aws_region = "us-east-1"
        mock_get_settings.return_value = mock_settings

        mock_boto3.Session.side_effect = Exception("AWS credentials not found")

        # Should raise SageMakerConnectionError
        with pytest.raises(SageMakerConnectionError) as exc_info:
            SageMakerService()

        assert "Failed to initialize SageMaker client" in str(exc_info.value)


class TestSageMakerServicePrediction:
    """Test emotion prediction functionality."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock SageMaker service."""
        with patch("app.infrastructure.ml.sagemaker_client.boto3"), patch(
            "app.infrastructure.ml.sagemaker_client.get_settings"
        ) as mock_get_settings:
            mock_settings = Mock()
            mock_settings.aws_region = "us-east-1"
            mock_settings.sagemaker_endpoint_name = "test-endpoint"
            mock_get_settings.return_value = mock_settings

            service = SageMakerService()
            service.runtime_client = Mock()
            service.sagemaker_client = Mock()
            return service

    @pytest.mark.asyncio
    async def test_predict_emotion_success(self, mock_service):
        """Test successful emotion prediction."""
        # Setup mock response
        mock_response = {
            "Body": Mock(),
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        response_data = {
            "predicted_emotion": "happy",
            "confidence": 0.85,
            "all_emotions": {
                "angry": 0.05,
                "disgust": 0.02,
                "fear": 0.03,
                "happy": 0.85,
                "neutral": 0.03,
                "sad": 0.02,
            },
        }
        mock_response["Body"].read.return_value = json.dumps(response_data).encode("utf-8")
        mock_service.runtime_client.invoke_endpoint.return_value = mock_response

        # Make prediction
        audio_base64 = "dGVzdCBhdWRpbyBkYXRh"  # "test audio data" in base64
        result = await mock_service.predict_emotion(audio_base64, sample_rate=16000)

        # Verify result
        assert result["predicted_emotion"] == "happy"
        assert result["confidence"] == 0.85
        assert "invocation_time" in result
        assert "response_size" in result
        assert "attempt" in result
        assert result["attempt"] == 1

        # Verify endpoint was called
        mock_service.runtime_client.invoke_endpoint.assert_called_once()
        call_kwargs = mock_service.runtime_client.invoke_endpoint.call_args[1]
        assert call_kwargs["EndpointName"] == "test-endpoint"
        assert call_kwargs["ContentType"] == "application/json"
        assert call_kwargs["Accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_predict_emotion_empty_audio(self, mock_service):
        """Test prediction with empty audio raises error."""
        with pytest.raises(SageMakerPredictionError) as exc_info:
            await mock_service.predict_emotion("", sample_rate=16000)

        assert "Audio data cannot be empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_predict_emotion_no_endpoint_configured(self, mock_service):
        """Test prediction without endpoint name raises error."""
        mock_service.settings.sagemaker_endpoint_name = None

        with pytest.raises(SageMakerPredictionError) as exc_info:
            await mock_service.predict_emotion("dGVzdA==", sample_rate=16000)

        assert "SageMaker endpoint name not configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_predict_emotion_missing_predicted_emotion(self, mock_service):
        """Test prediction with invalid response format."""
        # Setup mock response without predicted_emotion
        mock_response = {"Body": Mock()}
        response_data = {"confidence": 0.85}  # Missing predicted_emotion
        mock_response["Body"].read.return_value = json.dumps(response_data).encode("utf-8")
        mock_service.runtime_client.invoke_endpoint.return_value = mock_response

        with pytest.raises(SageMakerPredictionError) as exc_info:
            await mock_service.predict_emotion("dGVzdA==", sample_rate=16000)

        assert "missing predicted_emotion" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_predict_emotion_missing_confidence(self, mock_service):
        """Test prediction with missing confidence."""
        # Setup mock response without confidence
        mock_response = {"Body": Mock()}
        response_data = {"predicted_emotion": "happy"}  # Missing confidence
        mock_response["Body"].read.return_value = json.dumps(response_data).encode("utf-8")
        mock_service.runtime_client.invoke_endpoint.return_value = mock_response

        with pytest.raises(SageMakerPredictionError) as exc_info:
            await mock_service.predict_emotion("dGVzdA==", sample_rate=16000)

        assert "missing confidence" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_predict_emotion_invalid_confidence_value(self, mock_service):
        """Test prediction with invalid confidence value."""
        # Setup mock response with invalid confidence
        mock_response = {"Body": Mock()}
        response_data = {
            "predicted_emotion": "happy",
            "confidence": "not_a_number",
        }
        mock_response["Body"].read.return_value = json.dumps(response_data).encode("utf-8")
        mock_service.runtime_client.invoke_endpoint.return_value = mock_response

        with pytest.raises(SageMakerPredictionError) as exc_info:
            await mock_service.predict_emotion("dGVzdA==", sample_rate=16000)

        assert "Invalid confidence value" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_predict_emotion_confidence_out_of_range(self, mock_service):
        """Test prediction with confidence out of valid range logs warning."""
        # Setup mock response with confidence > 1
        mock_response = {"Body": Mock()}
        response_data = {
            "predicted_emotion": "happy",
            "confidence": 1.5,  # Out of range
        }
        mock_response["Body"].read.return_value = json.dumps(response_data).encode("utf-8")
        mock_service.runtime_client.invoke_endpoint.return_value = mock_response

        # Should succeed but log warning
        result = await mock_service.predict_emotion("dGVzdA==", sample_rate=16000)
        assert result["confidence"] == 1.5


class TestSageMakerServiceRetryLogic:
    """Test retry logic for SageMaker invocations."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock SageMaker service."""
        with patch("app.infrastructure.ml.sagemaker_client.boto3"), patch(
            "app.infrastructure.ml.sagemaker_client.get_settings"
        ) as mock_get_settings:
            mock_settings = Mock()
            mock_settings.aws_region = "us-east-1"
            mock_settings.sagemaker_endpoint_name = "test-endpoint"
            mock_get_settings.return_value = mock_settings

            service = SageMakerService()
            service.runtime_client = Mock()
            service.sagemaker_client = Mock()
            return service

    @pytest.mark.asyncio
    @patch("app.infrastructure.ml.sagemaker_client.time.sleep")
    async def test_retry_on_connection_error(self, mock_sleep, mock_service):
        """Test retry logic on connection errors."""
        # Setup mock to fail twice then succeed
        mock_response = {"Body": Mock()}
        response_data = {"predicted_emotion": "happy", "confidence": 0.85}
        mock_response["Body"].read.return_value = json.dumps(response_data).encode("utf-8")

        # Use BotoCoreError for testing retry logic
        error1 = BotoCoreError()
        error2 = BotoCoreError()

        mock_service.runtime_client.invoke_endpoint.side_effect = [
            error1,
            error2,
            mock_response,
        ]

        # Make prediction with retries
        result = await mock_service.predict_emotion("dGVzdA==", sample_rate=16000, max_retries=3)

        # Verify retries occurred
        assert mock_service.runtime_client.invoke_endpoint.call_count == 3
        assert result["predicted_emotion"] == "happy"
        assert result["attempt"] == 3
        assert mock_sleep.call_count == 2  # Two retries

    @pytest.mark.asyncio
    @patch("app.infrastructure.ml.sagemaker_client.time.sleep")
    async def test_retry_on_timeout_error(self, mock_sleep, mock_service):
        """Test retry logic on timeout errors."""
        mock_response = {"Body": Mock()}
        response_data = {"predicted_emotion": "sad", "confidence": 0.75}
        mock_response["Body"].read.return_value = json.dumps(response_data).encode("utf-8")

        mock_service.runtime_client.invoke_endpoint.side_effect = [
            ReadTimeoutError(endpoint_url="http://test", error="Timeout"),
            mock_response,
        ]

        result = await mock_service.predict_emotion("dGVzdA==", sample_rate=16000, max_retries=2)

        assert mock_service.runtime_client.invoke_endpoint.call_count == 2
        assert result["attempt"] == 2

    @pytest.mark.asyncio
    @patch("app.infrastructure.ml.sagemaker_client.time.sleep")
    async def test_no_retry_on_validation_error(self, mock_sleep, mock_service):
        """Test that validation errors are not retried."""
        error_response = {"Error": {"Code": "ValidationError", "Message": "Invalid input"}}
        mock_service.runtime_client.invoke_endpoint.side_effect = ClientError(
            error_response, "InvokeEndpoint"
        )

        with pytest.raises(SageMakerPredictionError) as exc_info:
            await mock_service.predict_emotion("dGVzdA==", sample_rate=16000, max_retries=3)

        # Should not retry validation errors
        assert mock_service.runtime_client.invoke_endpoint.call_count == 1
        assert "SageMaker client error" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("app.infrastructure.ml.sagemaker_client.time.sleep")
    async def test_retry_on_retryable_client_error(self, mock_sleep, mock_service):
        """Test retry logic on retryable client errors."""
        mock_response = {"Body": Mock()}
        response_data = {"predicted_emotion": "happy", "confidence": 0.85}
        mock_response["Body"].read.return_value = json.dumps(response_data).encode("utf-8")

        error_response = {"Error": {"Code": "ThrottlingException", "Message": "Rate exceeded"}}
        mock_service.runtime_client.invoke_endpoint.side_effect = [
            ClientError(error_response, "InvokeEndpoint"),
            mock_response,
        ]

        result = await mock_service.predict_emotion("dGVzdA==", sample_rate=16000, max_retries=2)

        assert mock_service.runtime_client.invoke_endpoint.call_count == 2
        assert result["predicted_emotion"] == "happy"

    @pytest.mark.asyncio
    @patch("app.infrastructure.ml.sagemaker_client.time.sleep")
    async def test_max_retries_exceeded(self, mock_sleep, mock_service):
        """Test behavior when max retries are exceeded."""
        mock_service.runtime_client.invoke_endpoint.side_effect = BotoCoreError()

        with pytest.raises(SageMakerPredictionError) as exc_info:
            await mock_service.predict_emotion("dGVzdA==", sample_rate=16000, max_retries=2)

        assert "Failed to invoke SageMaker endpoint after 3 attempts" in str(exc_info.value)
        assert mock_service.runtime_client.invoke_endpoint.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    @patch("app.infrastructure.ml.sagemaker_client.time.sleep")
    async def test_exponential_backoff(self, mock_sleep, mock_service):
        """Test exponential backoff in retry logic."""
        mock_response = {"Body": Mock()}
        response_data = {"predicted_emotion": "happy", "confidence": 0.85}
        mock_response["Body"].read.return_value = json.dumps(response_data).encode("utf-8")

        error1 = BotoCoreError()
        error2 = BotoCoreError()

        mock_service.runtime_client.invoke_endpoint.side_effect = [
            error1,
            error2,
            mock_response,
        ]

        await mock_service.predict_emotion("dGVzdA==", sample_rate=16000, max_retries=3)

        # Verify exponential backoff: 0.5, 1.0
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(0.5)
        mock_sleep.assert_any_call(1.0)


class TestSageMakerServiceHealthCheck:
    """Test health check functionality."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock SageMaker service."""
        with patch("app.infrastructure.ml.sagemaker_client.boto3"), patch(
            "app.infrastructure.ml.sagemaker_client.get_settings"
        ) as mock_get_settings:
            mock_settings = Mock()
            mock_settings.aws_region = "us-east-1"
            mock_settings.sagemaker_endpoint_name = "test-endpoint"
            mock_get_settings.return_value = mock_settings

            service = SageMakerService()
            service.runtime_client = Mock()
            service.sagemaker_client = Mock()
            return service

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_service):
        """Test health check with healthy endpoint."""
        mock_response = {"Body": Mock(), "ResponseMetadata": {"HTTPStatusCode": 200}}
        mock_response["Body"].read.return_value = b'{"result": "ok"}'
        mock_service.runtime_client.invoke_endpoint.return_value = mock_response

        result = await mock_service.health_check()

        assert result["status"] == "healthy"
        assert result["endpoint"] == "test-endpoint"
        assert result["region"] == "us-east-1"
        assert result["accessible"] is True

    @pytest.mark.asyncio
    async def test_health_check_model_error(self, mock_service):
        """Test health check with model error (expected with test data)."""
        error_response = {"Error": {"Code": "ModelError", "Message": "Model processing error"}}
        mock_service.runtime_client.invoke_endpoint.side_effect = ClientError(
            error_response, "InvokeEndpoint"
        )

        result = await mock_service.health_check()

        assert result["status"] == "healthy"
        assert result["accessible"] is True
        assert "note" in result

    @pytest.mark.asyncio
    async def test_health_check_endpoint_not_found(self, mock_service):
        """Test health check with endpoint not found error."""
        error_response = {
            "Error": {"Code": "ValidationException", "Message": "Endpoint not found"}
        }
        mock_service.runtime_client.invoke_endpoint.side_effect = ClientError(
            error_response, "InvokeEndpoint"
        )

        result = await mock_service.health_check()

        assert result["status"] == "unhealthy"
        assert result["accessible"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_health_check_generic_exception(self, mock_service):
        """Test health check with generic exception."""
        mock_service.runtime_client.invoke_endpoint.side_effect = Exception("Unexpected error")

        result = await mock_service.health_check()

        assert result["status"] == "unhealthy"
        assert result["accessible"] is False
        assert "error" in result


class TestSageMakerServiceEndpointManagement:
    """Test endpoint management functionality."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock SageMaker service."""
        with patch("app.infrastructure.ml.sagemaker_client.boto3"), patch(
            "app.infrastructure.ml.sagemaker_client.get_settings"
        ) as mock_get_settings:
            mock_settings = Mock()
            mock_settings.aws_region = "us-east-1"
            mock_settings.sagemaker_endpoint_name = "test-endpoint"
            mock_get_settings.return_value = mock_settings

            service = SageMakerService()
            service.runtime_client = Mock()
            service.sagemaker_client = Mock()
            return service

    @pytest.mark.asyncio
    async def test_get_endpoint_info_success(self, mock_service):
        """Test getting endpoint information."""
        mock_response = {
            "EndpointName": "test-endpoint",
            "EndpointArn": "arn:aws:sagemaker:us-east-1:123456789:endpoint/test-endpoint",
            "EndpointStatus": "InService",
            "EndpointConfigName": "test-config",
            "CreationTime": "2024-01-01T00:00:00Z",
            "LastModifiedTime": "2024-01-02T00:00:00Z",
            "ProductionVariants": [{"VariantName": "AllTraffic", "InitialInstanceCount": 1}],
        }
        mock_service.sagemaker_client.describe_endpoint.return_value = mock_response

        result = await mock_service.get_endpoint_info()

        assert result["endpoint_name"] == "test-endpoint"
        assert result["endpoint_status"] == "InService"
        assert len(result["production_variants"]) == 1

    @pytest.mark.asyncio
    async def test_get_endpoint_info_not_found(self, mock_service):
        """Test getting endpoint info when endpoint doesn't exist."""
        error_response = {
            "Error": {"Code": "ValidationException", "Message": "Endpoint not found"}
        }
        mock_service.sagemaker_client.describe_endpoint.side_effect = ClientError(
            error_response, "DescribeEndpoint"
        )

        with pytest.raises(SageMakerServiceError) as exc_info:
            await mock_service.get_endpoint_info()

        assert "Failed to get endpoint info" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_endpoint_config_success(self, mock_service):
        """Test getting endpoint configuration."""
        mock_response = {
            "EndpointConfigName": "test-config",
            "EndpointConfigArn": "arn:aws:sagemaker:us-east-1:123456789:endpoint-config/test-config",
            "ProductionVariants": [
                {
                    "VariantName": "AllTraffic",
                    "ModelName": "test-model",
                    "InitialInstanceCount": 1,
                    "InstanceType": "ml.t2.medium",
                }
            ],
            "CreationTime": "2024-01-01T00:00:00Z",
        }
        mock_service.sagemaker_client.describe_endpoint_config.return_value = mock_response

        result = await mock_service.get_endpoint_config("test-config")

        assert result["config_name"] == "test-config"
        assert len(result["production_variants"]) == 1

    @pytest.mark.asyncio
    async def test_list_endpoints_success(self, mock_service):
        """Test listing endpoints."""
        mock_paginator = Mock()
        mock_service.sagemaker_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Endpoints": [
                    {"EndpointName": "endpoint-1", "EndpointStatus": "InService"},
                    {"EndpointName": "endpoint-2", "EndpointStatus": "InService"},
                ]
            }
        ]

        result = await mock_service.list_endpoints()

        assert result["count"] == 2
        assert len(result["endpoints"]) == 2
        assert result["region"] == "us-east-1"

    @pytest.mark.asyncio
    async def test_list_endpoints_with_filter(self, mock_service):
        """Test listing endpoints with status filter."""
        mock_paginator = Mock()
        mock_service.sagemaker_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Endpoints": [
                    {"EndpointName": "endpoint-1", "EndpointStatus": "InService"},
                    {"EndpointName": "endpoint-2", "EndpointStatus": "Failed"},
                ]
            }
        ]

        result = await mock_service.list_endpoints(status_filter="InService")

        assert result["count"] == 1
        assert result["endpoints"][0]["EndpointName"] == "endpoint-1"


class TestSageMakerServicePayloadHandling:
    """Test payload preparation and response parsing."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock SageMaker service."""
        with patch("app.infrastructure.ml.sagemaker_client.boto3"), patch(
            "app.infrastructure.ml.sagemaker_client.get_settings"
        ) as mock_get_settings:
            mock_settings = Mock()
            mock_settings.aws_region = "us-east-1"
            mock_settings.sagemaker_endpoint_name = "test-endpoint"
            mock_get_settings.return_value = mock_settings

            service = SageMakerService()
            service.runtime_client = Mock()
            service.sagemaker_client = Mock()
            return service

    def test_prepare_payload(self, mock_service):
        """Test payload preparation."""
        audio_base64 = "dGVzdCBhdWRpbyBkYXRh"
        sample_rate = 16000

        payload = mock_service._prepare_payload(audio_base64, sample_rate)

        # Verify payload is valid JSON
        payload_dict = json.loads(payload)
        assert payload_dict["audio_base64"] == audio_base64
        assert payload_dict["sample_rate"] == sample_rate

    def test_parse_response_bytes(self, mock_service):
        """Test parsing response from bytes."""
        response_data = {"predicted_emotion": "happy", "confidence": 0.85}
        response_body = json.dumps(response_data).encode("utf-8")

        result = mock_service._parse_response(response_body)

        assert result["predicted_emotion"] == "happy"
        assert result["confidence"] == 0.85

    def test_parse_response_string(self, mock_service):
        """Test parsing response from string."""
        response_data = {"predicted_emotion": "sad", "confidence": 0.75}
        response_body = json.dumps(response_data)

        result = mock_service._parse_response(response_body)

        assert result["predicted_emotion"] == "sad"
        assert result["confidence"] == 0.75

    def test_parse_response_invalid_json(self, mock_service):
        """Test parsing invalid JSON response."""
        response_body = b"invalid json"

        with pytest.raises(SageMakerPredictionError) as exc_info:
            mock_service._parse_response(response_body)

        assert "Invalid JSON response" in str(exc_info.value)

    def test_parse_response_invalid_type(self, mock_service):
        """Test parsing response with invalid type."""
        response_body = 12345  # Invalid type

        with pytest.raises(SageMakerPredictionError) as exc_info:
            mock_service._parse_response(response_body)

        assert "Unexpected response body type" in str(exc_info.value)


class TestSageMakerServiceSingleton:
    """Test singleton pattern for SageMaker service."""

    @patch("app.infrastructure.ml.sagemaker_client.boto3")
    @patch("app.infrastructure.ml.sagemaker_client.get_settings")
    def test_get_sagemaker_service_returns_singleton(self, mock_get_settings, mock_boto3):
        """Test that get_sagemaker_service returns the same instance."""
        from app.infrastructure.ml.sagemaker_client import get_sagemaker_service

        # Setup mocks
        mock_settings = Mock()
        mock_settings.aws_region = "us-east-1"
        mock_settings.sagemaker_endpoint_name = "test-endpoint"
        mock_get_settings.return_value = mock_settings

        # Reset global instance
        import app.infrastructure.ml.sagemaker_client as client_module

        client_module._sagemaker_service = None

        # Get instances
        service1 = get_sagemaker_service()
        service2 = get_sagemaker_service()

        # Verify same instance
        assert service1 is service2
        assert id(service1) == id(service2)


class TestSageMakerServiceDisableEndpoint:
    """Test disable endpoint functionality."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock SageMaker service."""
        with patch("app.infrastructure.ml.sagemaker_client.boto3"), patch(
            "app.infrastructure.ml.sagemaker_client.get_settings"
        ) as mock_get_settings:
            mock_settings = Mock()
            mock_settings.aws_region = "us-east-1"
            mock_settings.sagemaker_endpoint_name = "test-endpoint"
            mock_get_settings.return_value = mock_settings

            service = SageMakerService()
            service.runtime_client = Mock()
            service.sagemaker_client = Mock()
            return service

    @pytest.mark.asyncio
    async def test_disable_endpoint_already_disabled(self, mock_service):
        """Test disable endpoint when already disabled."""
        # Mock get_endpoint_info
        mock_service.sagemaker_client.describe_endpoint.return_value = {
            "EndpointName": "test-endpoint",
            "EndpointStatus": "InService",
            "EndpointConfigName": "test-config",
        }

        # Mock get_endpoint_config with 0 instances
        mock_service.sagemaker_client.describe_endpoint_config.return_value = {
            "EndpointConfigName": "test-config",
            "ProductionVariants": [
                {
                    "VariantName": "AllTraffic",
                    "ModelName": "test-model",
                    "InitialInstanceCount": 0,
                    "InstanceType": "ml.t2.medium",
                }
            ],
        }

        result = await mock_service.disable_endpoint()

        assert result["status"] == "already_disabled"
        assert result["current_instances"] == 0

    @pytest.mark.asyncio
    async def test_disable_endpoint_success_no_wait(self, mock_service):
        """Test successful disable without waiting."""
        # Mock get_endpoint_info
        mock_service.sagemaker_client.describe_endpoint.return_value = {
            "EndpointName": "test-endpoint",
            "EndpointStatus": "InService",
            "EndpointConfigName": "test-config",
        }

        # Mock get_endpoint_config with 1 instance
        mock_service.sagemaker_client.describe_endpoint_config.return_value = {
            "EndpointConfigName": "test-config",
            "ProductionVariants": [
                {
                    "VariantName": "AllTraffic",
                    "ModelName": "test-model",
                    "InitialInstanceCount": 1,
                    "InstanceType": "ml.t2.medium",
                    "InitialVariantWeight": 1.0,
                }
            ],
        }

        # Mock create_endpoint_config
        mock_service.sagemaker_client.create_endpoint_config.return_value = {}

        # Mock update_endpoint
        mock_service.sagemaker_client.update_endpoint.return_value = {}

        result = await mock_service.disable_endpoint(wait_for_completion=False)

        assert result["status"] == "initiated"
        assert result["previous_instances"] == 1

    @pytest.mark.asyncio
    async def test_disable_endpoint_config_already_exists(self, mock_service):
        """Test disable when config already exists."""
        # Mock get_endpoint_info
        mock_service.sagemaker_client.describe_endpoint.return_value = {
            "EndpointName": "test-endpoint",
            "EndpointStatus": "InService",
            "EndpointConfigName": "test-config",
        }

        # Mock get_endpoint_config
        mock_service.sagemaker_client.describe_endpoint_config.return_value = {
            "EndpointConfigName": "test-config",
            "ProductionVariants": [
                {
                    "VariantName": "AllTraffic",
                    "ModelName": "test-model",
                    "InitialInstanceCount": 1,
                    "InstanceType": "ml.t2.medium",
                }
            ],
        }

        # Mock create_endpoint_config to raise "already exists" error
        error_response = {
            "Error": {"Code": "ValidationException", "Message": "Endpoint config already exists"}
        }
        mock_service.sagemaker_client.create_endpoint_config.side_effect = ClientError(
            error_response, "CreateEndpointConfig"
        )

        # Mock update_endpoint
        mock_service.sagemaker_client.update_endpoint.return_value = {}

        result = await mock_service.disable_endpoint(wait_for_completion=False)

        assert result["status"] == "initiated"

    @pytest.mark.asyncio
    async def test_disable_endpoint_failure(self, mock_service):
        """Test disable endpoint failure."""
        # Mock get_endpoint_info to raise exception
        mock_service.sagemaker_client.describe_endpoint.side_effect = Exception("Network error")

        with pytest.raises(SageMakerServiceError) as exc_info:
            await mock_service.disable_endpoint()

        assert "Failed to disable endpoint" in str(exc_info.value)


class TestSageMakerServiceReenableEndpoint:
    """Test reenable endpoint functionality."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock SageMaker service."""
        with patch("app.infrastructure.ml.sagemaker_client.boto3"), patch(
            "app.infrastructure.ml.sagemaker_client.get_settings"
        ) as mock_get_settings:
            mock_settings = Mock()
            mock_settings.aws_region = "us-east-1"
            mock_settings.sagemaker_endpoint_name = "test-endpoint"
            mock_get_settings.return_value = mock_settings

            service = SageMakerService()
            service.runtime_client = Mock()
            service.sagemaker_client = Mock()
            return service

    @pytest.mark.asyncio
    async def test_reenable_endpoint_already_enabled(self, mock_service):
        """Test reenable endpoint when already enabled."""
        # Mock get_endpoint_info
        mock_service.sagemaker_client.describe_endpoint.return_value = {
            "EndpointName": "test-endpoint",
            "EndpointStatus": "InService",
            "EndpointConfigName": "test-config",
        }

        # Mock get_endpoint_config with 1 instance
        mock_service.sagemaker_client.describe_endpoint_config.return_value = {
            "EndpointConfigName": "test-config",
            "ProductionVariants": [
                {
                    "VariantName": "AllTraffic",
                    "ModelName": "test-model",
                    "InitialInstanceCount": 1,
                    "InstanceType": "ml.t2.medium",
                }
            ],
        }

        result = await mock_service.reenable_endpoint()

        assert result["status"] == "already_enabled"
        assert result["current_instances"] == 1

    @pytest.mark.asyncio
    async def test_reenable_endpoint_no_config_specified(self, mock_service):
        """Test reenable endpoint without specifying config."""
        # Mock get_endpoint_info
        mock_service.sagemaker_client.describe_endpoint.return_value = {
            "EndpointName": "test-endpoint",
            "EndpointStatus": "InService",
            "EndpointConfigName": "test-endpoint-disabled-config",
        }

        # Mock get_endpoint_config with 0 instances (disabled)
        mock_service.sagemaker_client.describe_endpoint_config.return_value = {
            "EndpointConfigName": "test-endpoint-disabled-config",
            "ProductionVariants": [
                {
                    "VariantName": "AllTraffic",
                    "ModelName": "test-model",
                    "InitialInstanceCount": 0,
                    "InstanceType": "ml.t2.medium",
                }
            ],
        }

        # Mock list_endpoint_configs (paginator)
        mock_paginator = Mock()
        mock_service.sagemaker_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "EndpointConfigs": [
                    {"EndpointConfigName": "test-endpoint-disabled-config"},
                    {"EndpointConfigName": "test-config-original"},
                ]
            }
        ]

        # Mock second describe_endpoint_config for original config
        def describe_config_side_effect(EndpointConfigName):
            if "disabled" in EndpointConfigName:
                return {
                    "EndpointConfigName": EndpointConfigName,
                    "ProductionVariants": [
                        {"VariantName": "AllTraffic", "ModelName": "test-model", "InitialInstanceCount": 0, "InstanceType": "ml.t2.medium"}
                    ],
                }
            else:
                return {
                    "EndpointConfigName": EndpointConfigName,
                    "ProductionVariants": [
                        {"VariantName": "AllTraffic", "ModelName": "test-model", "InitialInstanceCount": 1, "InstanceType": "ml.t2.medium"}
                    ],
                }

        mock_service.sagemaker_client.describe_endpoint_config.side_effect = describe_config_side_effect

        # Mock update_endpoint
        mock_service.sagemaker_client.update_endpoint.return_value = {}

        result = await mock_service.reenable_endpoint(wait_for_completion=False)

        assert result["status"] == "initiated"

    @pytest.mark.asyncio
    async def test_reenable_endpoint_failure(self, mock_service):
        """Test reenable endpoint failure."""
        mock_service.sagemaker_client.describe_endpoint.side_effect = Exception("Network error")

        with pytest.raises(SageMakerServiceError) as exc_info:
            await mock_service.reenable_endpoint()

        assert "Failed to re-enable endpoint" in str(exc_info.value)


class TestSageMakerServiceGetEndpointConfigError:
    """Test get_endpoint_config error handling."""

    @pytest.fixture
    def mock_service(self):
        """Create a mock SageMaker service."""
        with patch("app.infrastructure.ml.sagemaker_client.boto3"), patch(
            "app.infrastructure.ml.sagemaker_client.get_settings"
        ) as mock_get_settings:
            mock_settings = Mock()
            mock_settings.aws_region = "us-east-1"
            mock_settings.sagemaker_endpoint_name = "test-endpoint"
            mock_get_settings.return_value = mock_settings

            service = SageMakerService()
            service.runtime_client = Mock()
            service.sagemaker_client = Mock()
            return service

    @pytest.mark.asyncio
    async def test_get_endpoint_config_error(self, mock_service):
        """Test get_endpoint_config error handling."""
        error_response = {
            "Error": {"Code": "ValidationException", "Message": "Config not found"}
        }
        mock_service.sagemaker_client.describe_endpoint_config.side_effect = ClientError(
            error_response, "DescribeEndpointConfig"
        )

        with pytest.raises(SageMakerServiceError) as exc_info:
            await mock_service.get_endpoint_config("nonexistent-config")

        assert "Failed to get endpoint config" in str(exc_info.value)
