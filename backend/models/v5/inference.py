"""
SageMaker Inference Handler for Speech Emotion Recognition (Option A)

This module provides minimal inference functions for AWS SageMaker deployment
where feature extraction is handled by the backend API.

Backend sends pre-computed features (210 floats) to SageMaker.
SageMaker loads model and runs prediction only.

SageMaker expects these functions:
- model_fn: Load the model from the model directory
- input_fn: Parse pre-computed features from request
- predict_fn: Run prediction on features
- output_fn: Format prediction output

Reference: https://sagemaker.readthedocs.io/en/stable/frameworks/sklearn/using_sklearn.html
"""

import os
import pickle
import json
import logging
from typing import Dict, Any

import numpy as np

# Import UltraEnsembleModel - REQUIRED for unpickling model.pkl
from ultra_ensemble import UltraEnsembleModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def model_fn(model_dir: str):
    """
    Load the model from the model directory.

    SageMaker calls this function once when the endpoint is initialized.
    The model is cached in memory for all subsequent requests.

    CRITICAL: Must import UltraEnsembleModel before unpickling,
    otherwise pickle.load() will fail with AttributeError.

    Args:
        model_dir: Path to the directory containing model artifacts
                   (typically /opt/ml/model in SageMaker)

    Returns:
        Loaded model object (UltraEnsembleModel instance)
    """
    model_path = os.path.join(model_dir, 'model.pkl')

    logger.info(f"Loading model from {model_path}")

    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)

        logger.info(f"Model loaded successfully: {type(model).__name__}")
        return model

    except Exception as e:
        logger.error(f"Failed to load model: {str(e)}")
        raise


def input_fn(request_body: str, request_content_type: str) -> np.ndarray:
    """
    Parse pre-computed features from request.

    Backend extracts features locally and sends them as JSON:
    {"features": [0.1, 0.2, ..., 0.9]}  # 210 floats

    Args:
        request_body: The raw request body (JSON string)
        request_content_type: Content type of the request

    Returns:
        np.ndarray of shape (1, 210) ready for model.predict()

    Expected input format (JSON):
    {
        "features": [0.1, 0.2, ..., 0.9]  # List of 210 floats
    }
    """
    if request_content_type != 'application/json':
        raise ValueError(
            f"Unsupported content type: {request_content_type}. "
            f"Expected application/json"
        )

    try:
        # Parse JSON request
        data = json.loads(request_body)

        # Extract features
        features = data.get('features')

        if features is None:
            raise ValueError("Missing required field: features")

        # Convert to numpy array
        features_array = np.array(features, dtype=np.float64)

        # Validate shape
        if features_array.shape[0] != 210:
            raise ValueError(
                f"Expected 210 features, got {features_array.shape[0]}"
            )

        # Reshape to (1, 210) for single prediction
        features_2d = features_array.reshape(1, -1)

        logger.info(f"Features parsed: shape={features_2d.shape}")

        return features_2d

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request body: {str(e)}")
        raise ValueError(f"Invalid JSON: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to process input: {str(e)}")
        raise ValueError(f"Input processing failed: {str(e)}")


def predict_fn(features: np.ndarray, model) -> Dict[str, Any]:
    """
    Run prediction on pre-computed features.

    Args:
        features: Feature array of shape (1, 210) from input_fn
        model: Loaded model from model_fn

    Returns:
        Dictionary containing prediction and probabilities
    """
    try:
        logger.info(f"Running prediction on features: shape={features.shape}")

        # Predict emotion
        prediction = model.predict(features)[0]
        probabilities = model.predict_proba(features)[0]

        # Get emotion class names
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
            'prediction': prediction,
            'probabilities': probabilities,
            'emotion_classes': emotion_classes,
            'prob_dict': prob_dict,
            'confidence': confidence
        }

        logger.info(f"Prediction: {prediction} (confidence: {confidence:.4f})")

        return result

    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}")
        raise RuntimeError(f"Prediction failed: {str(e)}")


def output_fn(prediction_dict: Dict[str, Any], response_content_type: str = 'application/json') -> str:
    """
    Format the prediction output.

    Args:
        prediction_dict: Prediction dictionary from predict_fn
        response_content_type: Desired response content type

    Returns:
        JSON-formatted response string

    Output format:
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
    """
    if response_content_type != 'application/json':
        raise ValueError(
            f"Unsupported response content type: {response_content_type}"
        )

    try:
        response = {
            'emotion': str(prediction_dict['prediction']),
            'confidence': prediction_dict['confidence'],
            'probabilities': prediction_dict['prob_dict'],
            'model_version': os.getenv('MODEL_VERSION', 'unknown')
        }

        json_response = json.dumps(response, indent=2)
        return json_response

    except Exception as e:
        logger.error(f"Failed to format output: {str(e)}")
        raise RuntimeError(f"Output formatting failed: {str(e)}")
