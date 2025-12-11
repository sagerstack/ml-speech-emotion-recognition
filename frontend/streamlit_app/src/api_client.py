"""
API Client for Speech Emotion Recognition Backend

This module handles communication with the FastAPI backend for emotion inference.
It supports both local development and deployment scenarios.
"""

import os
import logging
from typing import Optional, Dict, Any, BinaryIO
from pathlib import Path
import json
import time

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
ML_APP_BASE_URL = os.getenv("ML_APP_BASE_URL", "http://localhost:8000")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))


class ErrorResponse(BaseModel):
    """Error response from the backend API"""
    error: str = Field(description="Error message")
    status_code: Optional[int] = Field(default=None, description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")


class AudioMetadata(BaseModel):
    """Audio file metadata from backend response"""
    filename: str
    sample_rate: int
    file_size_bytes: int


class InferenceMetadata(BaseModel):
    """Inference processing metadata from backend response"""
    sagemaker_endpoint: str
    aws_region: str
    invocation_time_seconds: float
    response_size_bytes: int


class EmotionPredictions(BaseModel):
    """Emotion predictions from backend response"""
    primary_emotion: str
    confidence: float
    all_emotions: Dict[str, float]


class InferenceResponse(BaseModel):
    """Success response from the backend API"""
    success: bool
    message: str
    data: Dict[str, Any]
    request_id: Optional[str] = None


class EmotionAnalysisResult(BaseModel):
    """Complete emotion analysis result"""
    source: str
    engine: str
    emotion: str
    confidence: float
    probabilities: Dict[str, float]
    processing_time: float
    audio_metadata: Optional[AudioMetadata] = None
    inference_metadata: Optional[InferenceMetadata] = None
    request_id: Optional[str] = None
    prediction_id: Optional[str] = None


class SpeechEmotionAPIClient:
    """
    Client for interacting with the Speech Emotion Recognition Backend API.

    This client handles HTTP requests to the FastAPI backend with proper error handling
    and retry logic for network issues.
    """

    def __init__(self, base_url: str = ML_APP_BASE_URL, timeout: int = REQUEST_TIMEOUT):
        """
        Initialize the API client.

        Args:
            base_url: Base URL of the backend API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

        # Set default headers
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Speech-Emotion-Streamlit-Client/1.0'
        })

        logger.info(f"Initialized API client with base URL: {self.base_url}")

    def health_check(self) -> bool:
        """
        Check if the backend API is healthy and accessible.

        Returns:
            True if API is healthy, False otherwise
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=15  # Increased timeout for EKS deployment
            )
            return response.status_code == 200
        except (RequestException, Timeout, ConnectionError) as e:
            logger.warning(f"Health check failed: {str(e)}")
            return False

    def get_model_versions(self) -> Dict[str, Any]:
        """
        Get all available model versions (v2 API).

        Returns:
            Dictionary containing:
            - versions: List of available versions (e.g., ["v4", "v3", "v2", "v1"])
            - latest: Latest version string (e.g., "v4")
            - count: Total number of versions

        Raises:
            RequestException: If the API request fails
        """
        try:
            logger.info("Fetching model versions")
            response = self.session.get(
                f"{self.base_url}/v2/inference/versions",
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Model versions fetched: {data.get('count', 0)} versions available")
                return data
            else:
                logger.error(f"Failed to fetch model versions: {response.status_code}")
                raise RequestException(f"Failed to fetch model versions: HTTP {response.status_code}")

        except (Timeout, ConnectionError) as e:
            logger.error(f"Connection error fetching model versions: {str(e)}")
            raise RequestException(f"Connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching model versions: {str(e)}")
            raise RequestException(f"Unexpected error: {str(e)}")

    def get_model_info(self, version: str) -> Dict[str, Any]:
        """
        Get information for a specific model version (v2 API).

        Args:
            version: Model version (e.g., "v4", "v3")

        Returns:
            Dictionary containing:
            - version: Model version
            - model_type: Type of model (e.g., "UltraEnsembleModel")
            - feature_dimension: Feature dimension
            - available: Boolean indicating availability

        Raises:
            RequestException: If the API request fails
        """
        try:
            logger.info(f"Fetching model info for version: {version}")
            response = self.session.get(
                f"{self.base_url}/v2/inference/{version}/info",
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Model info fetched for {version}: {data.get('model_type', 'unknown')}")
                return data
            elif response.status_code == 404:
                logger.warning(f"Model version {version} not found")
                raise RequestException(f"Model version {version} not found")
            else:
                logger.error(f"Failed to fetch model info: {response.status_code}")
                raise RequestException(f"Failed to fetch model info: HTTP {response.status_code}")

        except (Timeout, ConnectionError) as e:
            logger.error(f"Connection error fetching model info: {str(e)}")
            raise RequestException(f"Connection error: {str(e)}")
        except RequestException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching model info: {str(e)}")
            raise RequestException(f"Unexpected error: {str(e)}")

    def get_latest_model_info(self) -> Dict[str, Any]:
        """
        Get information for the latest model version (v2 API).

        Returns:
            Dictionary containing:
            - version: Model version
            - model_type: Type of model (e.g., "UltraEnsembleModel")
            - feature_dimension: Feature dimension
            - available: Boolean indicating availability
            - is_latest: Always True for this endpoint

        Raises:
            RequestException: If the API request fails
        """
        try:
            logger.info("Fetching latest model info")
            response = self.session.get(
                f"{self.base_url}/v2/inference/info",
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Latest model info fetched: {data.get('version', 'unknown')} - {data.get('model_type', 'unknown')}")
                return data
            elif response.status_code == 404:
                logger.warning("Latest model not found")
                raise RequestException("Latest model not found")
            else:
                logger.error(f"Failed to fetch latest model info: {response.status_code}")
                raise RequestException(f"Failed to fetch latest model info: HTTP {response.status_code}")

        except (Timeout, ConnectionError) as e:
            logger.error(f"Connection error fetching latest model info: {str(e)}")
            raise RequestException(f"Connection error: {str(e)}")
        except RequestException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching latest model info: {str(e)}")
            raise RequestException(f"Unexpected error: {str(e)}")

    def analyze_audio_file(
        self,
        audio_file: BinaryIO,
        filename: str,
        engine: str = "local"
    ) -> EmotionAnalysisResult:
        """
        Analyze an audio file for emotion recognition.

        DEPRECATED: This method uses a legacy endpoint that no longer exists.
        Use analyze_audio_local() instead which uses the v2 API.

        Args:
            audio_file: Audio file binary data
            filename: Name of the audio file
            engine: Processing engine (local, sagemaker_prod, etc.)

        Returns:
            EmotionAnalysisResult: Complete analysis result

        Raises:
            RequestException: If the API request fails
            ValueError: If the response is invalid
        """
        # Redirect to v2 endpoint
        logger.warning(
            "analyze_audio_file() is deprecated. Redirecting to analyze_audio_local() (v2 API)"
        )
        return self.analyze_audio_local(audio_file, filename, audio_features=False)

    def analyze_audio_local(
        self,
        audio_file: BinaryIO,
        filename: str,
        audio_features: bool = False
    ) -> EmotionAnalysisResult:
        """
        Analyze audio file using v2 inference endpoint (POST /v2/inference).

        This method uses the latest v2 API endpoint that returns predictions
        with model info and processing time.

        Args:
            audio_file: Audio file binary data
            filename: Name of the audio file
            audio_features: Include audio features in response (requires feature flag)

        Returns:
            EmotionAnalysisResult: Complete analysis result

        Raises:
            RequestException: If the API request fails
            ValueError: If the response is invalid
        """
        start_time = time.time()

        try:
            # Prepare the file for upload with explicit content type
            files = {'file': (filename, audio_file, 'audio/wav')}

            # Add audio_features query parameter if requested
            params = {}
            if audio_features:
                params['audio_features'] = 'true'

            logger.info(f"Analyzing audio file locally: {filename} (audio_features={audio_features})")

            # Make the request to the v2 inference endpoint
            response = self.session.post(
                f"{self.base_url}/v2/inference",
                files=files,
                params=params,
                timeout=self.timeout
            )

            # Calculate total processing time
            total_processing_time = time.time() - start_time

            # Handle different response scenarios
            if response.status_code == 200:
                return self._parse_local_response(response, filename, total_processing_time)
            else:
                return self._handle_error_response(response)

        except Timeout as e:
            logger.error(f"Request timeout after {self.timeout}s: {str(e)}")
            raise RequestException(f"Request timeout: The analysis took too long to complete.")

        except ConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            raise RequestException(f"Connection error: Unable to connect to the backend service.")

        except RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise

        except Exception as e:
            logger.error(f"Unexpected error during audio analysis: {str(e)}")
            raise RequestException(f"Unexpected error: {str(e)}")

    def _parse_local_response(
        self,
        response: requests.Response,
        filename: str,
        total_processing_time: float
    ) -> EmotionAnalysisResult:
        """
        Parse response from /v2/inference endpoint.

        Expected response format:
        {
            "version": "v4",
            "prediction": {
                "emotion": "happy",
                "confidence": 0.92,
                "all_probabilities": {
                    "angry": 0.01,
                    "disgust": 0.02,
                    "fear": 0.03,
                    "happy": 0.92,
                    "neutral": 0.01,
                    "sad": 0.01
                }
            },
            "processing_time_ms": 234,
            "audio_features": {...}  # Optional
        }
        """
        try:
            data = response.json()

            # Extract prediction data
            prediction = data.get('prediction', {})
            emotion = prediction.get('emotion')
            confidence = prediction.get('confidence', 0.0)
            all_probabilities = prediction.get('all_probabilities', {})

            # Extract version info
            version = data.get('version', 'unknown')
            prediction_id = data.get('prediction_id') or prediction.get('prediction_id')

            # Create and return the result
            return EmotionAnalysisResult(
                source=filename,
                engine=f"local-{version}",
                emotion=emotion,
                confidence=confidence,
                probabilities=all_probabilities,
                processing_time=total_processing_time,
                audio_metadata=None,
                inference_metadata=None,
                request_id=None,
                prediction_id=prediction_id
            )

        except Exception as e:
            logger.error(f"Failed to parse local response: {str(e)}")
            raise ValueError(f"Invalid response format: {str(e)}")

    def fetch_monitoring_summary(self) -> Dict[str, Any]:
        """Retrieve monitoring summary from the backend."""

        try:
            response = self.session.get(
                f"{self.base_url}/v1/monitoring/summary", timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except RequestException as exc:
            logger.error(f"Monitoring summary request failed: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Unexpected monitoring error: {exc}")
            raise RequestException("Unable to fetch monitoring summary")

    def fetch_monitoring_metrics_history(self) -> Dict[str, Any]:
        """Retrieve aggregated metrics history for dashboard panels."""

        try:
            response = self.session.get(
                f"{self.base_url}/v1/monitoring/metrics/history", timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except RequestException as exc:
            logger.error(f"Monitoring metrics history request failed: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Unexpected monitoring history error: {exc}")
            raise RequestException("Unable to fetch monitoring metrics history")

    def fetch_new_predictions_since_last_report(self) -> Dict[str, Any]:
        """Get count of predictions added since the most recent report."""
        try:
            response = self.session.get(
                f"{self.base_url}/v1/monitoring/buffer/since-last-report",
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except RequestException as exc:
            logger.error(f"New predictions since last report request failed: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Unexpected error fetching new predictions since last report: {exc}")
            raise RequestException("Unable to fetch new predictions since last report")

    def submit_feedback(self, prediction_id: str, actual_emotion: str) -> Dict[str, Any]:
        """
        Submit feedback for a prediction to the monitoring endpoint.

        Uses the session to maintain sticky session affinity with the backend pod
        that holds the prediction in its buffer.

        Args:
            prediction_id: The prediction ID to submit feedback for
            actual_emotion: The actual emotion label

        Returns:
            Dictionary with feedback submission result

        Raises:
            RequestException: If the API request fails
        """
        try:
            logger.info(f"Submitting feedback for prediction {prediction_id}")
            response = self.session.post(
                f"{self.base_url}/v1/monitoring/feedback/{prediction_id}",
                json={"actual_emotion": actual_emotion},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except RequestException as exc:
            logger.error(f"Feedback submission failed: {exc}")
            raise
        except Exception as exc:
            logger.error(f"Unexpected feedback error: {exc}")
            raise RequestException(f"Unable to submit feedback: {exc}")

    def _handle_error_response(self, response: requests.Response) -> None:
        """Handle error responses from the API"""
        try:
            error_data = response.json()
            error_message = error_data.get('detail', f"HTTP {response.status_code}: {response.reason}")
        except:
            error_message = f"HTTP {response.status_code}: {response.reason}"

        logger.error(f"API error response: {error_message}")

        # Create appropriate exception based on status code
        if response.status_code == 413:
            raise RequestException("File too large: The audio file exceeds the maximum allowed size.")
        elif response.status_code == 422:
            raise RequestException("Invalid file format: Please upload a valid audio file.")
        elif response.status_code == 429:
            raise RequestException("Too many requests: Please wait before making another request.")
        elif response.status_code >= 500:
            raise RequestException(f"Server error: The backend service is experiencing issues.")
        else:
            raise RequestException(f"Request failed: {error_message}")


# Global client instance
_api_client: Optional[SpeechEmotionAPIClient] = None


def get_api_client() -> SpeechEmotionAPIClient:
    """
    Get or create the global API client instance.

    Returns:
        SpeechEmotionAPIClient: Global client instance
    """
    global _api_client
    if _api_client is None:
        _api_client = SpeechEmotionAPIClient()
    return _api_client


def reset_api_client() -> None:
    """Reset the global API client instance (useful for testing or configuration changes)"""
    global _api_client
    if _api_client is not None:
        _api_client.session.close()
    _api_client = None


# Convenience function for direct usage
def analyze_emotion(
    audio_file: BinaryIO,
    filename: str,
    engine: str = "local"
) -> EmotionAnalysisResult:
    """
    Convenience function to analyze audio file for emotion.

    Args:
        audio_file: Audio file binary data
        filename: Name of the audio file
        engine: Processing engine to use

    Returns:
        EmotionAnalysisResult: Analysis result
    """
    client = get_api_client()
    return client.analyze_audio_file(audio_file, filename, engine)
