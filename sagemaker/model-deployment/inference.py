#!/usr/bin/env python3
"""
SageMaker Inference Script for Speech Emotion Recognition

This script contains the model loading and prediction functions that will be
executed on SageMaker endpoints for speech emotion recognition.
"""

import os
import sys
import logging
import json
import numpy as np
import torch
import torchaudio
import librosa
from typing import Dict, Any, List, Union
from transformers import AutoProcessor, AutoModelForAudioClassification
import base64
import io
from contextlib import contextmanager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelService:
    """SageMaker model service for speech emotion recognition."""

    def __init__(self, model_path: str = None):
        """Initialize the model service."""
        self.model_path = model_path or os.environ.get('SM_MODEL_DIR', '/opt/ml/model')
        self.model = None
        self.processor = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.sample_rate = 16000
        self.max_audio_length = 30  # Maximum audio length in seconds

    def model_fn(self, model_dir: str) -> Dict[str, Any]:
        """
        Load the model for inference.
        This function is called by SageMaker to load the model.
        """
        try:
            logger.info("Loading model for inference...")
            logger.info(f"Model directory: {model_dir}")
            logger.info(f"Using device: {self.device}")

            # Load model and processor
            model_name = os.path.join(model_dir, "ehcalabres_wav2vec2-lg-xlsr-en-speech-emotion-recognition")
            if not os.path.exists(model_name):
                # Fall back to downloading from HuggingFace if not found locally
                model_name = "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition"
                logger.info(f"Loading model from HuggingFace: {model_name}")
            else:
                logger.info(f"Loading model from local path: {model_name}")

            # Use correct processor and model for wav2vec2
            from transformers import Wav2Vec2FeatureExtractor, Wav2Vec2ForSequenceClassification
            self.processor = Wav2Vec2FeatureExtractor.from_pretrained(model_name)
            self.model = Wav2Vec2ForSequenceClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()

            logger.info("✅ Model loaded successfully")
            logger.info(f"Model architecture: {self.model.config.architectures}")
            logger.info(f"Number of labels: {self.model.config.num_labels}")

            # Store label mapping
            self.id2label = self.model.config.id2label
            self.label2id = self.model.config.label2id

            return {
                "model": self.model,
                "processor": self.processor,
                "sample_rate": self.sample_rate,
                "max_audio_length": self.max_audio_length,
                "id2label": self.id2label,
                "label2id": self.label2id
            }

        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            raise

    def input_fn(self, input_data: bytes, content_type: str) -> Dict[str, Any]:
        """
        Preprocess input data for inference.
        This function is called by SageMaker to preprocess input data.
        """
        try:
            logger.info(f"Processing input with content type: {content_type}")

            if content_type == "application/json":
                # Parse JSON input
                if isinstance(input_data, bytes):
                    data = json.loads(input_data.decode('utf-8'))
                else:
                    data = json.loads(input_data)

                # Handle different input formats
                if "audio_base64" in data:
                    # Base64 encoded audio data
                    audio_bytes = base64.b64decode(data["audio_base64"])
                    audio_array = self._load_audio_from_bytes(audio_bytes)
                elif "audio_url" in data:
                    # Audio URL (would need to download - not implemented for security)
                    raise ValueError("Audio URL input not supported in SageMaker environment")
                elif "audio_array" in data:
                    # Raw audio array
                    audio_array = np.array(data["audio_array"])
                else:
                    raise ValueError("No valid audio data found in input")

                # Get sample rate if provided
                sample_rate = data.get("sample_rate", 16000)

            elif content_type == "application/x-audio":
                # Raw audio bytes
                audio_array = self._load_audio_from_bytes(input_data)
                sample_rate = 16000

            elif content_type == "audio/wav" or content_type == "audio/mpeg":
                # Audio file bytes
                audio_array = self._load_audio_from_bytes(input_data)
                sample_rate = 16000

            else:
                raise ValueError(f"Unsupported content type: {content_type}")

            # Validate and preprocess audio
            processed_audio = self._preprocess_audio(audio_array, sample_rate)

            logger.info(f"✅ Input processed successfully")
            logger.info(f"Audio shape: {processed_audio.shape}")

            return {
                "audio": processed_audio,
                "sample_rate": self.sample_rate
            }

        except Exception as e:
            logger.error(f"❌ Input preprocessing failed: {e}")
            raise

    def predict_fn(self, input_data: Dict[str, Any], model: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform inference on preprocessed data.
        This function is called by SageMaker to perform inference.
        """
        try:
            logger.info("Performing emotion recognition inference...")

            audio = input_data["audio"]
            model_instance = model["model"]
            processor = model["processor"]
            id2label = model["id2label"]

            # Process audio for model input
            inputs = processor(
                audio,
                sampling_rate=self.sample_rate,
                return_tensors="pt",
                padding=True
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Perform inference
            with torch.no_grad():
                outputs = model_instance(**inputs)
                logits = outputs.logits
                probabilities = torch.nn.functional.softmax(logits, dim=-1)

            # Get predictions
            predicted_class_idx = torch.argmax(probabilities, dim=-1).item()
            predicted_label = id2label[predicted_class_idx]
            confidence = probabilities[0, predicted_class_idx].item()

            # Get all emotion probabilities
            emotion_scores = {}
            for idx, label in id2label.items():
                emotion_scores[label] = float(probabilities[0, idx].item())

            # Sort emotions by confidence
            sorted_emotions = sorted(
                emotion_scores.items(),
                key=lambda x: x[1],
                reverse=True
            )

            result = {
                "predicted_emotion": predicted_label,
                "confidence": float(confidence),
                "all_emotions": emotion_scores,
                "top_3_emotions": [
                    {"emotion": emotion, "score": float(score)}
                    for emotion, score in sorted_emotions[:3]
                ],
                "model_info": {
                    "model_type": "wav2vec2-lg-xlsr-speech-emotion",
                    "num_labels": len(id2label),
                    "supported_emotions": list(id2label.values())
                }
            }

            logger.info(f"✅ Inference completed successfully")
            logger.info(f"Predicted emotion: {predicted_label} (confidence: {confidence:.3f})")

            return result

        except Exception as e:
            logger.error(f"❌ Inference failed: {e}")
            raise

    def output_fn(self, prediction_output: Dict[str, Any], accept: str) -> bytes:
        """
        Postprocess and format the output.
        This function is called by SageMaker to format the output.
        """
        try:
            logger.info(f"Formatting output with accept type: {accept}")

            if accept == "application/json":
                # Return JSON response
                response = json.dumps(prediction_output)
                return response.encode('utf-8')

            elif accept == "text/csv":
                # Return CSV format (simplified)
                output = [
                    f"emotion,{prediction_output['predicted_emotion']}",
                    f"confidence,{prediction_output['confidence']}"
                ]
                return '\n'.join(output).encode('utf-8')

            else:
                # Default to JSON
                response = json.dumps(prediction_output)
                return response.encode('utf-8')

        except Exception as e:
            logger.error(f"❌ Output formatting failed: {e}")
            raise

    def _load_audio_from_bytes(self, audio_bytes: bytes) -> np.ndarray:
        """Load audio from bytes using librosa."""
        try:
            # Use librosa to load audio from bytes
            audio, sr = librosa.load(io.BytesIO(audio_bytes), sr=None)
            return audio
        except Exception as e:
            logger.error(f"Failed to load audio from bytes: {e}")
            # Try alternative approach with torchaudio
            try:
                buffer = io.BytesIO(audio_bytes)
                waveform, sample_rate = torchaudio.load(buffer)
                audio = waveform.squeeze().numpy()
                return audio
            except Exception as e2:
                logger.error(f"Failed to load audio with torchaudio: {e2}")
                raise ValueError(f"Could not load audio data: {e}")

    def _preprocess_audio(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Preprocess audio for model input."""
        try:
            logger.info(f"Preprocessing audio: original_sr={sample_rate}, length={len(audio)/sample_rate:.2f}s")

            # Resample to target sample rate if needed
            if sample_rate != self.sample_rate:
                audio = librosa.resample(
                    audio,
                    orig_sr=sample_rate,
                    target_sr=self.sample_rate
                )
                logger.info(f"Resampled audio to {self.sample_rate}Hz")

            # Trim or pad audio to maximum length
            max_length = int(self.sample_rate * self.max_audio_length)
            if len(audio) > max_length:
                # Trim to max length
                audio = audio[:max_length]
                logger.info(f"Trimmed audio to {self.max_audio_length}s")
            elif len(audio) < max_length:
                # Pad with zeros (this should be handled by the processor)
                logger.info(f"Audio length: {len(audio)/self.sample_rate:.2f}s (will be padded by processor)")

            # Validate audio
            if len(audio) == 0:
                raise ValueError("Audio is empty after preprocessing")

            # Check for invalid values
            if np.any(np.isnan(audio)) or np.any(np.isinf(audio)):
                logger.warning("Audio contains NaN or Inf values, applying correction")
                audio = np.nan_to_num(audio, nan=0.0, posinf=1.0, neginf=-1.0)

            # Normalize audio
            if np.max(np.abs(audio)) > 0:
                audio = audio / np.max(np.abs(audio))

            logger.info(f"✅ Audio preprocessing completed: shape={audio.shape}")
            return audio

        except Exception as e:
            logger.error(f"❌ Audio preprocessing failed: {e}")
            raise


# SageMaker required functions
model_service = ModelService()


def model_fn(model_dir: str = None):
    """SageMaker model loading function."""
    if model_dir is None:
        model_dir = os.environ.get('SM_MODEL_DIR', '/opt/ml/model')
    return model_service.model_fn(model_dir)


def input_fn(input_data: bytes, content_type: str):
    """SageMaker input preprocessing function."""
    return model_service.input_fn(input_data, content_type)


def predict_fn(input_data: Dict[str, Any], model: Dict[str, Any]):
    """SageMaker prediction function."""
    return model_service.predict_fn(input_data, model)


def output_fn(prediction_output: Dict[str, Any], accept: str):
    """SageMaker output formatting function."""
    return model_service.output_fn(prediction_output, accept)


# Health check endpoint
def health_check():
    """Health check for the model service."""
    return {
        "status": "healthy",
        "model": "wav2vec2-lg-xlsr-speech-emotion",
        "device": str(model_service.device),
        "sample_rate": model_service.sample_rate
    }


if __name__ == "__main__":
    # Test the model service locally
    import argparse

    parser = argparse.ArgumentParser(description="Test SageMaker inference script")
    parser.add_argument("--test", action="store_true", help="Run local test")
    parser.add_argument("--audio", type=str, help="Path to test audio file")
    args = parser.parse_args()

    if args.test:
        logger.info("Testing model service locally...")

        # Initialize model
        model_data = model_fn(".")

        if args.audio and os.path.exists(args.audio):
            # Test with audio file
            import base64

            with open(args.audio, "rb") as f:
                audio_data = f.read()

            test_input = base64.b64encode(audio_data).decode('utf-8')
            input_json = json.dumps({
                "audio_base64": test_input,
                "sample_rate": 16000
            }).encode('utf-8')

            # Test the pipeline
            processed_input = input_fn(input_json, "application/json")
            prediction = predict_fn(processed_input, model_data)
            output = output_fn(prediction, "application/json")

            logger.info("Test output:")
            print(output.decode('utf-8'))
        else:
            logger.info("No audio file provided. Health check only.")
            print(json.dumps(health_check(), indent=2))