"""
Unit tests for Model v1 Feature Extractor.

This test suite validates the feature extraction logic for the v1 model (DecisionTreeClassifier).
Tests cover:
- Valid audio processing
- Feature dimensions validation (must be 162)
- Individual feature component validation
- Invalid inputs handling
- Edge cases (silent audio, short audio)
- Deterministic output verification
"""

import importlib.util
from pathlib import Path

# Dynamically import feature extractor to avoid path conflicts
# (tests/unit/models conflicts with backend/models in sys.path)
FEATURE_EXTRACTOR_PATH = (
    Path(__file__).resolve().parents[3] / "models" / "v1" / "feature_extractor.py"
)

spec = importlib.util.spec_from_file_location("v1_feature_extractor", FEATURE_EXTRACTOR_PATH)
v1_extractor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v1_extractor_module)
extract_features = v1_extractor_module.extract_features

import io

import numpy as np
import pytest
import soundfile as sf


class TestV1FeatureExtractorValidInput:
    """Test valid audio input processing."""

    def test_extract_features_from_valid_audio(self, sample_audio_file):
        """Test feature extraction from valid audio bytes."""
        features = extract_features(sample_audio_file, "test.wav")

        assert features is not None, "Features should not be None"
        assert isinstance(features, np.ndarray), "Features should be numpy array"
        assert features.dtype in [np.float32, np.float64], "Features should be float type"
        assert not np.isnan(features).any(), "Features should not contain NaN values"
        assert not np.isinf(features).any(), "Features should not contain infinite values"

    def test_feature_dimension_is_162(self, sample_audio_file):
        """Test that extracted features have exactly 162 dimensions."""
        features = extract_features(sample_audio_file, "test.wav")

        assert features.shape == (162,), f"Expected feature shape (162,), got {features.shape}"
        assert len(features) == 162, f"Expected 162 features, got {len(features)}"

    @pytest.mark.parametrize("audio_format", ["wav", "mp3", "m4a"])
    def test_supports_multiple_audio_formats(self, sample_audio_file, audio_format):
        """Test feature extraction with different audio format filenames."""
        filename = f"test.{audio_format}"
        features = extract_features(sample_audio_file, filename)

        assert features.shape == (
            162,
        ), f"Failed for format {audio_format}: expected (162,), got {features.shape}"

    def test_deterministic_output_same_audio(self, sample_audio_file):
        """Test that same audio produces identical features (deterministic)."""
        features1 = extract_features(sample_audio_file, "test.wav")
        features2 = extract_features(sample_audio_file, "test.wav")

        np.testing.assert_array_almost_equal(
            features1, features2, decimal=10, err_msg="Same audio should produce identical features"
        )


class TestV1FeatureComponents:
    """Test individual feature components."""

    def test_zcr_component_exists(self, sample_audio_file):
        """Test Zero Crossing Rate component (1 feature)."""
        features = extract_features(sample_audio_file, "test.wav")

        # ZCR is the first feature
        zcr = features[0]
        assert isinstance(zcr, (np.floating, float)), "ZCR should be a float"
        assert zcr >= 0.0, "ZCR should be non-negative"

    def test_chroma_stft_component_exists(self, sample_audio_file):
        """Test Chroma STFT component (12 features)."""
        features = extract_features(sample_audio_file, "test.wav")

        # Chroma STFT: features[1:13] (12 features)
        chroma_stft = features[1:13]
        assert len(chroma_stft) == 12, "Chroma STFT should have 12 features"
        assert np.all(chroma_stft >= 0.0), "Chroma features should be non-negative"

    def test_mfcc_component_exists(self, sample_audio_file):
        """Test MFCC component (20 features)."""
        features = extract_features(sample_audio_file, "test.wav")

        # MFCC: features[13:33] (20 features)
        mfcc = features[13:33]
        assert len(mfcc) == 20, "MFCC should have 20 features"
        # MFCCs can be positive or negative, just check they're valid numbers
        assert not np.isnan(mfcc).any(), "MFCC should not contain NaN"

    def test_rms_component_exists(self, sample_audio_file):
        """Test RMS component (1 feature)."""
        features = extract_features(sample_audio_file, "test.wav")

        # RMS: features[33] (1 feature)
        rms = features[33]
        assert isinstance(rms, (np.floating, float)), "RMS should be a float"
        assert rms >= 0.0, "RMS should be non-negative"

    def test_mel_spectrogram_component_exists(self, sample_audio_file):
        """Test Mel Spectrogram component (128 features)."""
        features = extract_features(sample_audio_file, "test.wav")

        # Mel Spectrogram: features[34:162] (128 features)
        mel = features[34:162]
        assert len(mel) == 128, "Mel Spectrogram should have 128 features"
        assert np.all(mel >= 0.0), "Mel Spectrogram features should be non-negative"

    def test_feature_components_sum_to_162(self):
        """Verify that all feature components sum to 162."""
        zcr_count = 1
        chroma_count = 12
        mfcc_count = 20
        rms_count = 1
        mel_count = 128

        total = zcr_count + chroma_count + mfcc_count + rms_count + mel_count
        assert total == 162, f"Feature components should sum to 162, got {total}"


class TestV1FeatureExtractorInvalidInput:
    """Test handling of invalid inputs."""

    def test_corrupted_audio_raises_error(self, corrupted_audio_file):
        """Test that corrupted audio file raises ValueError."""
        with pytest.raises(ValueError, match="Failed to extract features"):
            extract_features(corrupted_audio_file, "corrupted.wav")

    def test_empty_audio_raises_error(self):
        """Test that empty audio bytes raise ValueError."""
        with pytest.raises(ValueError, match="Failed to extract features"):
            extract_features(b"", "empty.wav")

    def test_invalid_audio_format_raises_error(self):
        """Test that invalid audio format raises ValueError."""
        invalid_audio = b"INVALID AUDIO DATA RANDOM BYTES"
        with pytest.raises(ValueError, match="Failed to extract features"):
            extract_features(invalid_audio, "invalid.wav")

    def test_none_audio_bytes_raises_error(self):
        """Test that None audio bytes raise appropriate error."""
        with pytest.raises((ValueError, TypeError, AttributeError)):
            extract_features(None, "none.wav")


class TestV1FeatureExtractorEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_silent_audio_produces_valid_features(self):
        """Test that silent audio (all zeros) produces valid features."""
        # Create silent audio
        sample_rate = 22050
        duration = 3.0  # Need >2.5s after 0.6s offset
        silent_audio = np.zeros(int(sample_rate * duration), dtype=np.float32)

        # Convert to WAV bytes
        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, silent_audio, sample_rate, format="WAV")
        audio_buffer.seek(0)
        audio_bytes = audio_buffer.read()

        # Extract features
        features = extract_features(audio_bytes, "silent.wav")

        assert features.shape == (162,), "Silent audio should still produce 162 features"
        # Silent audio will have very low values but should not have NaN
        assert not np.isnan(features).any(), "Silent audio should not produce NaN features"

        # ZCR should be zero or very low for silent audio
        zcr = features[0]
        assert zcr < 0.01, f"ZCR for silent audio should be very low, got {zcr}"

    def test_very_short_audio_with_offset(self):
        """Test audio shorter than duration + offset (< 3.1s)."""
        # Create audio that's only 2 seconds (less than 2.5 + 0.6)
        sample_rate = 22050
        duration = 2.0
        audio_data = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sample_rate * duration)))

        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, sample_rate, format="WAV")
        audio_buffer.seek(0)
        audio_bytes = audio_buffer.read()

        # Librosa will handle this by loading what's available
        # Should not raise error, but load less than 2.5s
        features = extract_features(audio_bytes, "short.wav")

        assert features.shape == (
            162,
        ), "Short audio should still produce 162 features (librosa pads or uses available)"

    def test_very_long_audio_uses_only_segment(self):
        """Test that long audio uses only the 2.5s segment from offset 0.6s."""
        # Create 10 second audio
        sample_rate = 22050
        duration = 10.0
        audio_data = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sample_rate * duration)))

        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, audio_data, sample_rate, format="WAV")
        audio_buffer.seek(0)
        audio_bytes = audio_buffer.read()

        features1 = extract_features(audio_bytes, "long.wav")

        # Create another long audio with different content after 3.1s
        # The segment from 0.6s to 3.1s should be identical
        audio_data2 = audio_data.copy()
        start_idx = int(sample_rate * 3.5)  # After the extracted segment
        audio_data2[start_idx:] = np.random.randn(len(audio_data2) - start_idx)

        audio_buffer2 = io.BytesIO()
        sf.write(audio_buffer2, audio_data2, sample_rate, format="WAV")
        audio_buffer2.seek(0)
        audio_bytes2 = audio_buffer2.read()

        features2 = extract_features(audio_bytes2, "long2.wav")

        # Features should be identical since only 0.6-3.1s segment is used
        np.testing.assert_array_almost_equal(
            features1, features2, decimal=5, err_msg="Features should be identical for same segment"
        )

    def test_mono_vs_stereo_audio(self):
        """Test that stereo audio is handled correctly (converted to mono)."""
        sample_rate = 22050
        duration = 3.0

        # Create mono audio
        mono_audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, int(sample_rate * duration)))
        mono_buffer = io.BytesIO()
        sf.write(mono_buffer, mono_audio, sample_rate, format="WAV")
        mono_buffer.seek(0)
        mono_bytes = mono_buffer.read()

        # Create stereo audio (duplicate mono to both channels)
        stereo_audio = np.stack([mono_audio, mono_audio], axis=1)
        stereo_buffer = io.BytesIO()
        sf.write(stereo_buffer, stereo_audio, sample_rate, format="WAV")
        stereo_buffer.seek(0)
        stereo_bytes = stereo_buffer.read()

        # Extract features from both
        mono_features = extract_features(mono_bytes, "mono.wav")
        stereo_features = extract_features(stereo_bytes, "stereo.wav")

        # Both should produce valid 162 features
        assert mono_features.shape == (162,), "Mono should produce 162 features"
        assert stereo_features.shape == (162,), "Stereo should produce 162 features"

        # Features should be very similar (librosa converts stereo to mono)
        np.testing.assert_array_almost_equal(
            mono_features,
            stereo_features,
            decimal=5,
            err_msg="Mono and stereo (identical channels) should produce similar features",
        )

    def test_different_sample_rates_normalized(self):
        """Test that different sample rates are handled correctly."""
        duration = 3.0
        frequency = 440

        # Test with different sample rates
        for sample_rate in [16000, 22050, 44100, 48000]:
            audio_data = np.sin(
                2 * np.pi * frequency * np.linspace(0, duration, int(sample_rate * duration))
            )

            audio_buffer = io.BytesIO()
            sf.write(audio_buffer, audio_data, sample_rate, format="WAV")
            audio_buffer.seek(0)
            audio_bytes = audio_buffer.read()

            features = extract_features(audio_bytes, f"test_{sample_rate}.wav")

            assert features.shape == (
                162,
            ), f"Sample rate {sample_rate} should produce 162 features, got {features.shape}"
            assert not np.isnan(
                features
            ).any(), f"Sample rate {sample_rate} should not produce NaN features"


class TestV1FeatureExtractorRealAudio:
    """Test with real CREMA-D audio samples (if available)."""

    @pytest.fixture
    def crema_d_path(self):
        """Path to CREMA-D dataset."""
        return Path(
            "/Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition/data/AudioWAV"
        )

    def test_real_crema_d_audio_happy(self, crema_d_path):
        """Test feature extraction on real CREMA-D happy audio."""
        audio_file = crema_d_path / "1001_DFA_HAP_XX.wav"

        if not audio_file.exists():
            pytest.skip("CREMA-D audio file not found")

        # Load audio file
        with open(audio_file, "rb") as f:
            audio_bytes = f.read()

        features = extract_features(audio_bytes, audio_file.name)

        assert features.shape == (162,), f"Expected (162,), got {features.shape}"
        assert not np.isnan(features).any(), "Real audio should not produce NaN"
        assert not np.isinf(features).any(), "Real audio should not produce inf"

    def test_real_crema_d_audio_sad(self, crema_d_path):
        """Test feature extraction on real CREMA-D sad audio."""
        audio_file = crema_d_path / "1001_DFA_SAD_XX.wav"

        if not audio_file.exists():
            pytest.skip("CREMA-D audio file not found")

        with open(audio_file, "rb") as f:
            audio_bytes = f.read()

        features = extract_features(audio_bytes, audio_file.name)

        assert features.shape == (162,), f"Expected (162,), got {features.shape}"
        assert not np.isnan(features).any(), "Real audio should not produce NaN"

    def test_real_crema_d_audio_angry(self, crema_d_path):
        """Test feature extraction on real CREMA-D angry audio."""
        audio_file = crema_d_path / "1001_DFA_ANG_XX.wav"

        if not audio_file.exists():
            pytest.skip("CREMA-D audio file not found")

        with open(audio_file, "rb") as f:
            audio_bytes = f.read()

        features = extract_features(audio_bytes, audio_file.name)

        assert features.shape == (162,), f"Expected (162,), got {features.shape}"
        assert not np.isnan(features).any(), "Real audio should not produce NaN"

    def test_different_real_audio_produce_different_features(self, crema_d_path):
        """Test that different emotion audio produce different features."""
        happy_file = crema_d_path / "1001_DFA_HAP_XX.wav"
        sad_file = crema_d_path / "1001_DFA_SAD_XX.wav"

        if not happy_file.exists() or not sad_file.exists():
            pytest.skip("CREMA-D audio files not found")

        with open(happy_file, "rb") as f:
            happy_bytes = f.read()
        with open(sad_file, "rb") as f:
            sad_bytes = f.read()

        happy_features = extract_features(happy_bytes, happy_file.name)
        sad_features = extract_features(sad_bytes, sad_file.name)

        # Features should be different
        assert not np.allclose(
            happy_features, sad_features, rtol=0.1
        ), "Different emotions should produce noticeably different features"


@pytest.mark.unit
class TestV1FeatureExtractorPerformance:
    """Test performance characteristics."""

    def test_feature_extraction_completes_quickly(self, sample_audio_file):
        """Test that feature extraction completes in reasonable time."""
        import time

        start_time = time.time()
        features = extract_features(sample_audio_file, "test.wav")
        elapsed = time.time() - start_time

        # Feature extraction should complete in < 2 seconds
        assert elapsed < 2.0, f"Feature extraction took {elapsed:.2f}s, expected < 2.0s"
        assert features.shape == (162,), "Features should still be valid"

    def test_multiple_extractions_consistent_timing(self, sample_audio_file):
        """Test that multiple extractions have consistent timing."""
        import time

        timings = []
        for _ in range(5):
            start_time = time.time()
            extract_features(sample_audio_file, "test.wav")
            elapsed = time.time() - start_time
            timings.append(elapsed)

        avg_time = np.mean(timings)
        std_time = np.std(timings)

        # Standard deviation should be small (consistent performance)
        assert (
            std_time < avg_time * 0.5
        ), f"Timing inconsistent: mean={avg_time:.3f}s, std={std_time:.3f}s"
        assert avg_time < 2.0, f"Average extraction time {avg_time:.2f}s should be < 2.0s"
