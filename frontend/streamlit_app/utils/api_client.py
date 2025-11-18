import requests
import json
import time
import logging
import os
from typing import Dict, Any, Optional
import streamlit as st

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class APIClient:
    """Client for interacting with the FastAPI backend"""

    def __init__(self, base_url: str = None):
        # Use environment variable first, then fallback to provided URL, then default
        if base_url is None:
            base_url = os.getenv('BACKEND_API_URL', 'http://localhost:8000')

        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

        logger.info(f"APIClient initialized with base_url: {self.base_url}")

        # Set timeout from environment variable
        self.timeout = int(os.getenv('API_TIMEOUT', '30'))

    def health_check(self, custom_url: str = None) -> Dict[str, Any]:
        """Check if the backend API is healthy"""
        if custom_url:
            url = custom_url.rstrip('/') + '/health'
        else:
            url = f"{self.base_url}/health"

        logger.info(f"Testing API health at: {url}")

        try:
            response = self.session.get(url, timeout=self.timeout)
            logger.info(f"Response status: {response.status_code}")

            response.raise_for_status()
            result = response.json()
            logger.info(f"Response data: {result}")
            return result
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to {url}: {e}")
            return {"status": "error", "message": f"Connection failed to {url}"}
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error for {url}: {e}")
            return {"status": "error", "message": f"Request timeout to {url}"}
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            return {"status": "error", "message": f"HTTP {e.response.status_code}: {e.response.reason}"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception for {url}: {e}")
            return {"status": "error", "message": str(e)}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error from {url}: {e}")
            return {"status": "error", "message": "Invalid JSON response"}

    def predict_emotion(
        self,
        audio_file,
        api_url: str = None,
        max_duration: int = 30
    ) -> Optional[Dict[str, Any]]:
        """Send audio file to backend for emotion prediction"""

        url = (api_url or self.base_url).rstrip('/')
        predict_url = f"{url}/predict"

        try:
            # Prepare file for upload
            files = {"file": (audio_file.name, audio_file, audio_file.type)}

            # Prepare form data
            data = {
                "max_duration": max_duration,
                "return_probabilities": "true"
            }

            start_time = time.time()

            # Make request
            response = self.session.post(
                predict_url,
                files=files,
                data=data,
                timeout=60
            )

            processing_time = time.time() - start_time

            response.raise_for_status()
            result = response.json()

            # Add processing time to result
            result["processing_time"] = processing_time

            return result

        except requests.exceptions.Timeout:
            st.error("Request timed out. The audio file might be too large or the server is busy.")
            return None
        except requests.exceptions.RequestException as e:
            st.error(f"API request failed: {str(e)}")
            return None
        except json.JSONDecodeError:
            st.error("Invalid response from server")
            return None

    def get_supported_formats(self, api_url: str = None) -> list:
        """Get list of supported audio formats from backend"""
        url = (api_url or self.base_url).rstrip('/')

        try:
            response = self.session.get(f"{url}/info", timeout=5)
            response.raise_for_status()
            info = response.json()
            return info.get("supported_formats", ["wav", "mp3", "flac", "m4a"])
        except requests.exceptions.RequestException:
            return ["wav", "mp3", "flac", "m4a"]  # Default formats

    def get_model_info(self, api_url: str = None) -> Dict[str, Any]:
        """Get model information from backend"""
        url = (api_url or self.base_url).rstrip('/')

        try:
            response = self.session.get(f"{url}/model/info", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException:
            return {"status": "unavailable"}

    def test_endpoint(self, endpoint_name: str, api_url: str = None) -> bool:
        """Test if a specific endpoint is available"""
        url = (api_url or self.base_url).rstrip('/')

        try:
            response = self.session.get(f"{url}/{endpoint_name}", timeout=5)
            return response.status_code != 404
        except requests.exceptions.RequestException:
            return False