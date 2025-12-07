"""Adapter that wraps SageMaker endpoint to implement domain EmotionModel interface.

This module implements the Adapter Pattern to convert SageMaker endpoint invocations
into the domain's EmotionModel interface. Feature extraction remains in the backend API,
and only model inference is delegated to SageMaker.
"""

import json
import time
from typing import Any

import boto3
import numpy as np
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError, ReadTimeoutError

from app.domain.model.entities.emotion_model import EmotionModel
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
from app.infrastructure.observability.logging import get_logger


class SageMakerEmotionModelAdapter(EmotionModel):
    """Adapts SageMaker endpoint invocations to domain EmotionModel interface.

    This adapter:
    - Receives pre-extracted features from backend API (180 floats)
    - Converts features to SageMaker request format (JSON)
    - Invokes SageMaker endpoint with retry logic
    - Parses SageMaker response
    - Maps predictions to Emotion enum
    - Handles errors with domain exceptions

    Adapter Pattern:
    - Target: EmotionModel (domain interface)
    - Adaptee: AWS SageMaker Runtime API (boto3 client)
    - Adapter: SageMakerEmotionModelAdapter (this class)

    The adapter handles:
    - Request/response serialization (numpy -> JSON -> numpy)
    - Error mapping (boto3 ClientError -> domain exceptions)
    - Retry logic with exponential backoff
    - Performance instrumentation
    """

    # Emotion order expected by v5 model (matching training labels)
    # This matches the class order used during model training
    _EMOTION_MAPPING = [
        Emotion.ANGRY,
        Emotion.DISGUST,
        Emotion.FEAR,
        Emotion.HAPPY,
        Emotion.NEUTRAL,
        Emotion.SAD,
    ]

    def __init__(
        self,
        endpoint_name: str,
        region: str,
        timeout_seconds: int = 30,
        max_retries: int = 3,
    ):
        """Initialize SageMaker adapter.

        Args:
            endpoint_name: SageMaker endpoint name
            region: AWS region (e.g., 'us-east-1')
            timeout_seconds: Timeout for endpoint invocation (default: 30)
            max_retries: Maximum number of retries for transient errors (default: 3)
        """
        self.endpoint_name = endpoint_name
        self.region = region
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.logger = get_logger(__name__)

        # Configure boto3 client with timeouts
        # Read timeout: time to wait for response after connection established
        # Connect timeout: time to wait for initial connection
        config = Config(
            region_name=region,
            read_timeout=timeout_seconds,
            connect_timeout=10,  # 10 seconds for connection
            retries={"max_attempts": 0},  # We implement custom retry logic
        )

        # Initialize SageMaker Runtime client
        try:
            self.client = boto3.client("sagemaker-runtime", config=config)
            self.logger.info(
                "SageMaker client initialized",
                endpoint_name=endpoint_name,
                region=region,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
            )
        except Exception as e:
            self.logger.error(
                "Failed to initialize SageMaker client",
                error=str(e),
                region=region,
            )
            raise PredictionFailedError(f"Failed to initialize SageMaker client: {str(e)}")

    def predict_emotion_probabilities(self, features: np.ndarray) -> dict[Emotion, float]:
        """Predict emotion probabilities using SageMaker endpoint.

        Implementation strategy:
        1. Validate and serialize features to JSON
        2. Invoke SageMaker endpoint with retry logic
        3. Parse response and extract probabilities
        4. Map probabilities to Emotion enum
        5. Validate and return results

        Args:
            features: Audio feature array of shape (180,) or (1, 180)

        Returns:
            Dictionary mapping each Emotion to its probability (0.0-1.0)

        Raises:
            PredictionFailedError: If prediction fails
            SageMakerEndpointNotFoundError: If endpoint doesn't exist
            SageMakerTimeoutError: If endpoint invocation times out
            SageMakerThrottlingError: If endpoint is throttling requests
            SageMakerAuthenticationError: If IAM permissions are insufficient
            SageMakerInvalidResponseError: If response is malformed
        """
        self.logger.debug(
            "Running SageMaker inference",
            endpoint_name=self.endpoint_name,
            input_shape=features.shape,
        )

        start_time = time.time()

        try:
            # Step 1: Validate and serialize features
            features_list = self._serialize_features(features)

            # Step 2: Invoke SageMaker endpoint with retry logic
            response_body = self._invoke_endpoint_with_retry(features_list)

            # Step 3: Parse response
            probabilities = self._parse_response(response_body)

            # Step 4: Map to Emotion enum
            emotion_probabilities = self._map_to_emotions(probabilities)

            # Step 5: Calculate and log performance
            end_time = time.time()
            inference_time_ms = (end_time - start_time) * 1000

            predicted_emotion = max(emotion_probabilities.items(), key=lambda x: x[1])

            self.logger.info(
                "SageMaker inference completed",
                endpoint_name=self.endpoint_name,
                predicted_emotion=str(predicted_emotion[0]),
                confidence=round(predicted_emotion[1], 4),
                inference_time_ms=round(inference_time_ms, 2),
            )

            return emotion_probabilities

        except (
            SageMakerEndpointNotFoundError,
            SageMakerTimeoutError,
            SageMakerThrottlingError,
            SageMakerAuthenticationError,
            SageMakerInvalidResponseError,
        ):
            # Re-raise domain exceptions as-is
            raise

        except Exception as e:
            # Convert any other exception to domain exception
            self.logger.error(
                "SageMaker inference failed unexpectedly",
                endpoint_name=self.endpoint_name,
                error=str(e),
                input_shape=features.shape,
            )
            raise PredictionFailedError(
                f"SageMaker inference failed: {type(e).__name__}: {str(e)}"
            ) from e

    def _serialize_features(self, features: np.ndarray) -> list[float]:
        """Serialize features to list for JSON request.

        Args:
            features: Feature array of shape (180,) or (1, 180)

        Returns:
            List of 180 floats

        Raises:
            PredictionFailedError: If features are invalid
        """
        # Flatten to 1D if needed
        if len(features.shape) == 2:
            if features.shape[0] != 1:
                raise PredictionFailedError(
                    f"Expected single sample, got {features.shape[0]} samples"
                )
            features = features.flatten()
        elif len(features.shape) != 1:
            raise PredictionFailedError(
                f"Invalid features shape: {features.shape}. "
                f"Expected 1D (180,) or 2D (1, 180)"
            )

        # Validate feature dimension (180 features from LibrosaAudioProcessor)
        if len(features) != 180:
            raise PredictionFailedError(
                f"Expected 180 features, got {len(features)}. "
                f"Ensure LibrosaAudioProcessor extracts correct number of features."
            )

        # Convert to Python list of floats
        features_list = [float(f) for f in features]

        self.logger.debug(
            "Features serialized",
            num_features=len(features_list),
            sample_features=features_list[:5],  # Log first 5 for debugging
        )

        return features_list

    def _invoke_endpoint_with_retry(self, features_list: list[float]) -> dict[str, Any]:
        """Invoke SageMaker endpoint with exponential backoff retry.

        Retry strategy:
        - Transient errors (throttling, network issues): Retry with exponential backoff
        - Permanent errors (404, 403): Raise immediately, no retry
        - Timeout errors: Raise immediately, no retry (already waited)

        Args:
            features_list: List of 180 features

        Returns:
            Parsed JSON response body

        Raises:
            SageMakerEndpointNotFoundError: Endpoint not found (permanent)
            SageMakerAuthenticationError: Permission denied (permanent)
            SageMakerTimeoutError: Timeout exceeded
            SageMakerThrottlingError: Throttling after retries exhausted
        """
        # Prepare request payload
        request_body = json.dumps({"features": features_list})

        retry_count = 0
        last_error = None

        while retry_count <= self.max_retries:
            try:
                self.logger.debug(
                    "Invoking SageMaker endpoint",
                    endpoint_name=self.endpoint_name,
                    attempt=retry_count + 1,
                    max_attempts=self.max_retries + 1,
                )

                # Invoke endpoint
                response = self.client.invoke_endpoint(
                    EndpointName=self.endpoint_name,
                    ContentType="application/json",
                    Accept="application/json",
                    Body=request_body,
                )

                # Parse response
                response_body = json.loads(response["Body"].read().decode("utf-8"))

                self.logger.debug(
                    "SageMaker endpoint invoked successfully",
                    endpoint_name=self.endpoint_name,
                    attempt=retry_count + 1,
                )

                return response_body

            except ReadTimeoutError as e:
                # Timeout - do NOT retry (already waited long enough)
                self.logger.error(
                    "SageMaker endpoint timeout",
                    endpoint_name=self.endpoint_name,
                    timeout_seconds=self.timeout_seconds,
                )
                raise SageMakerTimeoutError(self.endpoint_name, self.timeout_seconds) from e

            except EndpointConnectionError as e:
                # Connection timeout - treat as timeout error
                self.logger.error(
                    "SageMaker endpoint connection timeout",
                    endpoint_name=self.endpoint_name,
                )
                raise SageMakerTimeoutError(self.endpoint_name, self.timeout_seconds) from e

            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_message = e.response.get("Error", {}).get("Message", str(e))

                # Permanent errors - do NOT retry
                if error_code in ["ValidationError", "ResourceNotFoundException"]:
                    if "Could not find endpoint" in error_message or "does not exist" in error_message:
                        self.logger.error(
                            "SageMaker endpoint not found",
                            endpoint_name=self.endpoint_name,
                            error_code=error_code,
                        )
                        raise SageMakerEndpointNotFoundError(self.endpoint_name) from e

                if error_code in [
                    "AccessDeniedException",
                    "UnauthorizedException",
                    "InvalidSignatureException",
                    "InvalidAccessKeyId",
                    "SignatureDoesNotMatch",
                ]:
                    self.logger.error(
                        "SageMaker authentication failed",
                        endpoint_name=self.endpoint_name,
                        error_code=error_code,
                    )
                    raise SageMakerAuthenticationError(self.endpoint_name, error_code) from e

                # Transient errors - retry with exponential backoff
                if error_code in ["ThrottlingException", "TooManyRequestsException", "ServiceUnavailable"]:
                    last_error = e
                    retry_count += 1

                    if retry_count > self.max_retries:
                        self.logger.error(
                            "SageMaker throttling - max retries exceeded",
                            endpoint_name=self.endpoint_name,
                            retry_count=retry_count,
                        )
                        raise SageMakerThrottlingError(self.endpoint_name) from e

                    # Exponential backoff: 1s, 2s, 4s
                    sleep_time = 2 ** (retry_count - 1)
                    self.logger.warning(
                        "SageMaker throttling - retrying",
                        endpoint_name=self.endpoint_name,
                        retry_count=retry_count,
                        sleep_time=sleep_time,
                    )
                    time.sleep(sleep_time)
                    continue

                # Unknown error - raise as generic error
                self.logger.error(
                    "SageMaker client error",
                    endpoint_name=self.endpoint_name,
                    error_code=error_code,
                    error_message=error_message,
                )
                raise PredictionFailedError(
                    f"SageMaker error ({error_code}): {error_message}"
                ) from e

            except json.JSONDecodeError as e:
                # Response is not valid JSON
                self.logger.error(
                    "Invalid JSON in SageMaker response",
                    endpoint_name=self.endpoint_name,
                    error=str(e),
                )
                raise SageMakerInvalidResponseError(
                    self.endpoint_name, f"Response is not valid JSON: {str(e)}"
                ) from e

        # Should never reach here, but safety net
        if last_error:
            raise SageMakerThrottlingError(self.endpoint_name) from last_error
        raise PredictionFailedError("Unexpected error in retry logic")

    def _parse_response(self, response_body: dict[str, Any]) -> np.ndarray:
        """Parse SageMaker response and extract probabilities.

        Expected response format:
        {
            "emotion": "happy",
            "confidence": 0.87,
            "probabilities": {
                "angry": 0.03,
                "disgust": 0.02,
                "fear": 0.01,
                "happy": 0.87,
                "neutral": 0.05,
                "sad": 0.02
            },
            "model_version": "v5"
        }

        Args:
            response_body: Parsed JSON response from SageMaker

        Returns:
            Numpy array of 6 probabilities in order: [angry, disgust, fear, happy, neutral, sad]

        Raises:
            SageMakerInvalidResponseError: If response format is invalid
        """
        try:
            # Extract probabilities dictionary
            probabilities_dict = response_body.get("probabilities")

            if probabilities_dict is None:
                raise SageMakerInvalidResponseError(
                    self.endpoint_name,
                    "Response missing 'probabilities' field"
                )

            if not isinstance(probabilities_dict, dict):
                raise SageMakerInvalidResponseError(
                    self.endpoint_name,
                    f"'probabilities' must be dict, got {type(probabilities_dict)}"
                )

            # Map emotion names to probabilities in expected order
            # SageMaker returns: {"angry": 0.03, "disgust": 0.02, ...}
            # We need: [0.03, 0.02, 0.01, 0.87, 0.05, 0.02] (matching _EMOTION_MAPPING order)
            probabilities = []
            for emotion in self._EMOTION_MAPPING:
                # Convert Emotion enum to lowercase string for matching
                emotion_key = str(emotion).lower()

                if emotion_key not in probabilities_dict:
                    raise SageMakerInvalidResponseError(
                        self.endpoint_name,
                        f"Missing probability for emotion '{emotion_key}'"
                    )

                prob = probabilities_dict[emotion_key]

                # Validate probability value
                if not isinstance(prob, (int, float)):
                    raise SageMakerInvalidResponseError(
                        self.endpoint_name,
                        f"Probability for '{emotion_key}' must be numeric, got {type(prob)}"
                    )

                if not (0.0 <= prob <= 1.0):
                    raise SageMakerInvalidResponseError(
                        self.endpoint_name,
                        f"Probability for '{emotion_key}' must be in [0,1], got {prob}"
                    )

                probabilities.append(float(prob))

            # Convert to numpy array
            probabilities_array = np.array(probabilities, dtype=np.float64)

            self.logger.debug(
                "Response parsed successfully",
                num_probabilities=len(probabilities_array),
                probabilities_sum=round(sum(probabilities_array), 4),
            )

            return probabilities_array

        except SageMakerInvalidResponseError:
            # Re-raise as-is
            raise

        except Exception as e:
            # Unexpected error during parsing
            self.logger.error(
                "Failed to parse SageMaker response",
                endpoint_name=self.endpoint_name,
                error=str(e),
                response_body=response_body,
            )
            raise SageMakerInvalidResponseError(
                self.endpoint_name,
                f"Failed to parse response: {type(e).__name__}: {str(e)}"
            ) from e

    def _map_to_emotions(self, probabilities: np.ndarray) -> dict[Emotion, float]:
        """Map probability array to Emotion enum dictionary.

        Args:
            probabilities: Array of 6 probabilities

        Returns:
            Dictionary mapping Emotion to probability

        Raises:
            PredictionFailedError: If probabilities are invalid
        """
        # Validate probabilities
        if len(probabilities) != len(self._EMOTION_MAPPING):
            raise PredictionFailedError(
                f"Expected {len(self._EMOTION_MAPPING)} probabilities, "
                f"got {len(probabilities)}"
            )

        # Map to emotions
        emotion_probabilities: dict[Emotion, float] = {
            emotion: float(prob)
            for emotion, prob in zip(self._EMOTION_MAPPING, probabilities)
        }

        # Validate probabilities sum to ~1.0
        total_prob = sum(emotion_probabilities.values())
        if not (0.99 <= total_prob <= 1.01):
            raise PredictionFailedError(
                f"Probabilities sum to {total_prob:.4f}, expected ~1.0. "
                f"SageMaker output may be invalid."
            )

        return emotion_probabilities
