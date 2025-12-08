"""Unit tests for SageMakerModelRepository."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.domain.model.exceptions.model_not_found_error import ModelNotFoundError
from app.domain.model.exceptions.sagemaker_authentication_error import (
    SageMakerAuthenticationError,
)
from app.domain.model.value_objects.model_version import ModelVersion
from app.infrastructure.model.sagemaker_emotion_model_adapter import (
    SageMakerEmotionModelAdapter,
)
from app.infrastructure.model.sagemaker_model_repository import SageMakerModelRepository


class TestSageMakerModelRepository:
    """Test suite for SageMakerModelRepository."""

    @pytest.fixture
    def mock_boto3_client(self):
        """Mock boto3 SageMaker client."""
        with patch("app.infrastructure.model.sagemaker_model_repository.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def repository(self, mock_boto3_client):
        """Create SageMakerModelRepository instance."""
        return SageMakerModelRepository(
            endpoint_name="ml-ser-endpoint4",
            region="us-east-1",
            timeout_seconds=30,
            max_retries=3,
        )

    @pytest.fixture
    def model_version(self):
        """Create model version."""
        return ModelVersion.from_string("v5")

    def test_repository_initialization(self, mock_boto3_client):
        """Test repository initializes correctly."""
        repo = SageMakerModelRepository(
            endpoint_name="test-endpoint",
            region="us-west-2",
            timeout_seconds=60,
            max_retries=5,
        )

        assert repo.endpoint_name == "test-endpoint"
        assert repo.region == "us-west-2"
        assert repo.timeout_seconds == 60
        assert repo.max_retries == 5
        assert repo.sagemaker_client is not None

    def test_load_model_success(self, repository, mock_boto3_client, model_version):
        """Test successful model loading."""
        # Mock endpoint status
        mock_boto3_client.describe_endpoint.return_value = {
            "EndpointStatus": "InService",
            "EndpointName": "ml-ser-endpoint4",
        }

        # Load model
        model = repository.load_model(model_version)

        # Verify adapter created
        assert isinstance(model, SageMakerEmotionModelAdapter)
        assert model.endpoint_name == "ml-ser-endpoint4"
        assert model.region == "us-east-1"

    def test_load_model_caching(self, repository, mock_boto3_client, model_version):
        """Test model adapter is cached after first load."""
        # Mock endpoint status
        mock_boto3_client.describe_endpoint.return_value = {
            "EndpointStatus": "InService",
            "EndpointName": "ml-ser-endpoint4",
        }

        # Load model twice
        model1 = repository.load_model(model_version)
        model2 = repository.load_model(model_version)

        # Should return same instance (cached)
        assert model1 is model2

    def test_load_model_endpoint_not_found(
        self, repository, mock_boto3_client, model_version
    ):
        """Test loading model when endpoint doesn't exist."""
        error_response = {
            "Error": {
                "Code": "ValidationError",
                "Message": "Could not find endpoint",
            }
        }
        mock_boto3_client.describe_endpoint.side_effect = ClientError(
            error_response, "DescribeEndpoint"
        )

        with pytest.raises(ModelNotFoundError) as exc_info:
            repository.load_model(model_version)

        assert "ml-ser-endpoint4" in str(exc_info.value)

    def test_load_model_endpoint_not_in_service(
        self, repository, mock_boto3_client, model_version
    ):
        """Test loading model when endpoint is not InService."""
        mock_boto3_client.describe_endpoint.return_value = {
            "EndpointStatus": "Creating",  # Not InService
            "EndpointName": "ml-ser-endpoint4",
        }

        with pytest.raises(ModelNotFoundError) as exc_info:
            repository.load_model(model_version)

        assert "not in service" in str(exc_info.value).lower()

    def test_get_model_info_success(self, repository, mock_boto3_client, model_version):
        """Test getting model info successfully."""
        creation_time = datetime(2025, 1, 1, 12, 0, 0)
        mock_boto3_client.describe_endpoint.return_value = {
            "EndpointStatus": "InService",
            "EndpointName": "ml-ser-endpoint4",
            "EndpointArn": "arn:aws:sagemaker:us-east-1:123456789:endpoint/ml-ser-endpoint4",
            "CreationTime": creation_time,
        }

        mock_boto3_client.list_tags.return_value = {
            "Tags": [
                {"Key": "model_type", "Value": "UltraEnsembleModel"},
                {"Key": "feature_dimension", "Value": "180"},
                {"Key": "sklearn_version", "Value": "1.7.2"},
                {"Key": "num_classes", "Value": "6"},
            ]
        }

        model_info = repository.get_model_info(model_version)

        assert model_info is not None
        assert model_info.version == model_version
        assert model_info.model_type == "UltraEnsembleModel"
        assert model_info.feature_dimension == 180
        assert model_info.sklearn_version == "1.7.2"
        assert model_info.num_classes == 6
        assert "ml-ser-endpoint4" in model_info.notes

    def test_get_model_info_endpoint_not_found(
        self, repository, mock_boto3_client, model_version
    ):
        """Test getting model info when endpoint doesn't exist."""
        error_response = {
            "Error": {
                "Code": "ResourceNotFoundException",
                "Message": "Endpoint not found",
            }
        }
        mock_boto3_client.describe_endpoint.side_effect = ClientError(
            error_response, "DescribeEndpoint"
        )

        model_info = repository.get_model_info(model_version)

        assert model_info is None

    def test_get_model_info_without_tags(
        self, repository, mock_boto3_client, model_version
    ):
        """Test getting model info when tags are unavailable."""
        creation_time = datetime(2025, 1, 1, 12, 0, 0)
        mock_boto3_client.describe_endpoint.return_value = {
            "EndpointStatus": "InService",
            "EndpointName": "ml-ser-endpoint4",
            "EndpointArn": "arn:aws:sagemaker:us-east-1:123456789:endpoint/ml-ser-endpoint4",
            "CreationTime": creation_time,
        }

        # Tags request fails
        mock_boto3_client.list_tags.side_effect = Exception("Access denied")

        model_info = repository.get_model_info(model_version)

        # Should still return info with defaults
        assert model_info is not None
        assert model_info.model_type == "sklearn.pipeline.Pipeline"  # Default for v6+
        assert model_info.feature_dimension == 210  # Default for v6+

    def test_list_available_versions(self, repository, mock_boto3_client):
        """Test listing available versions."""
        creation_time = datetime(2025, 1, 1, 12, 0, 0)
        mock_boto3_client.describe_endpoint.return_value = {
            "EndpointStatus": "InService",
            "EndpointName": "ml-ser-endpoint4",
            "EndpointArn": "arn:aws:sagemaker:us-east-1:123456789:endpoint/ml-ser-endpoint4",
            "CreationTime": creation_time,
        }

        mock_boto3_client.list_tags.return_value = {"Tags": []}

        versions = repository.list_available_versions()

        assert len(versions) == 1
        assert versions[0] == ModelVersion.from_string("v5")

    def test_list_available_versions_endpoint_not_available(
        self, repository, mock_boto3_client
    ):
        """Test listing versions when endpoint is not available."""
        error_response = {
            "Error": {
                "Code": "ResourceNotFoundException",
                "Message": "Endpoint not found",
            }
        }
        mock_boto3_client.describe_endpoint.side_effect = ClientError(
            error_response, "DescribeEndpoint"
        )

        versions = repository.list_available_versions()

        assert len(versions) == 0

    def test_model_exists_true(self, repository, mock_boto3_client, model_version):
        """Test model exists returns True when endpoint is InService."""
        mock_boto3_client.describe_endpoint.return_value = {
            "EndpointStatus": "InService",
            "EndpointName": "ml-ser-endpoint4",
        }

        exists = repository.model_exists(model_version)

        assert exists is True

    def test_model_exists_false_not_in_service(
        self, repository, mock_boto3_client, model_version
    ):
        """Test model exists returns False when endpoint is not InService."""
        mock_boto3_client.describe_endpoint.return_value = {
            "EndpointStatus": "Updating",
            "EndpointName": "ml-ser-endpoint4",
        }

        exists = repository.model_exists(model_version)

        assert exists is False

    def test_model_exists_false_not_found(
        self, repository, mock_boto3_client, model_version
    ):
        """Test model exists returns False when endpoint doesn't exist."""
        error_response = {
            "Error": {
                "Code": "ValidationError",
                "Message": "Could not find endpoint",
            }
        }
        mock_boto3_client.describe_endpoint.side_effect = ClientError(
            error_response, "DescribeEndpoint"
        )

        exists = repository.model_exists(model_version)

        assert exists is False

    def test_model_exists_authentication_error(
        self, repository, mock_boto3_client, model_version
    ):
        """Test model exists raises authentication error."""
        error_response = {
            "Error": {
                "Code": "AccessDeniedException",
                "Message": "User is not authorized",
            }
        }
        mock_boto3_client.describe_endpoint.side_effect = ClientError(
            error_response, "DescribeEndpoint"
        )

        with pytest.raises(SageMakerAuthenticationError):
            repository.model_exists(model_version)

    def test_get_latest_version(self, repository, mock_boto3_client):
        """Test getting latest version."""
        creation_time = datetime(2025, 1, 1, 12, 0, 0)
        mock_boto3_client.describe_endpoint.return_value = {
            "EndpointStatus": "InService",
            "EndpointName": "ml-ser-endpoint4",
            "EndpointArn": "arn:aws:sagemaker:us-east-1:123456789:endpoint/ml-ser-endpoint4",
            "CreationTime": creation_time,
        }

        mock_boto3_client.list_tags.return_value = {"Tags": []}

        latest = repository.get_latest_version()

        assert latest is not None
        assert latest == ModelVersion.from_string("v5")

    def test_get_latest_version_none(self, repository, mock_boto3_client):
        """Test getting latest version when no endpoint available."""
        error_response = {
            "Error": {
                "Code": "ResourceNotFoundException",
                "Message": "Endpoint not found",
            }
        }
        mock_boto3_client.describe_endpoint.side_effect = ClientError(
            error_response, "DescribeEndpoint"
        )

        latest = repository.get_latest_version()

        assert latest is None
