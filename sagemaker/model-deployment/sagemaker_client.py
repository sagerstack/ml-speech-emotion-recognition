#!/usr/bin/env python3
"""
SageMaker Client for Backend Integration

This module provides a client interface for interacting with the SageMaker
speech emotion recognition endpoint from backend applications.
"""

import os
import sys
import json
import time
import logging
import base64
import boto3
from datetime import datetime
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError, BotoCoreError
from dataclasses import dataclass
from enum import Enum
import yaml
from pathlib import Path


def json_serializer(obj):
    """JSON serializer for datetime objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmotionLabel(Enum):
    """Standard emotion labels from the model."""
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    NEUTRAL = "neutral"
    FEARFUL = "fearful"
    DISGUSTED = "disgusted"
    SURPRISED = "surprised"
    CALM = "calm"


@dataclass
class EmotionResult:
    """Data class for emotion recognition results."""
    predicted_emotion: str
    confidence: float
    all_emotions: Dict[str, float]
    top_3_emotions: List[Dict[str, float]]
    model_info: Dict[str, Any]
    processing_time: float
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "predicted_emotion": self.predicted_emotion,
            "confidence": self.confidence,
            "all_emotions": self.all_emotions,
            "top_3_emotions": self.top_3_emotions,
            "model_info": self.model_info,
            "processing_time": self.processing_time,
            "timestamp": self.timestamp
        }


@dataclass
class SageMakerConfig:
    """Configuration for SageMaker client."""
    endpoint_name: str
    region: str = "us-east-1"
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 60.0
    content_type: str = "application/json"
    accept_type: str = "application/json"


class SageMakerClientError(Exception):
    """Custom exception for SageMaker client errors."""
    pass


class SageMakerClient:
    """Client for interacting with SageMaker speech emotion recognition endpoint."""

    def __init__(self, config: SageMakerConfig):
        """Initialize the SageMaker client."""
        self.config = config
        self.client = boto3.client(
            'sagemaker-runtime',
            region_name=config.region
        )
        logger.info(f"✅ SageMaker client initialized for endpoint: {config.endpoint_name}")

    @classmethod
    def from_config_file(cls, config_path: str, endpoint_name: Optional[str] = None) -> 'SageMakerClient':
        """Create client from configuration file."""
        try:
            config_file = Path(config_path)
            with open(config_file, 'r') as f:
                config_data = yaml.safe_load(f)

            aws_config = config_data.get('aws', {})
            serverless_config = config_data.get('serverless', {})

            config = SageMakerConfig(
                endpoint_name=endpoint_name or os.getenv('SAGEMAKER_ENDPOINT_NAME', ''),
                region=aws_config.get('region', 'us-east-1'),
                timeout=serverless_config.get('timeout_in_seconds', 60.0)
            )

            return cls(config)

        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            raise

    @classmethod
    def from_env(cls) -> 'SageMakerClient':
        """Create client from environment variables."""
        config = SageMakerConfig(
            endpoint_name=os.getenv('SAGEMAKER_ENDPOINT_NAME', ''),
            region=os.getenv('AWS_REGION', 'us-east-1'),
            max_retries=int(os.getenv('SAGEMAKER_MAX_RETRIES', '3')),
            retry_delay=float(os.getenv('SAGEMAKER_RETRY_DELAY', '1.0')),
            timeout=float(os.getenv('SAGEMAKER_TIMEOUT', '60.0'))
        )

        if not config.endpoint_name:
            raise ValueError("SAGEMAKER_ENDPOINT_NAME environment variable is required")

        return cls(config)

    def _invoke_with_retry(self, payload: str) -> Dict[str, Any]:
        """Invoke SageMaker endpoint with retry logic."""
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                logger.debug(f"Invocation attempt {attempt + 1}/{self.config.max_retries + 1}")

                response = self.client.invoke_endpoint(
                    EndpointName=self.config.endpoint_name,
                    ContentType=self.config.content_type,
                    Accept=self.config.accept_type,
                    Body=payload
                )

                # Parse response
                result = json.loads(response['Body'].read().decode('utf-8'))
                logger.debug("✅ Endpoint invocation successful")
                return result

            except ClientError as e:
                last_exception = e
                error_code = e.response['Error']['Code']

                if error_code in ['ModelTimeoutError', 'InternalServerException', 'ServiceUnavailable']:
                    if attempt < self.config.max_retries:
                        wait_time = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Endpoint error {error_code}, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Max retries exceeded for error {error_code}")
                        break

                elif error_code in ['ValidationError', 'ModelNotReadyException']:
                    logger.error(f"Non-retryable error {error_code}: {e}")
                    break

                else:
                    if attempt < self.config.max_retries:
                        logger.warning(f"Unexpected error {error_code}, retrying...")
                        time.sleep(self.config.retry_delay)
                        continue
                    else:
                        break

            except BotoCoreError as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    logger.warning(f"BotoCore error, retrying: {e}")
                    time.sleep(self.config.retry_delay)
                    continue
                else:
                    break

            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error during invocation: {e}")
                break

        # If we get here, all retries failed
        raise SageMakerClientError(f"Failed to invoke endpoint after {self.config.max_retries + 1} attempts: {last_exception}")

    def predict_emotion_from_base64(self, audio_base64: str, sample_rate: int = 16000) -> EmotionResult:
        """Predict emotion from base64-encoded audio."""
        try:
            start_time = time.time()

            # Prepare input
            input_data = {
                "audio_base64": audio_base64,
                "sample_rate": sample_rate
            }

            payload = json.dumps(input_data)

            # Invoke endpoint
            result = self._invoke_with_retry(payload)
            processing_time = time.time() - start_time

            # Handle errors in response
            if "error" in result:
                raise SageMakerClientError(f"Endpoint returned error: {result['error']}")

            # Create EmotionResult
            emotion_result = EmotionResult(
                predicted_emotion=result.get("predicted_emotion", "unknown"),
                confidence=result.get("confidence", 0.0),
                all_emotions=result.get("all_emotions", {}),
                top_3_emotions=result.get("top_3_emotions", []),
                model_info=result.get("model_info", {}),
                processing_time=processing_time,
                timestamp=time.time()
            )

            logger.info(f"✅ Emotion prediction: {emotion_result.predicted_emotion} "
                       f"(confidence: {emotion_result.confidence:.3f}, "
                       f"time: {emotion_result.processing_time:.3f}s)")

            return emotion_result

        except Exception as e:
            logger.error(f"❌ Emotion prediction failed: {e}")
            raise

    def predict_emotion_from_file(self, audio_file_path: str) -> EmotionResult:
        """Predict emotion from audio file."""
        try:
            logger.debug(f"Processing audio file: {audio_file_path}")

            # Read and encode audio file
            with open(audio_file_path, 'rb') as f:
                audio_bytes = f.read()

            audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

            return self.predict_emotion_from_base64(audio_base64)

        except Exception as e:
            logger.error(f"❌ Failed to process audio file {audio_file_path}: {e}")
            raise

    def predict_emotion_from_array(self, audio_array: List[float], sample_rate: int = 16000) -> EmotionResult:
        """Predict emotion from audio array."""
        try:
            import soundfile as sf
            import io

            # Convert array to audio bytes
            buffer = io.BytesIO()
            sf.write(buffer, audio_array, sample_rate, format='WAV')
            buffer.seek(0)

            audio_base64 = base64.b64encode(buffer.read()).decode('utf-8')

            return self.predict_emotion_from_base64(audio_base64, sample_rate)

        except Exception as e:
            logger.error(f"❌ Failed to process audio array: {e}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the endpoint."""
        try:
            logger.info("Performing endpoint health check...")

            # Create minimal test audio
            import numpy as np
            test_audio = np.random.randn(16000).astype(np.float32)  # 1 second of noise

            # Convert to base64
            import soundfile as sf
            import io
            buffer = io.BytesIO()
            sf.write(buffer, test_audio, 16000, format='WAV')
            buffer.seek(0)
            audio_base64 = base64.b64encode(buffer.read()).decode('utf-8')

            # Test prediction
            start_time = time.time()
            result = self.predict_emotion_from_base64(audio_base64)
            response_time = time.time() - start_time

            health_status = {
                "endpoint_name": self.config.endpoint_name,
                "status": "healthy",
                "response_time": response_time,
                "predicted_emotion": result.predicted_emotion,
                "confidence": result.confidence,
                "timestamp": time.time()
            }

            logger.info(f"✅ Endpoint health check passed (response time: {response_time:.3f}s)")
            return health_status

        except Exception as e:
            logger.error(f"❌ Endpoint health check failed: {e}")
            return {
                "endpoint_name": self.config.endpoint_name,
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }

    def get_endpoint_info(self) -> Dict[str, Any]:
        """Get endpoint information."""
        try:
            sagemaker_client = boto3.client('sagemaker', region_name=self.config.region)
            response = sagemaker_client.describe_endpoint(EndpointName=self.config.endpoint_name)

            return {
                "endpoint_name": response.get("EndpointName"),
                "endpoint_arn": response.get("EndpointArn"),
                "endpoint_status": response.get("EndpointStatus"),
                "creation_time": response.get("CreationTime"),
                "last_modified_time": response.get("LastModifiedTime"),
                "production_variants": response.get("ProductionVariants", [])
            }

        except Exception as e:
            logger.error(f"Failed to get endpoint info: {e}")
            return {"error": str(e)}

    def batch_predict(self, audio_files: List[str]) -> List[EmotionResult]:
        """Predict emotions for multiple audio files."""
        try:
            logger.info(f"Processing batch prediction for {len(audio_files)} files...")

            results = []
            for i, audio_file in enumerate(audio_files):
                try:
                    logger.debug(f"Processing file {i+1}/{len(audio_files)}: {audio_file}")
                    result = self.predict_emotion_from_file(audio_file)
                    results.append(result)

                    # Small delay to avoid throttling
                    time.sleep(0.1)

                except Exception as e:
                    logger.error(f"Failed to process {audio_file}: {e}")
                    # Create error result
                    error_result = EmotionResult(
                        predicted_emotion="error",
                        confidence=0.0,
                        all_emotions={},
                        top_3_emotions=[],
                        model_info={},
                        processing_time=0.0,
                        timestamp=time.time()
                    )
                    results.append(error_result)

            successful_results = [r for r in results if r.predicted_emotion != "error"]
            logger.info(f"✅ Batch prediction completed: {len(successful_results)}/{len(audio_files)} successful")

            return results

        except Exception as e:
            logger.error(f"❌ Batch prediction failed: {e}")
            raise

    def validate_emotion_result(self, result: EmotionResult) -> bool:
        """Validate emotion prediction result."""
        try:
            # Check required fields
            if not result.predicted_emotion:
                logger.warning("Invalid result: missing predicted_emotion")
                return False

            if not isinstance(result.confidence, (int, float)) or not (0 <= result.confidence <= 1):
                logger.warning(f"Invalid result: invalid confidence {result.confidence}")
                return False

            if not result.all_emotions:
                logger.warning("Invalid result: missing all_emotions")
                return False

            # Check emotion labels
            valid_emotions = [e.value for e in EmotionLabel]
            if result.predicted_emotion not in valid_emotions:
                logger.warning(f"Invalid result: unknown emotion {result.predicted_emotion}")
                return False

            return True

        except Exception as e:
            logger.error(f"Result validation failed: {e}")
            return False


# Convenience function for quick usage
def create_client(endpoint_name: str, region: str = "us-east-1") -> SageMakerClient:
    """Create SageMaker client with default configuration."""
    config = SageMakerConfig(endpoint_name=endpoint_name, region=region)
    return SageMakerClient(config)


# Example usage
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SageMaker Client Test")
    parser.add_argument("--endpoint", required=True, help="SageMaker endpoint name")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--audio", help="Audio file to test")
    parser.add_argument("--health", action="store_true", help="Run health check")

    args = parser.parse_args()

    try:
        # Create client
        if args.config:
            client = SageMakerClient.from_config_file(args.config, args.endpoint)
        else:
            client = create_client(args.endpoint)

        if args.health:
            # Health check
            health = client.health_check()
            print("Health Check Result:")
            print(json.dumps(health, indent=2))

        elif args.audio:
            # Test with audio file
            result = client.predict_emotion_from_file(args.audio)
            print("Emotion Recognition Result:")
            print(json.dumps(result.to_dict(), indent=2))

        else:
            # Get endpoint info
            info = client.get_endpoint_info()
            print("Endpoint Information:")
            print(json.dumps(info, indent=2, default=json_serializer))

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        sys.exit(1)