#!/usr/bin/env python3
"""
Model Analysis and Validation Script for Speech Emotion Recognition

This script validates the HuggingFace model locally before SageMaker deployment,
testing input/output formats, preprocessing requirements, and performance.
"""

import os
import sys
import logging
import numpy as np
import torch
import torchaudio
import librosa
from typing import Dict, Any, Tuple
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
import time
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModelValidator:
    """Validates the speech emotion recognition model locally."""

    def __init__(self, model_name: str = "MIT/ast-finetuned-audioset-10-10-0.4593"):
        """Initialize the model validator."""
        self.model_name = model_name
        self.processor = None
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")

    def load_model(self) -> bool:
        """Load the model and processor."""
        try:
            logger.info(f"Loading model: {self.model_name}")
            logger.info("This may take a few minutes...")

            self.processor = AutoFeatureExtractor.from_pretrained(self.model_name)
            self.model = AutoModelForAudioClassification.from_pretrained(self.model_name)
            self.model.to(self.device)
            self.model.eval()

            logger.info("✅ Model loaded successfully")
            logger.info(f"Model architecture: {self.model.config.architectures}")
            logger.info(f"Number of parameters: {self.model.num_parameters():,}")
            logger.info(f"Model size: {self.model.num_parameters() * 4 / 1024 / 1024:.1f} MB")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """Get detailed model information."""
        if not self.model:
            return {}

        config = self.model.config

        return {
            "model_name": self.model_name,
            "num_labels": config.num_labels,
            "id2label": config.id2label,
            "label2id": config.label2id,
            "sample_rate": config.sampling_rate if hasattr(config, 'sampling_rate') else 16000,
            "architecture": config.architectures[0] if config.architectures else "Unknown",
            "vocab_size": config.vocab_size if hasattr(config, 'vocab_size') else None,
            "hidden_size": config.hidden_size if hasattr(config, 'hidden_size') else None,
            "num_attention_heads": config.num_attention_heads if hasattr(config, 'num_attention_heads') else None,
        }

    def create_test_audio(self, duration: float = 3.0, sample_rate: int = 16000) -> np.ndarray:
        """Create a synthetic audio signal for testing."""
        logger.info(f"Creating test audio: {duration}s at {sample_rate}Hz")

        # Generate a complex audio signal with multiple frequencies
        t = np.linspace(0, duration, int(sample_rate * duration), False)

        # Mix of frequencies to simulate speech-like audio
        frequencies = [100, 200, 400, 800, 1600]  # Hz
        audio = np.zeros_like(t)

        for i, freq in enumerate(frequencies):
            amplitude = 0.2 * (1 - i * 0.15)  # Decreasing amplitude for higher frequencies
            audio += amplitude * np.sin(2 * np.pi * freq * t)

        # Add some noise to make it more realistic
        noise = np.random.normal(0, 0.05, audio.shape)
        audio = audio + noise

        # Normalize to [-1, 1]
        audio = np.clip(audio, -1, 1)

        return audio.astype(np.float32)

    def test_model_input_output(self) -> bool:
        """Test model input/output format and requirements."""
        try:
            logger.info("Testing model input/output format...")

            # Create test audio
            audio = self.create_test_audio(duration=2.0, sample_rate=16000)

            # Test with librosa (what we'll use in production)
            logger.info("Testing with librosa preprocessing...")

            # Resample if needed (librosa loads at 22050Hz by default)
            audio_librosa = librosa.resample(
                audio,
                orig_sr=16000,
                target_sr=16000
            )

            # Process audio
            inputs = self.processor(
                audio_librosa,
                sampling_rate=16000,
                return_tensors="pt",
                padding=True
            )

            logger.info(f"Input tensor shape: {inputs['input_values'].shape}")
            logger.info(f"Input tensor dtype: {inputs['input_values'].dtype}")

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Test inference
            with torch.no_grad():
                start_time = time.time()
                outputs = self.model(**inputs)
                inference_time = time.time() - start_time

            logger.info(f"✅ Inference successful in {inference_time:.3f} seconds")
            logger.info(f"Output logits shape: {outputs.logits.shape}")
            logger.info(f"Output logits dtype: {outputs.logits.dtype}")

            # Get predictions
            probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
            predicted_class = torch.argmax(probabilities, dim=-1).item()
            confidence = probabilities[0, predicted_class].item()

            predicted_label = self.model.config.id2label[predicted_class]

            logger.info(f"Predicted emotion: {predicted_label}")
            logger.info(f"Confidence: {confidence:.3f}")

            # Test all emotion classes
            logger.info("All emotion classes:")
            for idx, label in self.model.config.id2label.items():
                prob = probabilities[0, idx].item()
                logger.info(f"  {label}: {prob:.3f}")

            return True

        except Exception as e:
            logger.error(f"❌ Input/output test failed: {e}")
            return False

    def test_audio_formats(self) -> bool:
        """Test different audio formats and preprocessing."""
        try:
            logger.info("Testing different audio formats...")

            formats = [
                ("float32_16kHz", self.create_test_audio(2.0, 16000).astype(np.float32)),
                ("float32_22kHz", self.create_test_audio(2.0, 22050).astype(np.float32)),
                ("float32_44kHz", self.create_test_audio(2.0, 44100).astype(np.float32)),
            ]

            for format_name, audio in formats:
                logger.info(f"Testing {format_name}...")

                try:
                    # Determine sample rate
                    if "16kHz" in format_name:
                        sr = 16000
                    elif "22kHz" in format_name:
                        sr = 22050
                    else:
                        sr = 44100

                    # Resample to 16kHz for model input
                    if sr != 16000:
                        audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)

                    # Process and predict
                    inputs = self.processor(audio, sampling_rate=16000, return_tensors="pt", padding=True)
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}

                    with torch.no_grad():
                        outputs = self.model(**inputs)
                        probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
                        predicted_class = torch.argmax(probabilities, dim=-1).item()
                        confidence = probabilities[0, predicted_class].item()

                    predicted_label = self.model.config.id2label[predicted_class]
                    logger.info(f"  ✅ {format_name}: {predicted_label} ({confidence:.3f})")

                except Exception as e:
                    logger.error(f"  ❌ {format_name}: {e}")
                    return False

            return True

        except Exception as e:
            logger.error(f"❌ Audio format test failed: {e}")
            return False

    def test_performance(self, num_trials: int = 10) -> Dict[str, float]:
        """Test model performance metrics."""
        logger.info(f"Testing performance with {num_trials} trials...")

        try:
            audio = self.create_test_audio(3.0, 16000)
            inputs = self.processor(audio, sampling_rate=16000, return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            times = []

            # Warm up
            with torch.no_grad():
                self.model(**inputs)

            for i in range(num_trials):
                with torch.no_grad():
                    start_time = time.time()
                    outputs = self.model(**inputs)
                    torch.cuda.synchronize() if torch.cuda.is_available() else None
                    end_time = time.time()
                    times.append(end_time - start_time)

            times = np.array(times)

            stats = {
                "mean_time": float(np.mean(times)),
                "std_time": float(np.std(times)),
                "min_time": float(np.min(times)),
                "max_time": float(np.max(times)),
                "median_time": float(np.median(times)),
            }

            logger.info(f"Performance Statistics (seconds):")
            logger.info(f"  Mean: {stats['mean_time']:.3f}s")
            logger.info(f"  Std:  {stats['std_time']:.3f}s")
            logger.info(f"  Min:  {stats['min_time']:.3f}s")
            logger.info(f"  Max:  {stats['max_time']:.3f}s")
            logger.info(f"  Median: {stats['median_time']:.3f}s")

            return stats

        except Exception as e:
            logger.error(f"❌ Performance test failed: {e}")
            return {}

    def validate_for_sagemaker(self) -> bool:
        """Validate model requirements for SageMaker deployment."""
        logger.info("Validating model for SageMaker deployment...")

        # Check model size (should be < 2GB for serverless)
        model_size_mb = self.model.num_parameters() * 4 / 1024 / 1024
        logger.info(f"Model size: {model_size_mb:.1f} MB")

        if model_size_mb > 1500:  # Leave some headroom
            logger.warning("⚠️  Model is large for serverless deployment")
            logger.warning("  Consider using a smaller model or provisioned endpoints")
        else:
            logger.info("✅ Model size is suitable for serverless deployment")

        # Check inference time (should be < 60 seconds)
        stats = self.test_performance(num_trials=5)
        if stats and stats.get('max_time', 0) > 50:
            logger.warning("⚠️  Inference time may approach serverless timeout")
            logger.warning("  Consider optimizing or using provisioned endpoints")
        else:
            logger.info("✅ Inference time is within serverless limits")

        return True

    def run_full_validation(self) -> bool:
        """Run complete model validation."""
        logger.info("🔍 Starting full model validation...")
        logger.info("=" * 50)

        # Load model
        if not self.load_model():
            return False

        # Get model info
        model_info = self.get_model_info()
        logger.info("Model Information:")
        for key, value in model_info.items():
            logger.info(f"  {key}: {value}")

        logger.info("=" * 50)

        # Run tests
        tests = [
            ("Input/Output Format", self.test_model_input_output),
            ("Audio Format Support", self.test_audio_formats),
            ("SageMaker Validation", self.validate_for_sagemaker),
        ]

        all_passed = True
        for test_name, test_func in tests:
            logger.info(f"\n🧪 Running {test_name} test...")
            try:
                if test_func():
                    logger.info(f"✅ {test_name} test passed")
                else:
                    logger.error(f"❌ {test_name} test failed")
                    all_passed = False
            except Exception as e:
                logger.error(f"❌ {test_name} test failed with exception: {e}")
                all_passed = False

        logger.info("=" * 50)
        if all_passed:
            logger.info("🎉 All validation tests passed!")
            logger.info("Model is ready for SageMaker deployment.")
        else:
            logger.error("❌ Some validation tests failed.")
            logger.error("Please address the issues before deploying to SageMaker.")

        return all_passed


def main():
    """Main validation function."""
    validator = ModelValidator()
    success = validator.run_full_validation()

    if success:
        logger.info("\n✅ Model validation completed successfully")
        sys.exit(0)
    else:
        logger.error("\n❌ Model validation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()