"""
SageMaker service for ML Speech Emotion Recognition.

This service handles communication with AWS SageMaker endpoints for emotion prediction,
including proper error handling, retry logic, and monitoring integration.
"""

import json
import time
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError, ConnectionError, ReadTimeoutError

from app.infrastructure.config import get_settings
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class SageMakerServiceError(Exception):
    """Custom exception for SageMaker service errors."""

    pass


class SageMakerConnectionError(SageMakerServiceError):
    """Exception for SageMaker connection errors."""

    pass


class SageMakerPredictionError(SageMakerServiceError):
    """Exception for SageMaker prediction errors."""

    pass


class SageMakerService:
    """Service for handling SageMaker endpoint communication."""

    def __init__(self):
        """Initialize SageMaker service with AWS client."""
        self.settings = get_settings()
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize SageMaker runtime client using IAM role approach."""
        try:
            # Create session using default credential chain (IAM role, instance profile, etc.)
            session = boto3.Session(region_name=self.settings.aws_region)

            # Initialize SageMaker runtime client
            self.runtime_client = session.client("sagemaker-runtime")

            # Initialize SageMaker management client for endpoint operations
            self.sagemaker_client = session.client("sagemaker")

            logger.info(
                "SageMaker runtime client initialized",
                region=self.settings.aws_region,
                endpoint=self.settings.sagemaker_endpoint_name,
            )

        except Exception as e:
            logger.error(
                "Failed to initialize SageMaker client",
                error=str(e),
                region=self.settings.aws_region,
            )
            raise SageMakerConnectionError(f"Failed to initialize SageMaker client: {str(e)}")

    def _prepare_payload(self, audio_base64: str, sample_rate: int) -> str:
        """
        Prepare JSON payload for SageMaker endpoint.

        Args:
            audio_base64: Base64-encoded audio data
            sample_rate: Audio sample rate

        Returns:
            JSON payload string
        """
        payload_data = {"audio_base64": audio_base64, "sample_rate": sample_rate}

        return json.dumps(payload_data)

    def _parse_response(self, response_body: bytes) -> dict[str, Any]:
        """
        Parse SageMaker response.

        Args:
            response_body: Raw response body from SageMaker

        Returns:
            Parsed response dictionary

        Raises:
            SageMakerPredictionError: If response parsing fails
        """
        try:
            # Handle different response body types
            if isinstance(response_body, str):
                result = json.loads(response_body)
            elif isinstance(response_body, bytes):
                result = json.loads(response_body.decode("utf-8"))
            else:
                raise ValueError(f"Unexpected response body type: {type(response_body)}")

            return result

        except json.JSONDecodeError as e:
            logger.error("Failed to decode JSON response", error=str(e))
            raise SageMakerPredictionError(f"Invalid JSON response from SageMaker: {str(e)}")
        except Exception as e:
            logger.error("Failed to parse response", error=str(e))
            raise SageMakerPredictionError(f"Failed to parse SageMaker response: {str(e)}")

    def _retry_invoke_endpoint(
        self, payload: str, max_retries: int = 3, initial_delay: float = 0.5
    ) -> dict[str, Any]:
        """
        Invoke SageMaker endpoint with retry logic.

        Args:
            payload: JSON payload string
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries (exponential backoff)

        Returns:
            SageMaker response dictionary

        Raises:
            SageMakerPredictionError: If all retries fail
        """
        last_error = None
        delay = initial_delay

        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                logger.debug(
                    "Invoking SageMaker endpoint",
                    attempt=attempt + 1,
                    max_retries=max_retries + 1,
                    endpoint=self.settings.sagemaker_endpoint_name,
                )

                start_time = time.time()

                # Invoke endpoint
                response = self.runtime_client.invoke_endpoint(
                    EndpointName=self.settings.sagemaker_endpoint_name,
                    ContentType="application/json",
                    Accept="application/json",
                    Body=payload,
                )

                invocation_time = time.time() - start_time

                # Read and parse response
                response_body = response["Body"].read()
                result = self._parse_response(response_body)

                # Add timing metadata
                result["invocation_time"] = invocation_time
                result["response_size"] = (
                    len(response_body)
                    if isinstance(response_body, bytes)
                    else len(response_body.encode("utf-8"))
                )
                result["attempt"] = attempt + 1

                logger.info(
                    "SageMaker endpoint invoked successfully",
                    endpoint=self.settings.sagemaker_endpoint_name,
                    invocation_time=invocation_time,
                    response_size=result["response_size"],
                    attempt=attempt + 1,
                )

                return result

            except (ConnectionError, ReadTimeoutError) as e:
                last_error = e
                logger.warning(
                    "SageMaker endpoint connection error",
                    attempt=attempt + 1,
                    error=str(e),
                    delay=delay,
                )

                if attempt < max_retries:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff

            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                error_message = e.response["Error"]["Message"]

                # Don't retry certain client errors
                if error_code in ["ValidationError", "ModelError", "ModelError"]:
                    logger.error(
                        "SageMaker endpoint client error (non-retryable)",
                        error_code=error_code,
                        error_message=error_message,
                    )
                    raise SageMakerPredictionError(f"SageMaker client error: {error_message}")

                last_error = e
                logger.warning(
                    "SageMaker endpoint client error (retryable)",
                    attempt=attempt + 1,
                    error_code=error_code,
                    error_message=error_message,
                    delay=delay,
                )

                if attempt < max_retries:
                    time.sleep(delay)
                    delay *= 2

            except BotoCoreError as e:
                last_error = e
                logger.warning(
                    "SageMaker endpoint AWS SDK error",
                    attempt=attempt + 1,
                    error=str(e),
                    delay=delay,
                )

                if attempt < max_retries:
                    time.sleep(delay)
                    delay *= 2

            except Exception as e:
                last_error = e
                logger.error(
                    "SageMaker endpoint unexpected error", attempt=attempt + 1, error=str(e)
                )
                # Don't retry unexpected errors
                break

        # All retries failed
        logger.error(
            "SageMaker endpoint invocation failed after all retries",
            max_attempts=max_retries + 1,
            last_error=str(last_error),
        )

        raise SageMakerPredictionError(
            f"Failed to invoke SageMaker endpoint after {max_retries + 1} attempts: {str(last_error)}"
        )

    async def predict_emotion(
        self, audio_base64: str, sample_rate: int = 16000, max_retries: int = 3
    ) -> dict[str, Any]:
        """
        Predict emotion from audio using SageMaker endpoint.

        Args:
            audio_base64: Base64-encoded audio data
            sample_rate: Audio sample rate (default: 16000)
            max_retries: Maximum number of retry attempts

        Returns:
            Prediction result dictionary containing:
            - predicted_emotion: str - Primary predicted emotion
            - confidence: float - Confidence score for primary emotion
            - all_emotions: Dict[str, float] - All emotion scores
            - invocation_time: float - Time taken for prediction
            - response_size: int - Size of response in bytes

        Raises:
            SageMakerPredictionError: If prediction fails
            SageMakerConnectionError: If connection to SageMaker fails
        """
        if not audio_base64:
            raise SageMakerPredictionError("Audio data cannot be empty")

        if not self.settings.sagemaker_endpoint_name:
            raise SageMakerPredictionError("SageMaker endpoint name not configured")

        try:
            # Prepare payload
            payload = self._prepare_payload(audio_base64, sample_rate)

            logger.info(
                "Starting emotion prediction",
                endpoint=self.settings.sagemaker_endpoint_name,
                sample_rate=sample_rate,
                payload_size=len(payload),
            )

            # Invoke endpoint with retry logic
            result = self._retry_invoke_endpoint(payload, max_retries)

            # Validate response format
            if "predicted_emotion" not in result:
                raise SageMakerPredictionError("Invalid response format: missing predicted_emotion")

            if "confidence" not in result:
                raise SageMakerPredictionError("Invalid response format: missing confidence")

            # Ensure confidence is a valid number
            try:
                confidence = float(result["confidence"])
                if not 0 <= confidence <= 1:
                    logger.warning("Confidence score out of expected range", confidence=confidence)
            except (ValueError, TypeError):
                raise SageMakerPredictionError(f"Invalid confidence value: {result['confidence']}")

            logger.info(
                "Emotion prediction completed successfully",
                predicted_emotion=result["predicted_emotion"],
                confidence=confidence,
                invocation_time=result.get("invocation_time", 0),
                endpoint=self.settings.sagemaker_endpoint_name,
            )

            return result

        except SageMakerPredictionError:
            # Re-raise SageMaker prediction errors
            raise
        except Exception as e:
            logger.error(
                "Unexpected error during emotion prediction",
                error=str(e),
                endpoint=self.settings.sagemaker_endpoint_name,
            )
            raise SageMakerPredictionError(f"Unexpected error during prediction: {str(e)}")

    async def health_check(self) -> dict[str, Any]:
        """
        Check SageMaker endpoint health status.

        Returns:
            Health status dictionary
        """
        try:
            # Create minimal test payload
            test_payload = json.dumps(
                {
                    "audio_base64": "dGVzdCBhdWRpbyBkYXRh",  # base64-encoded "test audio data"
                    "sample_rate": 16000,
                }
            )

            # Try to invoke endpoint (this will fail with audio processing error,
            # but confirms endpoint is accessible)
            response = self.runtime_client.invoke_endpoint(
                EndpointName=self.settings.sagemaker_endpoint_name,
                ContentType="application/json",
                Accept="application/json",
                Body=test_payload,
            )

            # If we get here, endpoint is responding
            return {
                "status": "healthy",
                "endpoint": self.settings.sagemaker_endpoint_name,
                "region": self.settings.aws_region,
                "accessible": True,
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ModelError":
                # Endpoint is accessible but model error occurred (expected with test data)
                return {
                    "status": "healthy",
                    "endpoint": self.settings.sagemaker_endpoint_name,
                    "region": self.settings.aws_region,
                    "accessible": True,
                    "note": "Model error with test data is expected",
                }
            else:
                # Endpoint is not accessible
                logger.error(
                    "SageMaker endpoint health check failed",
                    error_code=error_code,
                    error_message=e.response["Error"]["Message"],
                )
                return {
                    "status": "unhealthy",
                    "endpoint": self.settings.sagemaker_endpoint_name,
                    "region": self.settings.aws_region,
                    "accessible": False,
                    "error": f"{error_code}: {e.response['Error']['Message']}",
                }

        except Exception as e:
            logger.error("SageMaker endpoint health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "endpoint": self.settings.sagemaker_endpoint_name,
                "region": self.settings.aws_region,
                "accessible": False,
                "error": str(e),
            }

    async def get_endpoint_info(self, endpoint_name: str | None = None) -> dict[str, Any]:
        """
        Get detailed endpoint information.

        Args:
            endpoint_name: Specific endpoint name (uses default if not provided)

        Returns:
            Endpoint information dictionary
        """
        try:
            target_endpoint = endpoint_name or self.settings.sagemaker_endpoint_name

            response = self.sagemaker_client.describe_endpoint(EndpointName=target_endpoint)

            return {
                "endpoint_name": response.get("EndpointName"),
                "endpoint_arn": response.get("EndpointArn"),
                "endpoint_status": response.get("EndpointStatus"),
                "endpoint_config_name": response.get("EndpointConfigName"),
                "creation_time": response.get("CreationTime"),
                "last_modified_time": response.get("LastModifiedTime"),
                "production_variants": response.get("ProductionVariants", []),
                "failure_reason": response.get("FailureReason"),
            }

        except ClientError as e:
            logger.error(
                "Failed to get endpoint info",
                endpoint_name=target_endpoint,
                error_code=e.response["Error"]["Code"],
                error_message=e.response["Error"]["Message"],
            )
            raise SageMakerServiceError(
                f"Failed to get endpoint info: {e.response['Error']['Message']}"
            )

    async def get_endpoint_config(self, config_name: str) -> dict[str, Any]:
        """
        Get endpoint configuration details.

        Args:
            config_name: Endpoint configuration name

        Returns:
            Configuration information dictionary
        """
        try:
            response = self.sagemaker_client.describe_endpoint_config(
                EndpointConfigName=config_name
            )

            return {
                "config_name": response.get("EndpointConfigName"),
                "config_arn": response.get("EndpointConfigArn"),
                "production_variants": response.get("ProductionVariants", []),
                "creation_time": response.get("CreationTime"),
            }

        except ClientError as e:
            logger.error(
                "Failed to get endpoint config",
                config_name=config_name,
                error_code=e.response["Error"]["Code"],
                error_message=e.response["Error"]["Message"],
            )
            raise SageMakerServiceError(
                f"Failed to get endpoint config: {e.response['Error']['Message']}"
            )

    async def disable_endpoint(
        self,
        endpoint_name: str | None = None,
        wait_for_completion: bool = True,
        timeout: int = 600,
    ) -> dict[str, Any]:
        """
        Disable SageMaker endpoint by updating to 0 instances.

        Args:
            endpoint_name: Specific endpoint name (uses default if not provided)
            wait_for_completion: Whether to wait for the update to complete
            timeout: Maximum time to wait for completion (seconds)

        Returns:
            Dictionary with disable operation details
        """
        try:
            target_endpoint = endpoint_name or self.settings.sagemaker_endpoint_name

            logger.info("Starting endpoint disable process", endpoint_name=target_endpoint)

            # Get current endpoint info
            endpoint_info = await self.get_endpoint_info(target_endpoint)
            original_config_name = endpoint_info["endpoint_config_name"]

            # Get current configuration
            config_info = await self.get_endpoint_config(original_config_name)
            original_variants = config_info["production_variants"]

            # Calculate current total instances
            current_instances = sum(
                variant["InitialInstanceCount"] for variant in original_variants
            )

            logger.info(
                "Current endpoint state",
                endpoint=target_endpoint,
                current_instances=current_instances,
                config_name=original_config_name,
            )

            if current_instances == 0:
                logger.info("Endpoint already has 0 instances", endpoint=target_endpoint)
                return {
                    "endpoint_name": target_endpoint,
                    "status": "already_disabled",
                    "current_instances": 0,
                    "message": "Endpoint already has 0 instances",
                }

            # Create disabled configuration with 0 instances
            disabled_config_name = f"{target_endpoint}-disabled-config"
            disabled_variants = []

            for variant in original_variants:
                disabled_variant = {
                    "VariantName": variant["VariantName"],
                    "InstanceType": variant["InstanceType"],
                    "InitialInstanceCount": 0,
                    "ModelName": variant["ModelName"],
                }

                # Preserve optional parameters if they exist
                if "InitialVariantWeight" in variant:
                    disabled_variant["InitialVariantWeight"] = variant["InitialVariantWeight"]
                if "VolumeSizeInGB" in variant:
                    disabled_variant["VolumeSizeInGB"] = variant["VolumeSizeInGB"]

                disabled_variants.append(disabled_variant)

            # Create disabled configuration
            try:
                self.sagemaker_client.create_endpoint_config(
                    EndpointConfigName=disabled_config_name, ProductionVariants=disabled_variants
                )
                logger.info("Created disabled configuration", config_name=disabled_config_name)
            except ClientError as e:
                if e.response["Error"]["Code"] == "ValidationException" and "already exists" in str(
                    e
                ):
                    logger.info(
                        "Disabled configuration already exists", config_name=disabled_config_name
                    )
                else:
                    raise

            # Update endpoint to use disabled configuration
            update_response = self.sagemaker_client.update_endpoint(
                EndpointName=target_endpoint, EndpointConfigName=disabled_config_name
            )

            logger.info("Endpoint update initiated", endpoint_name=target_endpoint)

            if wait_for_completion:
                # Wait for endpoint to be InService with 0 instances
                start_time = time.time()

                while time.time() - start_time < timeout:
                    try:
                        current_info = await self.get_endpoint_info(target_endpoint)
                        current_status = current_info["endpoint_status"]

                        if current_status == "InService":
                            # Verify instance count is 0
                            current_config_info = await self.get_endpoint_config(
                                current_info["endpoint_config_name"]
                            )
                            total_instances = sum(
                                variant["InitialInstanceCount"]
                                for variant in current_config_info["production_variants"]
                            )

                            if total_instances == 0:
                                logger.info(
                                    "Endpoint successfully disabled",
                                    endpoint=target_endpoint,
                                    instances=total_instances,
                                )
                                return {
                                    "endpoint_name": target_endpoint,
                                    "status": "disabled",
                                    "previous_instances": current_instances,
                                    "current_instances": total_instances,
                                    "original_config": original_config_name,
                                    "disabled_config": disabled_config_name,
                                    "disable_time": time.time(),
                                }

                        elif current_status in ["Failed", "DeleteFailed"]:
                            logger.error(
                                "Endpoint disable failed",
                                endpoint=target_endpoint,
                                status=current_status,
                                failure_reason=current_info.get("failure_reason", "Unknown"),
                            )
                            return {
                                "endpoint_name": target_endpoint,
                                "status": "failed",
                                "error": current_info.get("failure_reason", "Unknown failure"),
                            }

                        time.sleep(30)  # Wait 30 seconds before checking again

                    except Exception as e:
                        logger.warning(
                            "Error checking endpoint status during disable", error=str(e)
                        )
                        time.sleep(30)

                # Timeout reached
                logger.error("Endpoint disable timeout", endpoint=target_endpoint, timeout=timeout)
                return {
                    "endpoint_name": target_endpoint,
                    "status": "timeout",
                    "error": f"Disable operation timed out after {timeout} seconds",
                }

            else:
                return {
                    "endpoint_name": target_endpoint,
                    "status": "initiated",
                    "previous_instances": current_instances,
                    "original_config": original_config_name,
                    "disabled_config": disabled_config_name,
                    "message": "Disable operation initiated, not waiting for completion",
                }

        except Exception as e:
            logger.error("Failed to disable endpoint", endpoint_name=target_endpoint, error=str(e))
            raise SageMakerServiceError(f"Failed to disable endpoint: {str(e)}")

    async def reenable_endpoint(
        self,
        endpoint_name: str | None = None,
        config_name: str | None = None,
        wait_for_completion: bool = True,
        timeout: int = 900,
    ) -> dict[str, Any]:
        """
        Re-enable SageMaker endpoint by restoring original configuration.

        Args:
            endpoint_name: Specific endpoint name (uses default if not provided)
            config_name: Specific config name to use (uses original if not provided)
            wait_for_completion: Whether to wait for the update to complete
            timeout: Maximum time to wait for completion (seconds)

        Returns:
            Dictionary with re-enable operation details
        """
        try:
            target_endpoint = endpoint_name or self.settings.sagemaker_endpoint_name

            logger.info(
                "Starting endpoint re-enable process",
                endpoint_name=target_endpoint,
                target_config=config_name,
            )

            # Get current endpoint info
            endpoint_info = await self.get_endpoint_info(target_endpoint)
            current_config_name = endpoint_info["endpoint_config_name"]
            current_status = endpoint_info["endpoint_status"]

            # Determine target configuration
            target_config_name = config_name

            if not target_config_name:
                # Try to find the original config by looking for non-disabled configs
                # This is a simplified approach - in practice you might want to store
                # the original config name when disabling
                disabled_config_suffix = "-disabled-config"
                if current_config_name.endswith(disabled_config_suffix):
                    # Remove the disabled suffix to get original name
                    original_config_name = current_config_name[: -len(disabled_config_suffix)]

                    # Verify the original config exists
                    try:
                        await self.get_endpoint_config(original_config_name)
                        target_config_name = original_config_name
                    except:
                        logger.warning(
                            "Original config not found, keeping current config",
                            original_config=original_config_name,
                        )
                        target_config_name = current_config_name
                else:
                    target_config_name = current_config_name

            # Get target configuration to verify it has instances
            target_config_info = await self.get_endpoint_config(target_config_name)
            target_instances = sum(
                variant["InitialInstanceCount"]
                for variant in target_config_info["production_variants"]
            )

            logger.info(
                "Configuration info",
                current_config=current_config_name,
                target_config=target_config_name,
                target_instances=target_instances,
            )

            if target_config_name == current_config_name and target_instances > 0:
                logger.info(
                    "Endpoint already enabled with instances",
                    endpoint=target_endpoint,
                    instances=target_instances,
                )
                return {
                    "endpoint_name": target_endpoint,
                    "status": "already_enabled",
                    "current_instances": target_instances,
                    "config_name": target_config_name,
                    "message": "Endpoint already enabled with active instances",
                }

            if target_instances == 0:
                logger.warning(
                    "Target configuration has 0 instances",
                    config=target_config_name,
                    instances=target_instances,
                )
                return {
                    "endpoint_name": target_endpoint,
                    "status": "no_instances",
                    "config_name": target_config_name,
                    "instances": target_instances,
                    "message": "Target configuration has 0 instances - endpoint will remain disabled",
                }

            # Update endpoint to use target configuration
            update_response = self.sagemaker_client.update_endpoint(
                EndpointName=target_endpoint, EndpointConfigName=target_config_name
            )

            logger.info(
                "Endpoint re-enable update initiated",
                endpoint_name=target_endpoint,
                target_config=target_config_name,
            )

            if wait_for_completion:
                # Wait for endpoint to be InService
                start_time = time.time()

                while time.time() - start_time < timeout:
                    try:
                        current_info = await self.get_endpoint_info(target_endpoint)
                        current_status = current_info["endpoint_status"]

                        if current_status == "InService":
                            # Verify instance count
                            current_config_info = await self.get_endpoint_config(
                                current_info["endpoint_config_name"]
                            )
                            total_instances = sum(
                                variant["InitialInstanceCount"]
                                for variant in current_config_info["production_variants"]
                            )

                            logger.info(
                                "Endpoint successfully re-enabled",
                                endpoint=target_endpoint,
                                instances=total_instances,
                                config=current_info["endpoint_config_name"],
                            )
                            return {
                                "endpoint_name": target_endpoint,
                                "status": "enabled",
                                "instances": total_instances,
                                "config_name": target_config_name,
                                "previous_config": current_config_name,
                                "enable_time": time.time(),
                            }

                        elif current_status in ["Failed", "DeleteFailed"]:
                            logger.error(
                                "Endpoint re-enable failed",
                                endpoint=target_endpoint,
                                status=current_status,
                                failure_reason=current_info.get("failure_reason", "Unknown"),
                            )
                            return {
                                "endpoint_name": target_endpoint,
                                "status": "failed",
                                "error": current_info.get("failure_reason", "Unknown failure"),
                            }

                        # Show progress for long-running operations
                        if current_status == "Updating":
                            elapsed = time.time() - start_time
                            logger.info(
                                "Re-enable in progress",
                                endpoint=target_endpoint,
                                elapsed_seconds=f"{elapsed:.0f}",
                            )

                        time.sleep(30)  # Wait 30 seconds before checking again

                    except Exception as e:
                        logger.warning(
                            "Error checking endpoint status during re-enable", error=str(e)
                        )
                        time.sleep(30)

                # Timeout reached
                logger.error(
                    "Endpoint re-enable timeout", endpoint=target_endpoint, timeout=timeout
                )
                return {
                    "endpoint_name": target_endpoint,
                    "status": "timeout",
                    "error": f"Re-enable operation timed out after {timeout} seconds",
                }

            else:
                return {
                    "endpoint_name": target_endpoint,
                    "status": "initiated",
                    "target_config": target_config_name,
                    "previous_config": current_config_name,
                    "target_instances": target_instances,
                    "message": "Re-enable operation initiated, not waiting for completion",
                }

        except Exception as e:
            logger.error("Failed to re-enable endpoint", endpoint_name=endpoint_name, error=str(e))
            raise SageMakerServiceError(f"Failed to re-enable endpoint: {str(e)}")

    async def list_endpoints(self, status_filter: str | None = None) -> dict[str, Any]:
        """
        List SageMaker endpoints with optional status filter.

        Args:
            status_filter: Filter endpoints by status (e.g., 'InService', 'Failed')

        Returns:
            Dictionary with endpoint list
        """
        try:
            endpoints = []
            paginator = self.sagemaker_client.get_paginator("list_endpoints")

            for page in paginator.paginate():
                for endpoint in page.get("Endpoints", []):
                    if status_filter is None or endpoint.get("EndpointStatus") == status_filter:
                        endpoints.append(endpoint)

            return {
                "endpoints": endpoints,
                "count": len(endpoints),
                "region": self.settings.aws_region,
            }

        except Exception as e:
            logger.error("Failed to list endpoints", error=str(e))
            raise SageMakerServiceError(f"Failed to list endpoints: {str(e)}")


# Global service instance
_sagemaker_service: SageMakerService | None = None


def get_sagemaker_service() -> SageMakerService:
    """Get or create global SageMaker service instance."""
    global _sagemaker_service
    if _sagemaker_service is None:
        _sagemaker_service = SageMakerService()
    return _sagemaker_service
