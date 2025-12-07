"""SageMaker-based model repository implementation."""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.domain.model.entities.emotion_model import EmotionModel
from app.domain.model.entities.model_info import ModelInfo
from app.domain.model.exceptions.inference_error import InferenceError
from app.domain.model.exceptions.model_not_found_error import ModelNotFoundError
from app.domain.model.exceptions.sagemaker_authentication_error import (
    SageMakerAuthenticationError,
)
from app.domain.model.exceptions.sagemaker_endpoint_not_found_error import (
    SageMakerEndpointNotFoundError,
)
from app.domain.model.repositories.model_repository import ModelRepository
from app.domain.model.value_objects.model_version import ModelVersion
from app.infrastructure.model.sagemaker_emotion_model_adapter import (
    SageMakerEmotionModelAdapter,
)
from app.infrastructure.observability.logging import get_logger


class SageMakerModelRepository(ModelRepository):
    """SageMaker-based implementation of ModelRepository.

    This implementation uses AWS SageMaker endpoints for model inference.
    Feature extraction remains in the backend API (LibrosaAudioProcessor),
    and only model inference is delegated to SageMaker.

    Architecture:
    - Backend API: Feature extraction (audio -> 180 features)
    - SageMaker: Model inference (180 features -> emotion probabilities)

    The repository handles:
    - Loading model metadata from SageMaker endpoint tags
    - Creating SageMakerEmotionModelAdapter instances
    - Checking endpoint status (InService, OutOfService, etc.)
    - Error mapping from SageMaker to domain exceptions

    Clean Architecture compliance:
    - Implements domain ModelRepository interface
    - Depends on domain abstractions (EmotionModel, ModelVersion)
    - Infrastructure concerns isolated (boto3, SageMaker SDK)
    """

    def __init__(
        self,
        endpoint_name: str,
        region: str = "us-east-1",
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ):
        """Initialize SageMaker model repository.

        Args:
            endpoint_name: SageMaker endpoint name (single endpoint for all versions)
            region: AWS region (default: us-east-1)
            timeout_seconds: Timeout for endpoint invocation (default: 30)
            max_retries: Maximum retries for transient errors (default: 3)
        """
        self.endpoint_name = endpoint_name
        self.region = region
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.logger = get_logger(__name__)

        # Configure boto3 client for SageMaker control plane operations
        # (describe endpoint, list endpoints, get tags, etc.)
        config = Config(
            region_name=region,
            connect_timeout=10,
            read_timeout=30,
        )

        # Initialize SageMaker client (control plane, not runtime)
        try:
            self.sagemaker_client = boto3.client("sagemaker", config=config)
            self.logger.info(
                "SageMaker repository initialized",
                endpoint_name=endpoint_name,
                region=region,
            )
        except Exception as e:
            self.logger.error(
                "Failed to initialize SageMaker client",
                error=str(e),
                region=region,
            )
            raise InferenceError(f"Failed to initialize SageMaker client: {str(e)}")

        # Cache for loaded adapter (reuse same adapter for all requests)
        self._adapter_cache: SageMakerEmotionModelAdapter | None = None

    def load_model(self, version: ModelVersion) -> EmotionModel:
        """Load model by returning SageMaker adapter.

        In SageMaker deployment, the model version is implicit in the endpoint configuration.
        This method simply returns an adapter that invokes the configured endpoint.

        Note: The version parameter is currently ignored because we use a single endpoint.
        In the future, you could:
        - Map version to different endpoints
        - Include version in request payload
        - Use SageMaker model variants for A/B testing

        Args:
            version: Model version (currently ignored, single endpoint used)

        Returns:
            SageMakerEmotionModelAdapter configured for the endpoint

        Raises:
            ModelNotFoundError: If endpoint doesn't exist or is not in service
            InferenceError: If adapter creation fails
        """
        self.logger.info(
            "Loading SageMaker model",
            version=str(version),
            endpoint_name=self.endpoint_name,
        )

        # Verify endpoint exists and is in service
        if not self.model_exists(version):
            raise ModelNotFoundError(
                f"SageMaker endpoint '{self.endpoint_name}' not found or not in service"
            )

        try:
            # Return cached adapter if available (reuse for performance)
            if self._adapter_cache is None:
                self._adapter_cache = SageMakerEmotionModelAdapter(
                    endpoint_name=self.endpoint_name,
                    region=self.region,
                    timeout_seconds=self.timeout_seconds,
                    max_retries=self.max_retries,
                )

                self.logger.info(
                    "SageMaker adapter created",
                    endpoint_name=self.endpoint_name,
                    version=str(version),
                )
            else:
                self.logger.debug(
                    "Using cached SageMaker adapter",
                    endpoint_name=self.endpoint_name,
                )

            return self._adapter_cache

        except Exception as e:
            self.logger.error(
                "Failed to create SageMaker adapter",
                version=str(version),
                error=str(e),
            )
            raise InferenceError(
                f"Failed to create SageMaker adapter for {str(version)}: {str(e)}"
            )

    def get_model_info(self, version: ModelVersion) -> ModelInfo | None:
        """Get metadata about the SageMaker endpoint.

        Retrieves metadata from SageMaker endpoint tags and configuration.
        This is useful for displaying model information without running inference.

        Args:
            version: Model version (currently ignored, single endpoint used)

        Returns:
            ModelInfo if endpoint exists, None otherwise
        """
        try:
            # Describe endpoint to get metadata
            response = self.sagemaker_client.describe_endpoint(
                EndpointName=self.endpoint_name
            )

            endpoint_status = response.get("EndpointStatus")
            creation_time = response.get("CreationTime")
            endpoint_arn = response.get("EndpointArn")

            # Get endpoint tags for additional metadata
            tags = {}
            try:
                tags_response = self.sagemaker_client.list_tags(ResourceArn=endpoint_arn)
                tags = {tag["Key"]: tag["Value"] for tag in tags_response.get("Tags", [])}
            except Exception as e:
                self.logger.warning(
                    "Failed to retrieve endpoint tags",
                    endpoint_name=self.endpoint_name,
                    error=str(e),
                )

            # Extract metadata from tags or use defaults
            model_type = tags.get("model_type", "UltraEnsembleModel")
            feature_dimension = int(tags.get("feature_dimension", 180))
            model_name = tags.get("model_name", "SageMaker Emotion Recognition Model")
            sklearn_version = tags.get("sklearn_version", "1.7.2")
            num_classes = int(tags.get("num_classes", 6))

            return ModelInfo(
                version=version,
                model_type=model_type,
                feature_dimension=feature_dimension,
                model_name=model_name,
                sklearn_version=sklearn_version,
                created_date=creation_time.isoformat() if creation_time else None,
                num_classes=num_classes,
                notes=f"SageMaker endpoint: {self.endpoint_name} (status: {endpoint_status})",
            )

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            if error_code in ["ValidationError", "ResourceNotFoundException"]:
                self.logger.warning(
                    "SageMaker endpoint not found",
                    endpoint_name=self.endpoint_name,
                )
                return None

            self.logger.error(
                "Failed to get endpoint metadata",
                endpoint_name=self.endpoint_name,
                error_code=error_code,
            )
            return None

        except Exception as e:
            self.logger.error(
                "Unexpected error getting endpoint metadata",
                endpoint_name=self.endpoint_name,
                error=str(e),
            )
            return None

    def list_available_versions(self) -> list[ModelVersion]:
        """List available model versions.

        For SageMaker deployment with single endpoint, this returns a single
        version based on endpoint tags or a default version.

        In a more advanced setup, you could:
        - List all endpoints with a specific tag
        - Map endpoint names to versions
        - Query endpoint variants for multi-model deployment

        Returns:
            List containing single version (endpoint's version)
        """
        # Get endpoint metadata to determine version
        model_info = self.get_model_info(ModelVersion.from_string("v5"))

        if model_info:
            return [model_info.version]
        else:
            # Endpoint not available
            self.logger.warning(
                "No SageMaker endpoint available",
                endpoint_name=self.endpoint_name,
            )
            return []

    def model_exists(self, version: ModelVersion) -> bool:
        """Check if SageMaker endpoint exists and is in service.

        Args:
            version: Model version (currently ignored, single endpoint checked)

        Returns:
            True if endpoint exists and is InService, False otherwise
        """
        try:
            response = self.sagemaker_client.describe_endpoint(
                EndpointName=self.endpoint_name
            )

            endpoint_status = response.get("EndpointStatus")

            # Endpoint must be InService to be considered available
            is_available = endpoint_status == "InService"

            self.logger.debug(
                "Checked endpoint status",
                endpoint_name=self.endpoint_name,
                status=endpoint_status,
                is_available=is_available,
            )

            return is_available

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            if error_code in ["ValidationError", "ResourceNotFoundException"]:
                self.logger.debug(
                    "SageMaker endpoint not found",
                    endpoint_name=self.endpoint_name,
                )
                return False

            if error_code in ["AccessDeniedException", "UnauthorizedException"]:
                self.logger.warning(
                    "Insufficient permissions to describe endpoint",
                    endpoint_name=self.endpoint_name,
                    error_code=error_code,
                )
                # Raise authentication error immediately
                raise SageMakerAuthenticationError(self.endpoint_name, error_code)

            # Unknown error
            self.logger.error(
                "Failed to check endpoint status",
                endpoint_name=self.endpoint_name,
                error_code=error_code,
            )
            return False

        except Exception as e:
            self.logger.error(
                "Unexpected error checking endpoint",
                endpoint_name=self.endpoint_name,
                error=str(e),
            )
            return False

    def get_latest_version(self) -> ModelVersion | None:
        """Get the latest available model version.

        For SageMaker deployment, this returns the version of the configured endpoint.

        Returns:
            Latest ModelVersion if endpoint exists, None otherwise
        """
        versions = self.list_available_versions()

        if not versions:
            self.logger.warning(
                "No SageMaker endpoint available",
                endpoint_name=self.endpoint_name,
            )
            return None

        # Return first (and only) version
        latest = versions[0]
        self.logger.debug("Latest SageMaker model version", version=str(latest))
        return latest
