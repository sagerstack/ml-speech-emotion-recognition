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

    def analyze_audio_file(
        self,
        audio_file: BinaryIO,
        filename: str,
        engine: str = "local"
    ) -> EmotionAnalysisResult:
        """
        Analyze an audio file for emotion recognition.

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
        start_time = time.time()

        try:
            # Prepare the file for upload
            files = {'file': (filename, audio_file, 'audio/wav')}
            data = {'engine': engine}

            logger.info(f"Analyzing audio file: {filename} with engine: {engine}")

            # Make the request to the inference endpoint
            response = self.session.post(
                f"{self.base_url}/v1/infer/infer",
                files=files,
                data=data,
                timeout=self.timeout
            )

            # Calculate total processing time
            total_processing_time = time.time() - start_time

            # Handle different response scenarios
            if response.status_code == 200:
                return self._parse_success_response(response, filename, engine, total_processing_time)
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

    def _parse_success_response(
        self,
        response: requests.Response,
        filename: str,
        engine: str,
        total_processing_time: float
    ) -> EmotionAnalysisResult:
        """Parse successful API response into EmotionAnalysisResult"""
        try:
            response_data = response.json()
            inference_response = InferenceResponse(**response_data)

            if not inference_response.success:
                raise ValueError(f"API returned error: {inference_response.message}")

            # Extract predictions and metadata
            predictions_data = inference_response.data.get('predictions', {})
            audio_metadata_data = inference_response.data.get('audio_metadata')
            inference_metadata_data = inference_response.data.get('inference_metadata')

            # Create objects
            predictions = EmotionPredictions(**predictions_data)

            audio_metadata = None
            if audio_metadata_data:
                audio_metadata = AudioMetadata(**audio_metadata_data)

            inference_metadata = None
            if inference_metadata_data:
                inference_metadata = InferenceMetadata(**inference_metadata_data)

            # Create and return the result
            return EmotionAnalysisResult(
                source=filename,
                engine=engine,
                emotion=predictions.primary_emotion,
                confidence=predictions.confidence,
                probabilities=predictions.all_emotions,
                processing_time=total_processing_time,
                audio_metadata=audio_metadata,
                inference_metadata=inference_metadata,
                request_id=inference_response.request_id
            )

        except Exception as e:
            logger.error(f"Failed to parse successful response: {str(e)}")
            raise ValueError(f"Invalid response format: {str(e)}")

    def analyze_audio_local(
        self,
        audio_file: BinaryIO,
        filename: str
    ) -> EmotionAnalysisResult:
        """
        Analyze audio file using local model endpoint (/v1/infer/local/latest).

        This method uses the new local inference endpoint that returns
        predictions with model info and processing time.

        Args:
            audio_file: Audio file binary data
            filename: Name of the audio file

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

            logger.info(f"Analyzing audio file locally: {filename}")

            # Make the request to the local inference endpoint
            response = self.session.post(
                f"{self.base_url}/v1/infer/local/latest",
                files=files,
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
        Parse response from /v1/infer/local/latest endpoint.

        Expected response format:
        {
            "version": "2",
            "prediction": {
                "emotion": "happy",
                "confidence": 0.92,
                "all_probabilities": {"happy": 0.92, "neutral": 0.05, ...}
            },
            "model_info": {
                "type": "SVM Pipeline",
                "features_used": 78
            },
            "processing_time_ms": 234
        }
        """
        try:
            data = response.json()

            # Extract prediction data
            prediction = data.get('prediction', {})
            emotion = prediction.get('emotion')
            confidence = prediction.get('confidence', 0.0)
            all_probabilities = prediction.get('all_probabilities', {})

            # Create and return the result
            return EmotionAnalysisResult(
                source=filename,
                engine="local",
                emotion=emotion,
                confidence=confidence,
                probabilities=all_probabilities,
                processing_time=total_processing_time,
                audio_metadata=None,
                inference_metadata=None,
                request_id=None
            )

        except Exception as e:
            logger.error(f"Failed to parse local response: {str(e)}")
            raise ValueError(f"Invalid response format: {str(e)}")

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