"""
SageMaker Inference Handler for Speech Emotion Recognition

This module provides the inference functions required by AWS SageMaker for
serving the Ultra Ensemble model for speech emotion recognition.

SageMaker expects the following functions:
- model_fn: Load the model from the model directory
- input_fn: Parse and preprocess input data
- predict_fn: Run prediction on preprocessed input
- output_fn: Format prediction output

Reference: https://sagemaker.readthedocs.io/en/stable/frameworks/sklearn/using_sklearn.html#serve-a-scikit-learn-model
"""

import os
import pickle
import io
import json
import base64
import logging
from typing import Dict, Any, Tuple

import numpy as np
import librosa

# Import feature extractor - will be packaged with model
from feature_extractor import extract_features

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def model_fn(model_dir: str):
    """
    Load the model from the model directory.

    SageMaker calls this function once when the endpoint is initialized.
    The model is cached after loading.

    Args:
        model_dir: Path to the directory containing model artifacts
                   (typically /opt/ml/model in SageMaker)

    Returns:
        Loaded model object (scikit-learn UltraEnsembleModel)
    """
    model_path = os.path.join(model_dir, 'model.pkl')

    logger.info(f"Loading model from {model_path}")

    try:
        with open(model_path, 'rb') as f:
            # Use custom unpickler if needed for UltraEnsembleModel
            model = pickle.load(f)

        logger.info(f"Model loaded successfully: {type(model).__name__}")
        return model

    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise


def input_fn(request_body: str, request_content_type: str) -> Tuple[np.ndarray, int]:
    """
    Parse and preprocess the input data.

    Args:
        request_body: The raw request body (JSON string)
        request_content_type: Content type of the request

    Returns:
        Tuple of (audio_array, sample_rate)

    Expected input format (JSON):
    {
        "audio_base64": "<base64-encoded audio data>",
        "sample_rate": 16000  # optional, default is 16000
    }
    """
    if request_content_type != 'application/json':
        raise ValueError(f"Unsupported content type: {request_content_type}. Expected application/json")

    try:
        # Parse JSON request
        data = json.loads(request_body)

        # Extract parameters
        audio_base64 = data.get('audio_base64')
        sample_rate = data.get('sample_rate', 16000)

        if not audio_base64:
            raise ValueError("Missing required field: audio_base64")

        # Decode base64 audio
        audio_bytes = base64.b64decode(audio_base64)

        # Load audio with librosa
        audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=sample_rate)

        logger.info(f"Audio loaded: duration={len(audio)/sr:.2f}s, sample_rate={sr}Hz")

        return audio, sr

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {str(e)}")
        raise ValueError(f"Invalid JSON: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to process input: {str(e)}")
        raise ValueError(f"Input processing failed: {str(e)}")


def predict_fn(input_data: Tuple[np.ndarray, int], model) -> Dict[str, Any]:
    """
    Run prediction on preprocessed input.

    Args:
        input_data: Tuple of (audio_array, sample_rate) from input_fn
        model: Loaded model from model_fn

    Returns:
        Dictionary containing prediction and probabilities
    """
    audio, sr = input_data

    try:
        # Extract features (210 features for Ultra Ensemble model)
        logger.info("Extracting features from audio")
        features = extract_features(audio, sr)

        # Reshape for model input (1 sample x 210 features)
        features_array = np.array(features).reshape(1, -1)

        logger.info(f"Features extracted: shape={features_array.shape}")

        # Predict emotion
        prediction = model.predict(features_array)[0]
        probabilities = model.predict_proba(features_array)[0]

        # Get emotion class names (assuming model has classes_ attribute)
        if hasattr(model, 'classes_'):
            emotion_classes = model.classes_
        else:
            # Fallback to default CREMA-D emotion classes
            emotion_classes = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad']

        # Create probability distribution
        prob_dict = {
            emotion: float(prob)
            for emotion, prob in zip(emotion_classes, probabilities)
        }

        # Get confidence score
        confidence = float(probabilities.max())

        result = {
            'emotion': str(prediction),
            'confidence': confidence,
            'probabilities': prob_dict,
            'model_version': os.getenv('MODEL_VERSION', 'unknown')
        }

        logger.info(f"Prediction: {prediction} (confidence: {confidence:.4f})")

        return result

    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}")
        raise RuntimeError(f"Prediction failed: {str(e)}")


def output_fn(prediction: Dict[str, Any], response_content_type: str = 'application/json') -> str:
    """
    Format the prediction output.

    Args:
        prediction: Prediction dictionary from predict_fn
        response_content_type: Desired response content type

    Returns:
        JSON-formatted response string
    """
    if response_content_type != 'application/json':
        raise ValueError(f"Unsupported response content type: {response_content_type}")

    try:
        response = json.dumps(prediction, indent=2)
        return response

    except Exception as e:
        logger.error(f"Failed to format output: {str(e)}")
        raise RuntimeError(f"Output formatting failed: {str(e)}")
