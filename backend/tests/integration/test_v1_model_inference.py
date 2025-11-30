"""
Integration tests for Model v1 Full Inference Workflow.

This test suite validates the complete end-to-end inference flow for v1 model:
- Audio bytes → feature extraction → model prediction
- Full pipeline integration with ModelRegistry
- Real CREMA-D audio file processing
- Validation of complete prediction workflow
- Error handling through the entire pipeline

Focus: Application flow correctness, NOT model accuracy.
"""

import sys
import importlib.util
from pathlib import Path

# Dynamically import feature extractor to avoid path conflicts
FEATURE_EXTRACTOR_PATH = Path(__file__).resolve().parents[2] / "models" / "v1" / "feature_extractor.py"

spec = importlib.util.spec_from_file_location("v1_feature_extractor", FEATURE_EXTRACTOR_PATH)
v1_extractor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1_extractor_module)
extract_features = v1_extractor_module.extract_features

import io
import numpy as np
import pytest
import soundfile as sf

from app.services.model_registry import ModelRegistry, get_registry


@pytest.fixture
def registry():
    """Get initialized model registry."""
    registry = ModelRegistry()
    registry.discover_models()
    return registry


@pytest.fixture
def crema_d_audio_path():
    """Path to CREMA-D dataset."""
    return Path("/Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition/data/AudioWAV")


@pytest.fixture
def crema_d_sample(crema_d_audio_path):
    """Load a real CREMA-D audio sample."""
    # Try to find any CREMA-D file
    audio_files = list(crema_d_audio_path.glob("*.wav"))

    if not audio_files:
        pytest.skip("CREMA-D audio files not available")

    # Use the first available file
    audio_file = audio_files[0]

    with open(audio_file, 'rb') as f:
        audio_bytes = f.read()

    return audio_bytes, audio_file.name


@pytest.mark.integration
class TestV1FullInferencePipeline:
    """Test complete inference pipeline from audio to prediction."""

    def test_full_pipeline_audio_to_prediction(self, registry, sample_audio_file):
        """Test complete flow: audio bytes → features → prediction."""
        # Step 1: Extract features
        features = extract_features(sample_audio_file, "test.wav")

        assert features is not None, "Feature extraction should succeed"
        assert features.shape == (162,), "Features should have correct shape"

        # Step 2: Get model
        v1_model = registry.get_version("1")
        assert v1_model is not None, "v1 model should be available"

        # Step 3: Run prediction through registry
        result = registry.predict("1", sample_audio_file, "test.wav")

        # Validate complete result structure
        assert result is not None, "Prediction should return a result"
        assert isinstance(result, dict), "Result should be a dictionary"

        # Validate all required fields exist
        required_fields = [
            "emotion", "confidence", "all_probabilities",
            "model_version", "model_type", "feature_dimension"
        ]
        for field in required_fields:
            assert field in result, f"Result should have {field} field"

    def test_prediction_returns_valid_emotion_label(self, registry, sample_audio_file):
        """Test that prediction returns one of the 6 valid emotion labels."""
        result = registry.predict("1", sample_audio_file, "test.wav")

        valid_emotions = ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        emotion = result["emotion"]

        assert emotion in valid_emotions, \
            f"Emotion '{emotion}' should be one of {valid_emotions}"

    def test_prediction_confidence_valid_range(self, registry, sample_audio_file):
        """Test that confidence score is in valid [0, 1] range."""
        result = registry.predict("1", sample_audio_file, "test.wav")

        confidence = result["confidence"]

        assert isinstance(confidence, (float, np.floating)), \
            "Confidence should be a float"
        assert 0.0 <= confidence <= 1.0, \
            f"Confidence {confidence} should be in range [0, 1]"

    def test_prediction_all_probabilities_valid(self, registry, sample_audio_file):
        """Test that all_probabilities dict is valid."""
        result = registry.predict("1", sample_audio_file, "test.wav")

        all_probs = result["all_probabilities"]

        # Check it's a dictionary
        assert isinstance(all_probs, dict), "all_probabilities should be a dict"

        # Check it has all 6 emotion classes
        expected_classes = {"angry", "disgust", "fear", "happy", "neutral", "sad"}
        assert set(all_probs.keys()) == expected_classes, \
            f"Should have all classes, got {set(all_probs.keys())}"

        # Check all probabilities are valid numbers
        for emotion, prob in all_probs.items():
            assert isinstance(prob, (float, np.floating)), \
                f"Probability for {emotion} should be float"
            assert 0.0 <= prob <= 1.0, \
                f"Probability for {emotion} ({prob}) should be in [0, 1]"

    def test_prediction_probabilities_sum_to_one(self, registry, sample_audio_file):
        """Test that all probabilities sum to approximately 1.0."""
        result = registry.predict("1", sample_audio_file, "test.wav")

        all_probs = result["all_probabilities"]
        prob_sum = sum(all_probs.values())

        assert 0.99 <= prob_sum <= 1.01, \
            f"Probabilities should sum to ~1.0, got {prob_sum}"

    def test_prediction_metadata_correct(self, registry, sample_audio_file):
        """Test that prediction metadata is correct."""
        result = registry.predict("1", sample_audio_file, "test.wav")

        assert result["model_version"] == "1", "Model version should be '1'"
        assert result["model_type"] == "DecisionTreeClassifier", \
            "Model type should be DecisionTreeClassifier"
        assert result["feature_dimension"] == 162, \
            "Feature dimension should be 162"

    def test_multiple_predictions_are_deterministic(self, registry, sample_audio_file):
        """Test that same audio produces same prediction (deterministic)."""
        result1 = registry.predict("1", sample_audio_file, "test.wav")
        result2 = registry.predict("1", sample_audio_file, "test.wav")

        # Predictions should be identical
        assert result1["emotion"] == result2["emotion"], \
            "Same audio should produce same emotion"
        assert result1["confidence"] == result2["confidence"], \
            "Same audio should produce same confidence"

        # All probabilities should match
        for emotion in result1["all_probabilities"]:
            assert result1["all_probabilities"][emotion] == \
                   result2["all_probabilities"][emotion], \
                f"Probability for {emotion} should be identical"


@pytest.mark.integration
@pytest.mark.audio
class TestV1RealAudioInference:
    """Test inference with real CREMA-D audio files."""

    def test_real_crema_d_audio_inference(self, registry, crema_d_sample):
        """Test inference on real CREMA-D audio file."""
        audio_bytes, filename = crema_d_sample

        # Run full inference
        result = registry.predict("1", audio_bytes, filename)

        # Validate prediction structure
        assert result is not None, "Should return prediction for real audio"
        assert "emotion" in result, "Should have emotion"
        assert "confidence" in result, "Should have confidence"

        # Validate prediction values
        valid_emotions = ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        assert result["emotion"] in valid_emotions, \
            f"Emotion should be valid, got {result['emotion']}"
        assert 0.0 <= result["confidence"] <= 1.0, \
            f"Confidence should be valid, got {result['confidence']}"

    def test_real_audio_produces_valid_features_and_prediction(
        self, registry, crema_d_sample
    ):
        """Test that real audio produces valid features and prediction."""
        audio_bytes, filename = crema_d_sample

        # Step 1: Extract features
        features = extract_features(audio_bytes, filename)
        assert features.shape == (162,), "Should extract 162 features"
        assert not np.isnan(features).any(), "Features should not contain NaN"
        assert not np.isinf(features).any(), "Features should not contain inf"

        # Step 2: Run prediction
        result = registry.predict("1", audio_bytes, filename)
        assert result["emotion"] is not None, "Should predict an emotion"
        assert result["confidence"] > 0.0, "Should have non-zero confidence"

    def test_multiple_real_audio_files_all_produce_predictions(
        self, registry, crema_d_audio_path
    ):
        """Test that multiple real audio files all produce valid predictions."""
        audio_files = list(crema_d_audio_path.glob("*.wav"))[:5]  # Test first 5 files

        if len(audio_files) < 2:
            pytest.skip("Need at least 2 CREMA-D audio files")

        predictions = []

        for audio_file in audio_files:
            with open(audio_file, 'rb') as f:
                audio_bytes = f.read()

            result = registry.predict("1", audio_bytes, audio_file.name)
            predictions.append(result)

            # Each prediction should be valid
            assert result["emotion"] in ["angry", "disgust", "fear", "happy", "neutral", "sad"]
            assert 0.0 <= result["confidence"] <= 1.0
            assert sum(result["all_probabilities"].values()) >= 0.99

        # Should have predictions for all files
        assert len(predictions) == len(audio_files), \
            "Should have predictions for all audio files"


@pytest.mark.integration
class TestV1RegistryPredictIntegration:
    """Test registry.predict() method integration."""

    def test_registry_predict_handles_feature_extraction(
        self, registry, sample_audio_file
    ):
        """Test that registry.predict() internally handles feature extraction."""
        # predict() should handle feature extraction internally
        result = registry.predict("1", sample_audio_file, "test.wav")

        assert result is not None, "Should handle feature extraction internally"
        assert result["feature_dimension"] == 162, "Should use correct feature dimension"

    def test_registry_predict_validates_features(self, registry):
        """Test that registry.predict() validates feature dimensions."""
        # Create audio that might produce wrong features
        invalid_audio = b"invalid audio data"

        with pytest.raises(ValueError, match="Feature extraction failed"):
            registry.predict("1", invalid_audio, "invalid.wav")

    def test_registry_predict_with_different_filenames(
        self, registry, sample_audio_file
    ):
        """Test that prediction works with different filename extensions."""
        filenames = ["test.wav", "test.mp3", "test.m4a", "audio.WAV"]

        for filename in filenames:
            result = registry.predict("1", sample_audio_file, filename)

            assert result["emotion"] is not None, \
                f"Should work with filename {filename}"
            assert 0.0 <= result["confidence"] <= 1.0, \
                f"Should produce valid confidence for {filename}"


@pytest.mark.integration
class TestV1ErrorHandlingIntegration:
    """Test error handling through the full pipeline."""

    def test_corrupted_audio_fails_gracefully(self, registry, corrupted_audio_file):
        """Test that corrupted audio fails with appropriate error."""
        with pytest.raises(ValueError, match="Feature extraction failed"):
            registry.predict("1", corrupted_audio_file, "corrupted.wav")

    def test_empty_audio_fails_gracefully(self, registry):
        """Test that empty audio fails with appropriate error."""
        with pytest.raises(ValueError, match="Feature extraction failed"):
            registry.predict("1", b"", "empty.wav")

    def test_invalid_version_fails_gracefully(self, registry, sample_audio_file):
        """Test that invalid version request fails appropriately."""
        with pytest.raises(ValueError, match="Model version .* not found"):
            registry.predict("999", sample_audio_file, "test.wav")

    def test_none_audio_bytes_fails_gracefully(self, registry):
        """Test that None audio bytes fail appropriately."""
        with pytest.raises((ValueError, TypeError, AttributeError)):
            registry.predict("1", None, "none.wav")


@pytest.mark.integration
class TestV1PredictionConsistency:
    """Test prediction consistency and reliability."""

    def test_same_audio_consistent_across_calls(self, registry, sample_audio_file):
        """Test that same audio produces consistent results across multiple calls."""
        results = []

        for _ in range(3):
            result = registry.predict("1", sample_audio_file, "test.wav")
            results.append(result)

        # All results should be identical
        for i in range(1, len(results)):
            assert results[i]["emotion"] == results[0]["emotion"], \
                "Emotion should be consistent"
            assert results[i]["confidence"] == results[0]["confidence"], \
                "Confidence should be consistent"

            # Check all probabilities match
            for emotion in results[0]["all_probabilities"]:
                assert results[i]["all_probabilities"][emotion] == \
                       results[0]["all_probabilities"][emotion], \
                    f"Probability for {emotion} should be consistent"

    def test_different_audio_produces_predictions(self, registry):
        """Test that different audio samples all produce valid predictions."""
        # Create multiple different audio samples
        audio_samples = []

        for freq in [220, 440, 880]:  # Different frequencies
            sample_rate = 22050
            duration = 3.0
            audio_data = np.sin(2 * np.pi * freq * np.linspace(0, duration, int(sample_rate * duration)))

            audio_buffer = io.BytesIO()
            sf.write(audio_buffer, audio_data, sample_rate, format='WAV')
            audio_buffer.seek(0)
            audio_samples.append(audio_buffer.read())

        predictions = []
        for i, audio_bytes in enumerate(audio_samples):
            result = registry.predict("1", audio_bytes, f"test_{i}.wav")
            predictions.append(result)

            # Each should be valid
            assert result["emotion"] in ["angry", "disgust", "fear", "happy", "neutral", "sad"]
            assert 0.0 <= result["confidence"] <= 1.0

    def test_prediction_with_various_audio_characteristics(self, registry):
        """Test predictions with audio of various characteristics."""
        sample_rate = 22050

        # Test different durations (all > 3.1s to account for offset)
        durations = [3.5, 5.0, 10.0]

        for duration in durations:
            audio_data = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sample_rate * duration)))

            audio_buffer = io.BytesIO()
            sf.write(audio_buffer, audio_data, sample_rate, format='WAV')
            audio_buffer.seek(0)
            audio_bytes = audio_buffer.read()

            result = registry.predict("1", audio_bytes, f"test_{duration}s.wav")

            assert result["emotion"] in ["angry", "disgust", "fear", "happy", "neutral", "sad"], \
                f"Duration {duration}s should produce valid emotion"
            assert 0.0 <= result["confidence"] <= 1.0, \
                f"Duration {duration}s should produce valid confidence"


@pytest.mark.integration
class TestV1GlobalRegistryIntegration:
    """Test integration with global registry singleton."""

    def test_global_registry_predict_works(self, sample_audio_file):
        """Test that global registry predict() works correctly."""
        registry = get_registry()

        result = registry.predict("1", sample_audio_file, "test.wav")

        assert result is not None, "Global registry should work"
        assert result["emotion"] in ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        assert 0.0 <= result["confidence"] <= 1.0

    def test_global_registry_has_v1_registered(self):
        """Test that global registry has v1 model registered."""
        registry = get_registry()

        v1 = registry.get_version("1")
        assert v1 is not None, "v1 should be registered in global registry"

        info = registry.get_model_info("1")
        assert info is not None, "v1 info should be available"
        assert info["version"] == "1"
