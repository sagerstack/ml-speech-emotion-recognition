"""
Integration tests for Model v4 Full Inference Workflow.

This test suite validates the complete end-to-end inference flow for v4 model:
- Audio bytes → feature extraction → model prediction
- Full pipeline integration with ModelRegistry
- Real CREMA-D audio file processing
- Validation of complete prediction workflow
- Error handling through the entire pipeline

V4 Model Details:
- Architecture: Ultra Ensemble (Stacking + Extra Trees + Gradient Boosting + Majority Voting)
- Features: 210 (same as v3)
- Training Data: CREMA-D + RAVDESS datasets
- Identical architecture to v3 but trained on extended dataset

Focus: Application flow correctness, NOT model accuracy.
"""

import sys
import importlib.util
from pathlib import Path

# Dynamically import feature extractor to avoid path conflicts
FEATURE_EXTRACTOR_PATH = Path(__file__).resolve().parents[2] / "models" / "v4" / "feature_extractor.py"

spec = importlib.util.spec_from_file_location("v4_feature_extractor", FEATURE_EXTRACTOR_PATH)
v4_extractor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v4_extractor_module)
extract_features = v4_extractor_module.extract_features

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
class TestV4FullInferencePipeline:
    """Test complete inference pipeline from audio to prediction."""

    def test_full_pipeline_audio_to_prediction(self, registry, sample_audio_file):
        """Test complete flow: audio bytes → features → prediction."""
        # Step 1: Extract features
        features = extract_features(sample_audio_file, "test.wav")

        assert features is not None, "Feature extraction should succeed"
        assert features.shape == (210,), "Features should have correct shape"

        # Step 2: Get model
        v4_model = registry.get_version("4")
        assert v4_model is not None, "v4 model should be available"

        # Step 3: Run prediction through registry
        result = registry.predict("4", sample_audio_file, "test.wav")

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
        result = registry.predict("4", sample_audio_file, "test.wav")

        valid_emotions = ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        emotion = result["emotion"]

        assert emotion in valid_emotions, \
            f"Emotion '{emotion}' should be one of {valid_emotions}"

    def test_prediction_confidence_valid_range(self, registry, sample_audio_file):
        """Test that confidence score is in valid [0, 1] range."""
        result = registry.predict("4", sample_audio_file, "test.wav")

        confidence = result["confidence"]

        assert isinstance(confidence, (float, np.floating)), \
            "Confidence should be a float"
        assert 0.0 <= confidence <= 1.0, \
            f"Confidence {confidence} should be in range [0, 1]"

    def test_prediction_all_probabilities_valid(self, registry, sample_audio_file):
        """Test that all_probabilities dict is valid.

        Note: v4 model uses Ultra Ensemble with probability support,
        so it returns probabilities for all emotion classes.
        """
        result = registry.predict("4", sample_audio_file, "test.wav")

        all_probs = result["all_probabilities"]

        # Check it's a dictionary
        assert isinstance(all_probs, dict), "all_probabilities should be a dict"

        # v4 model should return probabilities for all classes
        assert len(all_probs) >= 1, "Should have at least one probability"

        # The predicted emotion should be in all_probabilities
        predicted_emotion = result["emotion"]
        assert predicted_emotion in all_probs, \
            f"Predicted emotion {predicted_emotion} should be in all_probabilities"

        # Check all probabilities are valid numbers
        for emotion, prob in all_probs.items():
            assert isinstance(prob, (float, np.floating)), \
                f"Probability for {emotion} should be float"
            assert 0.0 <= prob <= 1.0, \
                f"Probability for {emotion} ({prob}) should be in [0, 1]"

    def test_prediction_probabilities_sum_to_one(self, registry, sample_audio_file):
        """Test that all probabilities sum to approximately 1.0."""
        result = registry.predict("4", sample_audio_file, "test.wav")

        all_probs = result["all_probabilities"]
        prob_sum = sum(all_probs.values())

        assert 0.99 <= prob_sum <= 1.01, \
            f"Probabilities should sum to ~1.0, got {prob_sum}"

    def test_prediction_metadata_correct(self, registry, sample_audio_file):
        """Test that prediction metadata is correct."""
        result = registry.predict("4", sample_audio_file, "test.wav")

        assert result["model_version"] == "4", "Model version should be '4'"
        assert result["model_type"] == "Ultra Ensemble (Stacking + Extra Trees + Gradient Boosting + Majority Voting)", \
            "Model type should be Ultra Ensemble"
        assert result["feature_dimension"] == 210, \
            "Feature dimension should be 210"

    def test_multiple_predictions_are_deterministic(self, registry, sample_audio_file):
        """Test that same audio produces same prediction (deterministic)."""
        result1 = registry.predict("4", sample_audio_file, "test.wav")
        result2 = registry.predict("4", sample_audio_file, "test.wav")

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
class TestV4RealAudioInference:
    """Test inference with real CREMA-D audio files."""

    def test_real_crema_d_audio_inference(self, registry, crema_d_sample):
        """Test inference on real CREMA-D audio file."""
        audio_bytes, filename = crema_d_sample

        # Run full inference
        result = registry.predict("4", audio_bytes, filename)

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
        assert features.shape == (210,), "Should extract 210 features"
        assert not np.isnan(features).any(), "Features should not contain NaN"
        assert not np.isinf(features).any(), "Features should not contain inf"

        # Step 2: Run prediction
        result = registry.predict("4", audio_bytes, filename)
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

            result = registry.predict("4", audio_bytes, audio_file.name)
            predictions.append(result)

            # Each prediction should be valid
            assert result["emotion"] in ["angry", "disgust", "fear", "happy", "neutral", "sad"]
            assert 0.0 <= result["confidence"] <= 1.0
            assert sum(result["all_probabilities"].values()) >= 0.99

        # Should have predictions for all files
        assert len(predictions) == len(audio_files), \
            "Should have predictions for all audio files"


@pytest.mark.integration
class TestV4RegistryPredictIntegration:
    """Test registry.predict() method integration."""

    def test_registry_predict_handles_feature_extraction(
        self, registry, sample_audio_file
    ):
        """Test that registry.predict() internally handles feature extraction."""
        # predict() should handle feature extraction internally
        result = registry.predict("4", sample_audio_file, "test.wav")

        assert result is not None, "Should handle feature extraction internally"
        assert result["feature_dimension"] == 210, "Should use correct feature dimension"

    def test_registry_predict_validates_features(self, registry):
        """Test that registry.predict() validates feature dimensions."""
        # Create audio that might produce wrong features
        invalid_audio = b"invalid audio data"

        with pytest.raises(ValueError, match="Feature extraction failed"):
            registry.predict("4", invalid_audio, "invalid.wav")

    def test_registry_predict_with_different_filenames(
        self, registry, sample_audio_file
    ):
        """Test that prediction works with different filename extensions."""
        filenames = ["test.wav", "test.mp3", "test.m4a", "audio.WAV"]

        for filename in filenames:
            result = registry.predict("4", sample_audio_file, filename)

            assert result["emotion"] is not None, \
                f"Should work with filename {filename}"
            assert 0.0 <= result["confidence"] <= 1.0, \
                f"Should produce valid confidence for {filename}"


@pytest.mark.integration
class TestV4ErrorHandlingIntegration:
    """Test error handling through the full pipeline."""

    def test_corrupted_audio_fails_gracefully(self, registry, corrupted_audio_file):
        """Test that corrupted audio fails with appropriate error."""
        with pytest.raises(ValueError, match="Feature extraction failed"):
            registry.predict("4", corrupted_audio_file, "corrupted.wav")

    def test_empty_audio_fails_gracefully(self, registry):
        """Test that empty audio fails with appropriate error."""
        with pytest.raises(ValueError, match="Feature extraction failed"):
            registry.predict("4", b"", "empty.wav")

    def test_invalid_version_fails_gracefully(self, registry, sample_audio_file):
        """Test that invalid version request fails appropriately."""
        with pytest.raises(ValueError, match="Model version .* not found"):
            registry.predict("999", sample_audio_file, "test.wav")

    def test_none_audio_bytes_fails_gracefully(self, registry):
        """Test that None audio bytes fail appropriately."""
        with pytest.raises((ValueError, TypeError, AttributeError)):
            registry.predict("4", None, "none.wav")


@pytest.mark.integration
class TestV4PredictionConsistency:
    """Test prediction consistency and reliability."""

    def test_same_audio_consistent_across_calls(self, registry, sample_audio_file):
        """Test that same audio produces consistent results across multiple calls."""
        results = []

        for _ in range(3):
            result = registry.predict("4", sample_audio_file, "test.wav")
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
            result = registry.predict("4", audio_bytes, f"test_{i}.wav")
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

            result = registry.predict("4", audio_bytes, f"test_{duration}s.wav")

            assert result["emotion"] in ["angry", "disgust", "fear", "happy", "neutral", "sad"], \
                f"Duration {duration}s should produce valid emotion"
            assert 0.0 <= result["confidence"] <= 1.0, \
                f"Duration {duration}s should produce valid confidence"


@pytest.mark.integration
class TestV4GlobalRegistryIntegration:
    """Test integration with global registry singleton."""

    def test_global_registry_predict_works(self, sample_audio_file):
        """Test that global registry predict() works correctly."""
        registry = get_registry()

        result = registry.predict("4", sample_audio_file, "test.wav")

        assert result is not None, "Global registry should work"
        assert result["emotion"] in ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        assert 0.0 <= result["confidence"] <= 1.0

    def test_global_registry_has_v4_registered(self):
        """Test that global registry has v4 model registered."""
        registry = get_registry()

        v4 = registry.get_version("4")
        assert v4 is not None, "v4 should be registered in global registry"

        info = registry.get_model_info("4")
        assert info is not None, "v4 info should be available"
        assert info["version"] == "4"


@pytest.mark.integration
class TestV4VsOtherVersionsComparison:
    """Test comparisons between v4 and other model versions."""

    def test_v4_v3_v2_and_v1_all_work_on_same_audio(self, registry, sample_audio_file):
        """Test that v1, v2, v3, and v4 all work on the same audio file."""
        v1_result = registry.predict("1", sample_audio_file, "test.wav")
        v2_result = registry.predict("2", sample_audio_file, "test.wav")
        v3_result = registry.predict("3", sample_audio_file, "test.wav")
        v4_result = registry.predict("4", sample_audio_file, "test.wav")

        # All should produce valid predictions
        valid_emotions = ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        assert v1_result["emotion"] in valid_emotions, "v1 should predict valid emotion"
        assert v2_result["emotion"] in valid_emotions, "v2 should predict valid emotion"
        assert v3_result["emotion"] in valid_emotions, "v3 should predict valid emotion"
        assert v4_result["emotion"] in valid_emotions, "v4 should predict valid emotion"

    def test_v4_uses_same_features_as_v3_but_different_than_v1_and_v2(self, registry, sample_audio_file):
        """Test that v4 uses same features as v3, but different from v1 and v2."""
        v1_result = registry.predict("1", sample_audio_file, "test.wav")
        v2_result = registry.predict("2", sample_audio_file, "test.wav")
        v3_result = registry.predict("3", sample_audio_file, "test.wav")
        v4_result = registry.predict("4", sample_audio_file, "test.wav")

        # Different feature dimensions
        assert v1_result["feature_dimension"] == 162, "v1 should use 162 features"
        assert v2_result["feature_dimension"] == 78, "v2 should use 78 features"
        assert v3_result["feature_dimension"] == 210, "v3 should use 210 features"
        assert v4_result["feature_dimension"] == 210, "v4 should use 210 features (same as v3)"

    def test_v4_has_same_architecture_as_v3(self, registry):
        """Test that v4 has same architecture as v3 (Ultra Ensemble)."""
        v3_info = registry.get_model_info("3")
        v4_info = registry.get_model_info("4")

        # v3 and v4 should have identical architecture
        assert v3_info["model_type"] == v4_info["model_type"], \
            "v3 and v4 should have same model type"
        assert v4_info["model_type"] == "Ultra Ensemble (Stacking + Extra Trees + Gradient Boosting + Majority Voting)"

    def test_v4_has_different_model_architecture_than_v1_and_v2(self, registry):
        """Test that v4 has different architecture than v1 and v2."""
        v1_info = registry.get_model_info("1")
        v2_info = registry.get_model_info("2")
        v4_info = registry.get_model_info("4")

        assert v1_info["model_type"] != v4_info["model_type"], \
            "v1 and v4 should have different model types"
        assert v2_info["model_type"] != v4_info["model_type"], \
            "v2 and v4 should have different model types"
        assert v1_info["model_type"] == "DecisionTreeClassifier"
        assert v2_info["model_type"] == "Pipeline (StandardScaler + RFE + SVC)"
        assert v4_info["model_type"] == "Ultra Ensemble (Stacking + Extra Trees + Gradient Boosting + Majority Voting)"

    def test_v4_and_v3_produce_most_features(self, registry, sample_audio_file):
        """Test that v4 and v3 produce the most features among all versions."""
        v1_result = registry.predict("1", sample_audio_file, "test.wav")
        v2_result = registry.predict("2", sample_audio_file, "test.wav")
        v3_result = registry.predict("3", sample_audio_file, "test.wav")
        v4_result = registry.predict("4", sample_audio_file, "test.wav")

        v1_features = v1_result["feature_dimension"]
        v2_features = v2_result["feature_dimension"]
        v3_features = v3_result["feature_dimension"]
        v4_features = v4_result["feature_dimension"]

        # v4 should have the same features as v3
        assert v4_features == 210, "v4 should have 210 features"
        assert v3_features == 210, "v3 should have 210 features"
        assert v4_features == v3_features, "v4 and v3 should have same feature count"

        # v4 should have more features than v1 and v2
        assert v4_features > v1_features, "v4 should have more features than v1"
        assert v4_features > v2_features, "v4 should have more features than v2"

    def test_v4_trained_on_extended_dataset(self, registry):
        """Test that v4 metadata indicates training on CREMA-D + RAVDESS."""
        v3_info = registry.get_model_info("3")
        v4_info = registry.get_model_info("4")

        # Check that dataset information is available and correct
        assert "dataset" in v4_info, "v4 should have dataset information"
        assert v4_info["dataset"] == "CREMA-D + RAVDESS", \
            "v4 should be trained on CREMA-D + RAVDESS"

        # v3 should only be trained on CREMA-D
        assert "dataset" in v3_info, "v3 should have dataset information"
        assert v3_info["dataset"] == "CREMA-D", \
            "v3 should be trained on CREMA-D only"

    def test_v4_predictions_may_differ_from_v3_despite_same_architecture(
        self, registry, sample_audio_file
    ):
        """Test that v4 and v3 may produce different predictions due to different training data."""
        v3_result = registry.predict("3", sample_audio_file, "test.wav")
        v4_result = registry.predict("4", sample_audio_file, "test.wav")

        # Both should produce valid predictions
        valid_emotions = ["angry", "disgust", "fear", "happy", "neutral", "sad"]
        assert v3_result["emotion"] in valid_emotions
        assert v4_result["emotion"] in valid_emotions

        # Predictions MAY differ (or may be same) - both are valid outcomes
        # This test just ensures both models work independently
        # No assertion about whether predictions match or differ
        # because it depends on the specific audio sample

        # However, both should have valid confidence scores
        assert 0.0 <= v3_result["confidence"] <= 1.0
        assert 0.0 <= v4_result["confidence"] <= 1.0
