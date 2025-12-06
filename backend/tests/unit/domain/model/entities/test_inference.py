"""Tests for Inference entity."""

import pytest

from app.domain.model.entities.inference import Inference
from app.domain.model.value_objects.confidence import Confidence
from app.domain.model.value_objects.emotion import Emotion
from app.domain.model.value_objects.model_version import ModelVersion


class TestInferenceCreation:
    """Test Inference entity creation and validation."""

    def test_create_valid_inference(self):
        """Test creating a valid Inference instance."""
        emotion = Emotion.HAPPY
        confidence = Confidence.from_probability(0.85)
        all_probabilities = {
            Emotion.ANGRY: 0.02,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.05,
            Emotion.HAPPY: 0.85,
            Emotion.NEUTRAL: 0.03,
            Emotion.SAD: 0.02,
        }
        model_version = ModelVersion.from_string("v4")
        processing_time_ms = 123.45

        inference = Inference(
            emotion=emotion,
            confidence=confidence,
            all_probabilities=all_probabilities,
            model_version=model_version,
            processing_time_ms=processing_time_ms,
        )

        assert inference.emotion == emotion
        assert inference.confidence == confidence
        assert inference.all_probabilities == all_probabilities
        assert inference.model_version == model_version
        assert inference.processing_time_ms == processing_time_ms

    def test_create_factory_method(self):
        """Test creating Inference using create factory method."""
        emotion = Emotion.SAD
        all_probabilities = {
            Emotion.ANGRY: 0.05,
            Emotion.DISGUST: 0.05,
            Emotion.FEAR: 0.10,
            Emotion.HAPPY: 0.05,
            Emotion.NEUTRAL: 0.10,
            Emotion.SAD: 0.65,
        }
        model_version = ModelVersion.from_string("v4")
        processing_time_ms = 150.0

        inference = Inference.create(
            emotion=emotion,
            all_probabilities=all_probabilities,
            model_version=model_version,
            processing_time_ms=processing_time_ms,
        )

        assert inference.emotion == emotion
        assert inference.confidence.value == 0.65
        assert inference.all_probabilities == all_probabilities
        assert inference.model_version == model_version
        assert inference.processing_time_ms == processing_time_ms

    def test_invalid_emotion_type_raises_error(self):
        """Test that non-Emotion type raises ValueError."""
        with pytest.raises(ValueError, match="emotion must be Emotion instance"):
            Inference(
                emotion="happy",  # Should be Emotion enum
                confidence=Confidence.from_probability(0.85),
                all_probabilities={
                    Emotion.ANGRY: 0.02,
                    Emotion.DISGUST: 0.03,
                    Emotion.FEAR: 0.05,
                    Emotion.HAPPY: 0.85,
                    Emotion.NEUTRAL: 0.03,
                    Emotion.SAD: 0.02,
                },
                model_version=ModelVersion.from_string("v4"),
                processing_time_ms=100.0,
            )

    def test_invalid_confidence_type_raises_error(self):
        """Test that non-Confidence type raises ValueError."""
        with pytest.raises(ValueError, match="confidence must be Confidence instance"):
            Inference(
                emotion=Emotion.HAPPY,
                confidence=0.85,  # Should be Confidence object
                all_probabilities={
                    Emotion.ANGRY: 0.02,
                    Emotion.DISGUST: 0.03,
                    Emotion.FEAR: 0.05,
                    Emotion.HAPPY: 0.85,
                    Emotion.NEUTRAL: 0.03,
                    Emotion.SAD: 0.02,
                },
                model_version=ModelVersion.from_string("v4"),
                processing_time_ms=100.0,
            )

    def test_invalid_model_version_type_raises_error(self):
        """Test that non-ModelVersion type raises ValueError."""
        with pytest.raises(ValueError, match="model_version must be ModelVersion instance"):
            Inference(
                emotion=Emotion.HAPPY,
                confidence=Confidence.from_probability(0.85),
                all_probabilities={
                    Emotion.ANGRY: 0.02,
                    Emotion.DISGUST: 0.03,
                    Emotion.FEAR: 0.05,
                    Emotion.HAPPY: 0.85,
                    Emotion.NEUTRAL: 0.03,
                    Emotion.SAD: 0.02,
                },
                model_version="v4",  # Should be ModelVersion object
                processing_time_ms=100.0,
            )

    def test_negative_processing_time_raises_error(self):
        """Test that negative processing time raises ValueError."""
        with pytest.raises(ValueError, match="processing_time_ms cannot be negative"):
            Inference(
                emotion=Emotion.HAPPY,
                confidence=Confidence.from_probability(0.85),
                all_probabilities={
                    Emotion.ANGRY: 0.02,
                    Emotion.DISGUST: 0.03,
                    Emotion.FEAR: 0.05,
                    Emotion.HAPPY: 0.85,
                    Emotion.NEUTRAL: 0.03,
                    Emotion.SAD: 0.02,
                },
                model_version=ModelVersion.from_string("v4"),
                processing_time_ms=-10.0,
            )

    def test_invalid_processing_time_type_raises_error(self):
        """Test that non-numeric processing time raises ValueError."""
        with pytest.raises(ValueError, match="processing_time_ms must be a number"):
            Inference(
                emotion=Emotion.HAPPY,
                confidence=Confidence.from_probability(0.85),
                all_probabilities={
                    Emotion.ANGRY: 0.02,
                    Emotion.DISGUST: 0.03,
                    Emotion.FEAR: 0.05,
                    Emotion.HAPPY: 0.85,
                    Emotion.NEUTRAL: 0.03,
                    Emotion.SAD: 0.02,
                },
                model_version=ModelVersion.from_string("v4"),
                processing_time_ms="fast",
            )


class TestInferenceProbabilityValidation:
    """Test Inference probability validation."""

    def test_invalid_all_probabilities_type_raises_error(self):
        """Test that non-dict all_probabilities raises ValueError."""
        with pytest.raises(ValueError, match="all_probabilities must be a dict"):
            Inference(
                emotion=Emotion.HAPPY,
                confidence=Confidence.from_probability(0.85),
                all_probabilities=[0.85, 0.05, 0.05, 0.02, 0.02, 0.01],
                model_version=ModelVersion.from_string("v4"),
                processing_time_ms=100.0,
            )

    def test_missing_emotion_in_probabilities_raises_error(self):
        """Test that missing emotions in all_probabilities raises ValueError."""
        with pytest.raises(ValueError, match="missing emotions"):
            Inference(
                emotion=Emotion.HAPPY,
                confidence=Confidence.from_probability(0.85),
                all_probabilities={
                    Emotion.ANGRY: 0.05,
                    Emotion.HAPPY: 0.85,
                    Emotion.SAD: 0.10,
                    # Missing DISGUST, FEAR, NEUTRAL
                },
                model_version=ModelVersion.from_string("v4"),
                processing_time_ms=100.0,
            )

    def test_probabilities_not_summing_to_one_raises_error(self):
        """Test that probabilities not summing to 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="all_probabilities must sum to 1.0"):
            Inference(
                emotion=Emotion.HAPPY,
                confidence=Confidence.from_probability(0.85),
                all_probabilities={
                    Emotion.ANGRY: 0.02,
                    Emotion.DISGUST: 0.03,
                    Emotion.FEAR: 0.05,
                    Emotion.HAPPY: 0.85,
                    Emotion.NEUTRAL: 0.03,
                    Emotion.SAD: 0.05,  # Sum is 1.03, not 1.0
                },
                model_version=ModelVersion.from_string("v4"),
                processing_time_ms=100.0,
            )

    def test_invalid_probability_value_negative_raises_error(self):
        """Test that negative probability raises ValueError."""
        with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
            Inference(
                emotion=Emotion.HAPPY,
                confidence=Confidence.from_probability(0.85),
                all_probabilities={
                    Emotion.ANGRY: 0.02,
                    Emotion.DISGUST: 0.03,
                    Emotion.FEAR: 0.05,
                    Emotion.HAPPY: 0.85,
                    Emotion.NEUTRAL: -0.10,  # Invalid: < 0.0
                    Emotion.SAD: 0.15,
                },
                model_version=ModelVersion.from_string("v4"),
                processing_time_ms=100.0,
            )

    def test_predicted_emotion_not_highest_probability_raises_error(self):
        """Test that predicted emotion must have highest probability."""
        with pytest.raises(ValueError, match="does not have highest probability"):
            Inference(
                emotion=Emotion.HAPPY,  # Predicted emotion
                confidence=Confidence.from_probability(0.30),
                all_probabilities={
                    Emotion.ANGRY: 0.02,
                    Emotion.DISGUST: 0.03,
                    Emotion.FEAR: 0.05,
                    Emotion.HAPPY: 0.30,
                    Emotion.NEUTRAL: 0.05,
                    Emotion.SAD: 0.55,  # SAD has highest probability, not HAPPY
                },
                model_version=ModelVersion.from_string("v4"),
                processing_time_ms=100.0,
            )

    def test_confidence_mismatch_with_probability_raises_error(self):
        """Test that confidence must match predicted emotion probability."""
        with pytest.raises(ValueError, match="Confidence.*does not match"):
            Inference(
                emotion=Emotion.HAPPY,
                confidence=Confidence.from_probability(0.90),  # Wrong confidence
                all_probabilities={
                    Emotion.ANGRY: 0.02,
                    Emotion.DISGUST: 0.03,
                    Emotion.FEAR: 0.05,
                    Emotion.HAPPY: 0.85,  # Actual probability
                    Emotion.NEUTRAL: 0.03,
                    Emotion.SAD: 0.02,
                },
                model_version=ModelVersion.from_string("v4"),
                processing_time_ms=100.0,
            )

    def test_create_factory_missing_emotion_probability_raises_error(self):
        """Test that create factory method validates emotion is in probabilities."""
        with pytest.raises(ValueError, match="Probability for predicted emotion.*not found"):
            Inference.create(
                emotion=Emotion.HAPPY,
                all_probabilities={
                    Emotion.ANGRY: 0.20,
                    Emotion.DISGUST: 0.20,
                    Emotion.FEAR: 0.20,
                    Emotion.NEUTRAL: 0.20,
                    Emotion.SAD: 0.20,
                    # Missing HAPPY
                },
                model_version=ModelVersion.from_string("v4"),
                processing_time_ms=100.0,
            )


class TestInferenceTopEmotions:
    """Test Inference top emotions functionality."""

    def test_get_top_n_emotions_default(self):
        """Test getting top 3 emotions by default."""
        all_probabilities = {
            Emotion.ANGRY: 0.05,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.10,
            Emotion.HAPPY: 0.65,
            Emotion.NEUTRAL: 0.15,
            Emotion.SAD: 0.02,
        }

        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=100.0,
        )

        top_3 = inference.get_top_n_emotions()

        assert len(top_3) == 3
        assert top_3[0] == (Emotion.HAPPY, 0.65)
        assert top_3[1] == (Emotion.NEUTRAL, 0.15)
        assert top_3[2] == (Emotion.FEAR, 0.10)

    def test_get_top_n_emotions_custom_n(self):
        """Test getting custom number of top emotions."""
        all_probabilities = {
            Emotion.ANGRY: 0.05,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.10,
            Emotion.HAPPY: 0.65,
            Emotion.NEUTRAL: 0.15,
            Emotion.SAD: 0.02,
        }

        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=100.0,
        )

        top_2 = inference.get_top_n_emotions(n=2)

        assert len(top_2) == 2
        assert top_2[0] == (Emotion.HAPPY, 0.65)
        assert top_2[1] == (Emotion.NEUTRAL, 0.15)

    def test_get_top_n_emotions_all(self):
        """Test getting all emotions."""
        all_probabilities = {
            Emotion.ANGRY: 0.05,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.10,
            Emotion.HAPPY: 0.65,
            Emotion.NEUTRAL: 0.15,
            Emotion.SAD: 0.02,
        }

        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=100.0,
        )

        all_emotions = inference.get_top_n_emotions(n=6)

        assert len(all_emotions) == 6

    def test_get_top_n_emotions_invalid_n_raises_error(self):
        """Test that invalid n raises ValueError."""
        all_probabilities = {
            Emotion.ANGRY: 0.05,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.10,
            Emotion.HAPPY: 0.65,
            Emotion.NEUTRAL: 0.15,
            Emotion.SAD: 0.02,
        }

        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=100.0,
        )

        with pytest.raises(ValueError, match="n must be positive"):
            inference.get_top_n_emotions(n=0)

        with pytest.raises(ValueError, match="n must be positive"):
            inference.get_top_n_emotions(n=-1)


class TestInferenceAmbiguity:
    """Test Inference ambiguity detection."""

    def test_is_ambiguous_with_close_probabilities(self):
        """Test that close top probabilities are detected as ambiguous."""
        all_probabilities = {
            Emotion.ANGRY: 0.02,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.08,
            Emotion.HAPPY: 0.47,  # Top
            Emotion.NEUTRAL: 0.38,  # Close second (difference = 0.09)
            Emotion.SAD: 0.02,
        }

        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=100.0,
        )

        # Default threshold is 0.2, difference is 0.05, so it's ambiguous
        assert inference.is_ambiguous() is True

    def test_is_ambiguous_with_clear_winner(self):
        """Test that clear winner is not ambiguous."""
        all_probabilities = {
            Emotion.ANGRY: 0.02,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.05,
            Emotion.HAPPY: 0.80,  # Clear winner
            Emotion.NEUTRAL: 0.08,
            Emotion.SAD: 0.02,
        }

        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=100.0,
        )

        assert inference.is_ambiguous() is False

    def test_is_ambiguous_custom_threshold(self):
        """Test ambiguity detection with custom threshold."""
        all_probabilities = {
            Emotion.ANGRY: 0.02,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.10,
            Emotion.HAPPY: 0.60,
            Emotion.NEUTRAL: 0.50,  # Difference = 0.10
            Emotion.SAD: 0.02,
        }

        # Normalize to sum to 1.0
        all_probabilities = {
            Emotion.ANGRY: 0.02,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.05,
            Emotion.HAPPY: 0.50,
            Emotion.NEUTRAL: 0.38,  # Difference = 0.12
            Emotion.SAD: 0.02,
        }

        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=100.0,
        )

        # With threshold 0.15, difference of 0.12 is ambiguous
        assert inference.is_ambiguous(threshold=0.15) is True

        # With threshold 0.10, difference of 0.12 is not ambiguous
        assert inference.is_ambiguous(threshold=0.10) is False


class TestInferenceStringRepresentation:
    """Test Inference string representation."""

    def test_str_representation(self):
        """Test string representation includes key information."""
        all_probabilities = {
            Emotion.ANGRY: 0.02,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.05,
            Emotion.HAPPY: 0.85,
            Emotion.NEUTRAL: 0.03,
            Emotion.SAD: 0.02,
        }

        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=123.45,
        )

        str_repr = str(inference)

        assert "Inference" in str_repr
        assert "happy" in str_repr
        assert "v4" in str_repr
        assert "123.45" in str_repr


class TestInferenceWithAudioFeatures:
    """Test Inference with audio_features data."""

    def test_create_with_none_audio_features(self):
        """Test creating Inference without audio_features."""
        all_probabilities = {
            Emotion.ANGRY: 0.02,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.05,
            Emotion.HAPPY: 0.85,
            Emotion.NEUTRAL: 0.03,
            Emotion.SAD: 0.02,
        }

        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=123.45,
            audio_features=None,
        )

        assert inference.audio_features is None

    def test_create_with_audio_features(self):
        """Test creating Inference with audio_features data."""
        all_probabilities = {
            Emotion.ANGRY: 0.02,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.05,
            Emotion.HAPPY: 0.85,
            Emotion.NEUTRAL: 0.03,
            Emotion.SAD: 0.02,
        }

        audio_features = {
            "sample_rate": 22050,
            "duration": 2.5,
            "waveform": [0.1, 0.2, 0.3],
            "mel_spectrogram": [[0.1] * 10] * 128,
            "chroma": [[0.2] * 10] * 12,
            "mfcc": [[0.3] * 10] * 20,
        }

        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=123.45,
            audio_features=audio_features,
        )

        assert inference.audio_features is not None
        assert inference.audio_features == audio_features
        assert inference.audio_features["sample_rate"] == 22050
        assert inference.audio_features["duration"] == 2.5

    def test_create_with_empty_audio_features_dict(self):
        """Test creating Inference with empty audio_features dict."""
        all_probabilities = {
            Emotion.ANGRY: 0.02,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.05,
            Emotion.HAPPY: 0.85,
            Emotion.NEUTRAL: 0.03,
            Emotion.SAD: 0.02,
        }

        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=123.45,
            audio_features={},
        )

        assert inference.audio_features is not None
        assert inference.audio_features == {}

    def test_default_audio_features_is_none(self):
        """Test that audio_features defaults to None when not provided."""
        all_probabilities = {
            Emotion.ANGRY: 0.02,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.05,
            Emotion.HAPPY: 0.85,
            Emotion.NEUTRAL: 0.03,
            Emotion.SAD: 0.02,
        }

        # Not providing audio_features parameter
        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=123.45,
        )

        assert inference.audio_features is None


class TestInferenceWithPredictionId:
    """Test Inference with prediction_id for monitoring."""

    def test_create_with_none_prediction_id(self):
        """Test creating Inference without prediction_id."""
        all_probabilities = {
            Emotion.ANGRY: 0.02,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.05,
            Emotion.HAPPY: 0.85,
            Emotion.NEUTRAL: 0.03,
            Emotion.SAD: 0.02,
        }

        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=123.45,
            prediction_id=None,
        )

        assert inference.prediction_id is None

    def test_create_with_prediction_id(self):
        """Test creating Inference with prediction_id."""
        all_probabilities = {
            Emotion.ANGRY: 0.02,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.05,
            Emotion.HAPPY: 0.85,
            Emotion.NEUTRAL: 0.03,
            Emotion.SAD: 0.02,
        }

        prediction_id = "123e4567-e89b-12d3-a456-426614174000"

        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=123.45,
            prediction_id=prediction_id,
        )

        assert inference.prediction_id is not None
        assert inference.prediction_id == prediction_id

    def test_default_prediction_id_is_none(self):
        """Test that prediction_id defaults to None when not provided."""
        all_probabilities = {
            Emotion.ANGRY: 0.02,
            Emotion.DISGUST: 0.03,
            Emotion.FEAR: 0.05,
            Emotion.HAPPY: 0.85,
            Emotion.NEUTRAL: 0.03,
            Emotion.SAD: 0.02,
        }

        # Not providing prediction_id parameter
        inference = Inference.create(
            emotion=Emotion.HAPPY,
            all_probabilities=all_probabilities,
            model_version=ModelVersion.from_string("v4"),
            processing_time_ms=123.45,
        )

        assert inference.prediction_id is None
