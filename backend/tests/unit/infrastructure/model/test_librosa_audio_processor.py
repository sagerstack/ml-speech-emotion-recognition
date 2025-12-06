"""Unit tests for LibrosaAudioProcessor."""

import io

import numpy as np
import pytest
import soundfile as sf

from app.domain.model.entities.raw_audio import RawAudio
from app.domain.model.exceptions.invalid_audio_error import InvalidAudioError
from app.infrastructure.model.librosa_audio_processor import LibrosaAudioProcessor


class TestLibrosaAudioProcessor:
    """Test suite for LibrosaAudioProcessor."""

    @pytest.fixture
    def processor(self) -> LibrosaAudioProcessor:
        """Create LibrosaAudioProcessor instance."""
        return LibrosaAudioProcessor()

    @pytest.fixture
    def valid_audio_bytes(self) -> bytes:
        """Create valid audio bytes for testing."""
        # Generate a simple sine wave
        sample_rate = 22050
        duration = 2.5
        frequency = 440
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t)

        # Normalize
        audio_data = audio_data / np.max(np.abs(audio_data)) * 0.8

        # Convert to bytes
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, sample_rate, format="WAV")
        audio_buffer.seek(0)
        return audio_buffer.read()

    @pytest.fixture
    def valid_raw_audio(self, valid_audio_bytes: bytes) -> RawAudio:
        """Create valid RawAudio instance."""
        return RawAudio.from_bytes(valid_audio_bytes, "test_audio.wav")

    # Test extract_features
    def test_extract_features_returns_correct_shape(
        self, processor: LibrosaAudioProcessor, valid_raw_audio: RawAudio
    ):
        """Test that extract_features returns 210 features for v4 model."""
        features = processor.extract_features(valid_raw_audio)

        assert isinstance(features, np.ndarray)
        assert features.shape == (210,), f"Expected (210,), got {features.shape}"

    def test_extract_features_returns_valid_values(
        self, processor: LibrosaAudioProcessor, valid_raw_audio: RawAudio
    ):
        """Test that extracted features contain valid numerical values."""
        features = processor.extract_features(valid_raw_audio)

        # Check for no NaN values
        assert not np.any(np.isnan(features)), "Features contain NaN values"

        # Check for no infinite values
        assert not np.any(np.isinf(features)), "Features contain infinite values"

        # Check that features are numerical
        assert np.issubdtype(features.dtype, np.number), "Features are not numerical"

    def test_extract_features_with_empty_audio_raises_error(self, processor: LibrosaAudioProcessor):
        """Test that empty audio raises InvalidAudioError."""
        with pytest.raises(InvalidAudioError):
            empty_audio = RawAudio.from_bytes(b"", "empty.wav")
            processor.extract_features(empty_audio)

    def test_extract_features_with_corrupted_audio_raises_error(
        self, processor: LibrosaAudioProcessor
    ):
        """Test that corrupted audio raises InvalidAudioError."""
        corrupted_audio = RawAudio.from_bytes(b"not an audio file", "corrupted.wav")

        with pytest.raises(InvalidAudioError):
            processor.extract_features(corrupted_audio)

    def test_extract_features_is_deterministic(
        self, processor: LibrosaAudioProcessor, valid_raw_audio: RawAudio
    ):
        """Test that feature extraction is deterministic for same audio."""
        features1 = processor.extract_features(valid_raw_audio)
        features2 = processor.extract_features(valid_raw_audio)

        np.testing.assert_array_almost_equal(
            features1, features2, decimal=6, err_msg="Feature extraction is not deterministic"
        )

    # Test get_audio_metadata
    def test_get_audio_metadata_returns_correct_metadata(
        self, processor: LibrosaAudioProcessor, valid_raw_audio: RawAudio
    ):
        """Test that get_audio_metadata returns correct metadata."""
        metadata = processor.get_audio_metadata(valid_raw_audio)

        assert metadata.sample_rate > 0
        assert metadata.duration_seconds > 0
        assert metadata.channels > 0

    def test_get_audio_metadata_for_2_5_second_audio(
        self, processor: LibrosaAudioProcessor, valid_raw_audio: RawAudio
    ):
        """Test metadata for audio with known duration."""
        metadata = processor.get_audio_metadata(valid_raw_audio)

        # Audio should be close to 2.5 seconds (after trimming)
        assert (
            1.0 <= metadata.duration_seconds <= 3.0
        ), f"Expected duration around 2.5s, got {metadata.duration_seconds}s"

    def test_get_audio_metadata_with_invalid_audio_raises_error(
        self, processor: LibrosaAudioProcessor
    ):
        """Test that invalid audio raises InvalidAudioError."""
        invalid_audio = RawAudio.from_bytes(b"invalid audio data", "invalid.wav")

        with pytest.raises(InvalidAudioError):
            processor.get_audio_metadata(invalid_audio)

    # Test validate_audio
    def test_validate_audio_accepts_valid_audio(
        self, processor: LibrosaAudioProcessor, valid_raw_audio: RawAudio
    ):
        """Test that valid audio passes validation."""
        result = processor.validate_audio(valid_raw_audio)
        assert result is True

    def test_validate_audio_rejects_corrupted_audio(self, processor: LibrosaAudioProcessor):
        """Test that corrupted audio fails validation."""
        corrupted_audio = RawAudio.from_bytes(b"corrupted", "corrupted.wav")

        with pytest.raises(InvalidAudioError):
            processor.validate_audio(corrupted_audio)

    def test_validate_audio_rejects_empty_audio(self, processor: LibrosaAudioProcessor):
        """Test that empty audio fails validation."""
        with pytest.raises(InvalidAudioError):
            empty_audio = RawAudio.from_bytes(b"", "empty.wav")
            processor.validate_audio(empty_audio)

    def test_validate_audio_rejects_too_short_audio(self, processor: LibrosaAudioProcessor):
        """Test that very short audio fails validation."""
        # Create very short audio (< 0.5 seconds)
        sample_rate = 22050
        duration = 0.1  # Very short
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * 440 * t)

        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, sample_rate, format="WAV")
        audio_buffer.seek(0)
        short_audio = RawAudio.from_bytes(audio_buffer.read(), "short.wav")

        with pytest.raises(InvalidAudioError):
            processor.validate_audio(short_audio)

    # Integration tests
    def test_full_processing_pipeline(
        self, processor: LibrosaAudioProcessor, valid_raw_audio: RawAudio
    ):
        """Test the complete processing pipeline."""
        # Validate
        is_valid = processor.validate_audio(valid_raw_audio)
        assert is_valid is True

        # Get metadata
        metadata = processor.get_audio_metadata(valid_raw_audio)
        assert metadata.duration_seconds > 0

        # Extract features
        features = processor.extract_features(valid_raw_audio)
        assert features.shape == (210,)
        assert not np.any(np.isnan(features))

    def test_processor_handles_different_audio_formats(self, processor: LibrosaAudioProcessor):
        """Test that processor handles different audio formats."""
        # WAV format
        sample_rate = 22050
        duration = 2.5
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * 440 * t)

        # Test WAV
        wav_buffer = io.BytesIO()
        sf.write(wav_buffer, audio_data, sample_rate, format="WAV")
        wav_buffer.seek(0)
        wav_audio = RawAudio.from_bytes(wav_buffer.read(), "test.wav")

        features_wav = processor.extract_features(wav_audio)
        assert features_wav.shape == (210,)

    def test_extract_features_handles_different_sample_rates(
        self, processor: LibrosaAudioProcessor
    ):
        """Test that processor handles different sample rates."""
        # Test with 16kHz audio
        sample_rate = 16000
        duration = 2.5
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * 440 * t)

        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, sample_rate, format="WAV")
        audio_buffer.seek(0)
        audio_16k = RawAudio.from_bytes(audio_buffer.read(), "test_16k.wav")

        features = processor.extract_features(audio_16k)
        assert features.shape == (210,)
        assert not np.any(np.isnan(features))

    # Test extract_features_with_audio_data
    def test_extract_features_with_audio_data_returns_correct_structure(
        self, processor: LibrosaAudioProcessor, valid_raw_audio: RawAudio
    ):
        """Test that extract_features_with_audio_data returns correct structure."""
        result = processor.extract_features_with_audio_data(valid_raw_audio)

        # Check result is dict with correct keys
        assert isinstance(result, dict)
        assert "features" in result
        assert "audio_features" in result

        # Check features shape
        features = result["features"]
        assert isinstance(features, np.ndarray)
        assert features.shape == (210,), f"Expected (210,), got {features.shape}"

        # Check audio_features structure
        audio_features = result["audio_features"]
        assert isinstance(audio_features, dict)
        assert "sample_rate" in audio_features
        assert "duration" in audio_features
        assert "waveform" in audio_features
        assert "mel_spectrogram" in audio_features
        assert "chroma" in audio_features
        assert "mfcc" in audio_features
        assert "delta_mfcc" in audio_features
        assert "delta_delta_mfcc" in audio_features
        assert "pitch_times" in audio_features
        assert "pitch_values" in audio_features
        assert "rms_contour" in audio_features

    def test_extract_features_with_audio_data_features_match_extract_features(
        self, processor: LibrosaAudioProcessor, valid_raw_audio: RawAudio
    ):
        """Test that features from extract_features_with_audio_data match extract_features."""
        features_only = processor.extract_features(valid_raw_audio)
        result = processor.extract_features_with_audio_data(valid_raw_audio)
        features_with_viz = result["features"]

        # Features should be identical
        np.testing.assert_array_almost_equal(
            features_only,
            features_with_viz,
            decimal=6,
            err_msg="Features don't match between methods"
        )

    def test_extract_features_with_audio_data_returns_valid_audio_features(
        self, processor: LibrosaAudioProcessor, valid_raw_audio: RawAudio
    ):
        """Test that audio_features data contains valid values."""
        result = processor.extract_features_with_audio_data(valid_raw_audio)
        audio_features = result["audio_features"]

        # Check metadata
        assert audio_features["sample_rate"] > 0
        assert audio_features["duration"] > 0

        # Check waveform
        assert isinstance(audio_features["waveform"], list)
        assert len(audio_features["waveform"]) > 0

        # Check mel_spectrogram shape (128 x T)
        assert isinstance(audio_features["mel_spectrogram"], list)
        assert len(audio_features["mel_spectrogram"]) == 128

        # Check chroma shape (12 x T)
        assert isinstance(audio_features["chroma"], list)
        assert len(audio_features["chroma"]) == 12

        # Check mfcc shape (20 x T)
        assert isinstance(audio_features["mfcc"], list)
        assert len(audio_features["mfcc"]) == 20

        # Check delta_mfcc shape (20 x T)
        assert isinstance(audio_features["delta_mfcc"], list)
        assert len(audio_features["delta_mfcc"]) == 20

        # Check delta_delta_mfcc shape (20 x T)
        assert isinstance(audio_features["delta_delta_mfcc"], list)
        assert len(audio_features["delta_delta_mfcc"]) == 20

        # Check pitch contour
        assert isinstance(audio_features["pitch_times"], list)
        assert isinstance(audio_features["pitch_values"], list)
        assert len(audio_features["pitch_times"]) == len(audio_features["pitch_values"])

        # Check RMS contour
        assert isinstance(audio_features["rms_contour"], list)
        assert len(audio_features["rms_contour"]) > 0

    def test_extract_features_with_audio_data_with_empty_audio_raises_error(
        self, processor: LibrosaAudioProcessor
    ):
        """Test that empty audio raises InvalidAudioError."""
        with pytest.raises(InvalidAudioError):
            empty_audio = RawAudio.from_bytes(b"", "empty.wav")
            processor.extract_features_with_audio_data(empty_audio)

    def test_extract_features_with_audio_data_with_corrupted_audio_raises_error(
        self, processor: LibrosaAudioProcessor
    ):
        """Test that corrupted audio raises InvalidAudioError."""
        corrupted_audio = RawAudio.from_bytes(b"not an audio file", "corrupted.wav")

        with pytest.raises(InvalidAudioError):
            processor.extract_features_with_audio_data(corrupted_audio)

    def test_extract_features_with_audio_data_is_deterministic(
        self, processor: LibrosaAudioProcessor, valid_raw_audio: RawAudio
    ):
        """Test that extraction is deterministic for same audio."""
        result1 = processor.extract_features_with_audio_data(valid_raw_audio)
        result2 = processor.extract_features_with_audio_data(valid_raw_audio)

        # Check features are identical
        np.testing.assert_array_almost_equal(
            result1["features"],
            result2["features"],
            decimal=6,
            err_msg="Feature extraction is not deterministic"
        )

        # Check audio_features metadata is identical
        assert result1["audio_features"]["sample_rate"] == result2["audio_features"]["sample_rate"]
        assert result1["audio_features"]["duration"] == result2["audio_features"]["duration"]
