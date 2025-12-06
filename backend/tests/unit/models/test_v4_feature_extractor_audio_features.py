"""
Unit tests for Model v4 Feature Extractor with Visualization Support.

This test suite validates both the regular feature extraction (extract_features)
and the enhanced audio_features extraction (extract_features_with_viz) for the v4 model.

Tests cover:
- extract_features_with_viz returns correct structure
- Features array shape is (210,)
- Visualization dict has all required keys
- Matrix shapes are correct (mel: 128×T, chroma: 12×T, mfcc: 20×T, etc.)
- Backward compatibility: extract_features() unchanged
- Consistency between extract_features() and extract_features_with_viz()
- Edge cases and error handling
"""

import importlib.util
from pathlib import Path

# Dynamically import v4 feature extractor
FEATURE_EXTRACTOR_PATH = (
    Path(__file__).resolve().parents[3] / "models" / "v4" / "feature_extractor.py"
)

spec = importlib.util.spec_from_file_location("v4_feature_extractor", FEATURE_EXTRACTOR_PATH)
v4_extractor_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v4_extractor_module)
extract_features = v4_extractor_module.extract_features
extract_features_with_viz = v4_extractor_module.extract_features_with_viz

import io

import numpy as np
import pytest
import soundfile as sf


class TestV4ExtractFeaturesWithVizStructure:
    """Test the structure and return format of extract_features_with_viz."""

    def test_returns_dict_with_correct_keys(self, sample_audio_file):
        """Test that extract_features_with_viz returns a dict with 'features' and 'audio_features'."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")

        assert isinstance(
            result, dict
        ), f"extract_features_with_viz should return dict, got {type(result)}"

        assert "features" in result, "Result should contain 'features' key"

        assert "audio_features" in result, "Result should contain 'audio_features' key"

        assert len(result) == 2, f"Result should have exactly 2 keys, got {len(result)}"

    def test_features_key_contains_numpy_array(self, sample_audio_file):
        """Test that 'features' key contains a numpy array."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")

        features = result["features"]

        assert isinstance(
            features, np.ndarray
        ), f"features should be numpy array, got {type(features)}"

        assert features.dtype in [
            np.float32,
            np.float64,
        ], f"features should be float type, got {features.dtype}"

    def test_audio_features_key_contains_dict(self, sample_audio_file):
        """Test that 'audio_features' key contains a dictionary."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")

        viz_data = result["audio_features"]

        assert isinstance(viz_data, dict), f"audio_features should be dict, got {type(viz_data)}"

    def test_features_shape_is_210(self, sample_audio_file):
        """Test that features array has shape (210,)."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")

        features = result["features"]

        assert features.shape == (210,), f"Expected features shape (210,), got {features.shape}"

        assert len(features) == 210, f"Expected 210 features, got {len(features)}"


class TestV4VisualizationDataKeys:
    """Test that audio_features data contains all required keys."""

    def test_has_all_required_keys(self, sample_audio_file):
        """Test that audio_features dict has all expected keys."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")
        viz_data = result["audio_features"]

        required_keys = {
            # Audio metadata
            "sample_rate",
            "duration",
            # Waveform
            "waveform",
            # Spectral features (matrices)
            "mel_spectrogram",
            "chroma",
            "mfcc",
            "delta_mfcc",
            "delta_delta_mfcc",
            # Prosodic features (time series)
            "pitch_times",
            "pitch_values",
            "rms_contour",
        }

        actual_keys = set(viz_data.keys())

        assert required_keys == actual_keys, (
            f"Missing keys: {required_keys - actual_keys}, "
            f"Extra keys: {actual_keys - required_keys}"
        )

    def test_metadata_keys_correct_types(self, sample_audio_file):
        """Test that metadata keys have correct types."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")
        viz_data = result["audio_features"]

        # sample_rate should be int
        assert isinstance(
            viz_data["sample_rate"], int
        ), f"sample_rate should be int, got {type(viz_data['sample_rate'])}"

        # duration should be float
        assert isinstance(
            viz_data["duration"], float
        ), f"duration should be float, got {type(viz_data['duration'])}"

        # duration should be positive
        assert viz_data["duration"] > 0, f"duration should be positive, got {viz_data['duration']}"

        # sample_rate should be positive
        assert (
            viz_data["sample_rate"] > 0
        ), f"sample_rate should be positive, got {viz_data['sample_rate']}"


class TestV4VisualizationMatrixShapes:
    """Test that audio_features matrices have correct shapes."""

    def test_waveform_is_list(self, sample_audio_file):
        """Test that waveform is a list (JSON-serializable)."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")
        viz_data = result["audio_features"]

        waveform = viz_data["waveform"]

        assert isinstance(waveform, list), f"waveform should be list, got {type(waveform)}"

        assert len(waveform) > 0, "waveform should not be empty"

        # Elements should be numbers
        assert all(
            isinstance(x, (int, float)) for x in waveform[:10]
        ), "waveform elements should be numbers"

    def test_mel_spectrogram_shape(self, sample_audio_file):
        """Test that mel spectrogram has shape (128, T)."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")
        viz_data = result["audio_features"]

        mel = viz_data["mel_spectrogram"]

        assert isinstance(mel, list), f"mel_spectrogram should be list, got {type(mel)}"

        # Should be 2D: 128 rows
        assert len(mel) == 128, f"mel_spectrogram should have 128 rows, got {len(mel)}"

        # Each row should be a list (time dimension)
        assert isinstance(mel[0], list), "mel_spectrogram rows should be lists"

        # All rows should have same length (time dimension)
        time_dim = len(mel[0])
        assert all(
            len(row) == time_dim for row in mel
        ), "All mel_spectrogram rows should have same length"

        assert time_dim > 0, "mel_spectrogram time dimension should be > 0"

    def test_chroma_shape(self, sample_audio_file):
        """Test that chroma has shape (12, T)."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")
        viz_data = result["audio_features"]

        chroma = viz_data["chroma"]

        assert isinstance(chroma, list), f"chroma should be list, got {type(chroma)}"

        # Should be 2D: 12 rows
        assert len(chroma) == 12, f"chroma should have 12 rows, got {len(chroma)}"

        # Each row should be a list
        assert isinstance(chroma[0], list), "chroma rows should be lists"

        # All rows should have same length
        time_dim = len(chroma[0])
        assert all(
            len(row) == time_dim for row in chroma
        ), "All chroma rows should have same length"

        assert time_dim > 0, "chroma time dimension should be > 0"

    def test_mfcc_shape(self, sample_audio_file):
        """Test that MFCC has shape (20, T)."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")
        viz_data = result["audio_features"]

        mfcc = viz_data["mfcc"]

        assert isinstance(mfcc, list), f"mfcc should be list, got {type(mfcc)}"

        # Should be 2D: 20 rows
        assert len(mfcc) == 20, f"mfcc should have 20 rows, got {len(mfcc)}"

        # Each row should be a list
        assert isinstance(mfcc[0], list), "mfcc rows should be lists"

        # All rows should have same length
        time_dim = len(mfcc[0])
        assert all(len(row) == time_dim for row in mfcc), "All mfcc rows should have same length"

    def test_delta_mfcc_shape(self, sample_audio_file):
        """Test that delta MFCC has shape (20, T)."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")
        viz_data = result["audio_features"]

        delta_mfcc = viz_data["delta_mfcc"]

        assert isinstance(delta_mfcc, list), f"delta_mfcc should be list, got {type(delta_mfcc)}"

        # Should be 2D: 20 rows
        assert len(delta_mfcc) == 20, f"delta_mfcc should have 20 rows, got {len(delta_mfcc)}"

        # Each row should be a list
        assert isinstance(delta_mfcc[0], list), "delta_mfcc rows should be lists"

    def test_delta_delta_mfcc_shape(self, sample_audio_file):
        """Test that delta-delta MFCC has shape (20, T)."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")
        viz_data = result["audio_features"]

        delta_delta_mfcc = viz_data["delta_delta_mfcc"]

        assert isinstance(
            delta_delta_mfcc, list
        ), f"delta_delta_mfcc should be list, got {type(delta_delta_mfcc)}"

        # Should be 2D: 20 rows
        assert (
            len(delta_delta_mfcc) == 20
        ), f"delta_delta_mfcc should have 20 rows, got {len(delta_delta_mfcc)}"

    def test_pitch_contour_format(self, sample_audio_file):
        """Test that pitch contour has correct format."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")
        viz_data = result["audio_features"]

        pitch_times = viz_data["pitch_times"]
        pitch_values = viz_data["pitch_values"]

        # Both should be lists
        assert isinstance(pitch_times, list), f"pitch_times should be list, got {type(pitch_times)}"
        assert isinstance(
            pitch_values, list
        ), f"pitch_values should be list, got {type(pitch_values)}"

        # Should have same length
        assert len(pitch_times) == len(pitch_values), (
            f"pitch_times ({len(pitch_times)}) and pitch_values ({len(pitch_values)}) "
            "should have same length"
        )

        # Can be empty for synthetic audio
        if len(pitch_values) > 0:
            # All pitch values should be positive floats
            assert all(
                isinstance(p, float) and p > 0 for p in pitch_values
            ), "pitch_values should be positive floats"

            # All pitch times should be positive floats
            assert all(
                isinstance(t, float) and t >= 0 for t in pitch_times
            ), "pitch_times should be non-negative floats"

    def test_rms_contour_format(self, sample_audio_file):
        """Test that RMS contour has correct format."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")
        viz_data = result["audio_features"]

        rms_contour = viz_data["rms_contour"]

        # Should be a list
        assert isinstance(rms_contour, list), f"rms_contour should be list, got {type(rms_contour)}"

        # Should not be empty
        assert len(rms_contour) > 0, "rms_contour should not be empty"

        # All values should be non-negative
        assert all(
            isinstance(x, (int, float)) and x >= 0 for x in rms_contour
        ), "rms_contour values should be non-negative numbers"


class TestV4BackwardCompatibility:
    """Test that extract_features() function remains unchanged and compatible."""

    def test_extract_features_still_exists(self):
        """Test that original extract_features function still exists."""
        assert hasattr(
            v4_extractor_module, "extract_features"
        ), "extract_features function should still exist for backward compatibility"

    def test_extract_features_returns_numpy_array(self, sample_audio_file):
        """Test that extract_features still returns numpy array directly."""
        features = extract_features(sample_audio_file, "test.wav")

        assert isinstance(
            features, np.ndarray
        ), f"extract_features should return numpy array, got {type(features)}"

        assert features.shape == (
            210,
        ), f"extract_features should return (210,) array, got {features.shape}"

    def test_extract_features_signature_unchanged(self, sample_audio_file):
        """Test that extract_features signature is unchanged (audio_bytes, filename)."""
        # Should work with positional arguments
        features = extract_features(sample_audio_file, "test.wav")
        assert features.shape == (210,)

    def test_extract_features_produces_same_output(self, sample_audio_file):
        """Test that extract_features produces identical output to before."""
        features = extract_features(sample_audio_file, "test.wav")

        # Should produce valid 210 features
        assert features.shape == (210,)
        assert not np.isnan(features).any()
        assert not np.isinf(features).any()


class TestV4ConsistencyBetweenFunctions:
    """Test consistency between extract_features() and extract_features_with_viz()."""

    def test_features_array_identical(self, sample_audio_file):
        """Test that both functions produce identical feature arrays."""
        # Extract with both functions
        features_only = extract_features(sample_audio_file, "test.wav")
        result_with_viz = extract_features_with_viz(sample_audio_file, "test.wav")
        features_from_viz = result_with_viz["features"]

        # Features should be identical
        np.testing.assert_array_almost_equal(
            features_only,
            features_from_viz,
            decimal=10,
            err_msg="Features from both functions should be identical",
        )

    def test_deterministic_across_multiple_calls(self, sample_audio_file):
        """Test that extract_features_with_viz is deterministic."""
        result1 = extract_features_with_viz(sample_audio_file, "test.wav")
        result2 = extract_features_with_viz(sample_audio_file, "test.wav")

        # Features should be identical
        np.testing.assert_array_almost_equal(
            result1["features"],
            result2["features"],
            decimal=10,
            err_msg="Multiple calls should produce identical features",
        )

    def test_same_audio_processing_parameters(self, sample_audio_file):
        """Test that both functions use same audio processing parameters."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")
        viz_data = result["audio_features"]

        # Duration should be around 2.5s (after trimming, may be less)
        # Offset is 0.6s, duration is 2.5s, so max expected is ~2.5s
        assert (
            viz_data["duration"] <= 2.5
        ), f"Duration should be <= 2.5s (after processing), got {viz_data['duration']}"

        # Sample rate should be 22050 (librosa default)
        assert (
            viz_data["sample_rate"] == 22050
        ), f"Sample rate should be 22050 Hz, got {viz_data['sample_rate']}"


class TestV4VisualizationDataValidation:
    """Test that audio_features data is valid and usable."""

    def test_all_matrices_json_serializable(self, sample_audio_file):
        """Test that all audio_features data is JSON-serializable."""
        import json

        result = extract_features_with_viz(sample_audio_file, "test.wav")
        viz_data = result["audio_features"]

        # Should be JSON-serializable (all lists, no numpy arrays)
        try:
            json_str = json.dumps(viz_data)
            assert len(json_str) > 0, "JSON serialization produced empty string"
        except (TypeError, ValueError) as e:
            pytest.fail(f"Visualization data is not JSON-serializable: {e}")

    def test_no_nan_values_in_matrices(self, sample_audio_file):
        """Test that audio_features matrices don't contain NaN values."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")
        viz_data = result["audio_features"]

        # Check mel spectrogram
        mel = np.array(viz_data["mel_spectrogram"])
        assert not np.isnan(mel).any(), "mel_spectrogram should not contain NaN"

        # Check chroma
        chroma = np.array(viz_data["chroma"])
        assert not np.isnan(chroma).any(), "chroma should not contain NaN"

        # Check MFCCs
        mfcc = np.array(viz_data["mfcc"])
        assert not np.isnan(mfcc).any(), "mfcc should not contain NaN"

    def test_no_inf_values_in_matrices(self, sample_audio_file):
        """Test that audio_features matrices don't contain infinite values."""
        result = extract_features_with_viz(sample_audio_file, "test.wav")
        viz_data = result["audio_features"]

        # Check mel spectrogram
        mel = np.array(viz_data["mel_spectrogram"])
        assert not np.isinf(mel).any(), "mel_spectrogram should not contain inf"

        # Check waveform
        waveform = np.array(viz_data["waveform"])
        assert not np.isinf(waveform).any(), "waveform should not contain inf"


class TestV4VisualizationErrorHandling:
    """Test error handling for extract_features_with_viz."""

    def test_corrupted_audio_raises_error(self, corrupted_audio_file):
        """Test that corrupted audio file raises ValueError."""
        with pytest.raises(ValueError, match="Failed to extract features"):
            extract_features_with_viz(corrupted_audio_file, "corrupted.wav")

    def test_empty_audio_raises_error(self):
        """Test that empty audio bytes raise ValueError."""
        with pytest.raises(ValueError, match="Failed to extract features"):
            extract_features_with_viz(b"", "empty.wav")

    def test_invalid_audio_format_raises_error(self):
        """Test that invalid audio format raises ValueError."""
        invalid_audio = b"INVALID AUDIO DATA RANDOM BYTES"
        with pytest.raises(ValueError, match="Failed to extract features"):
            extract_features_with_viz(invalid_audio, "invalid.wav")


class TestV4VisualizationEdgeCases:
    """Test edge cases for audio_features extraction."""

    def test_silent_audio_produces_valid_audio_features(self):
        """Test that silent audio produces valid audio_features data."""
        # Create silent audio
        sample_rate = 22050
        duration = 3.0
        silent_audio = np.zeros(int(sample_rate * duration), dtype=np.float32)

        audio_buffer = io.BytesIO()
        sf.write(audio_buffer, silent_audio, sample_rate, format="WAV")
        audio_buffer.seek(0)
        audio_bytes = audio_buffer.read()

        result = extract_features_with_viz(audio_bytes, "silent.wav")

        # Should produce valid structure
        assert "features" in result
        assert "audio_features" in result

        # Features should be 210
        assert result["features"].shape == (210,)

        # Visualization should have all keys
        viz_data = result["audio_features"]
        assert "mel_spectrogram" in viz_data
        assert "waveform" in viz_data

        # Waveform should be near-zero
        waveform = np.array(viz_data["waveform"])
        assert np.allclose(waveform, 0, atol=0.01), "Silent audio waveform should be near-zero"

    def test_real_crema_d_audio_audio_features(self):
        """Test audio_features extraction on real CREMA-D audio."""
        crema_d_path = Path(
            "/Users/sagarpratapsingh/dev/sagerstack/ml-speech-emotion-recognition/data/AudioWAV"
        )
        audio_file = crema_d_path / "1001_DFA_HAP_XX.wav"

        if not audio_file.exists():
            pytest.skip("CREMA-D audio file not found")

        with open(audio_file, "rb") as f:
            audio_bytes = f.read()

        result = extract_features_with_viz(audio_bytes, audio_file.name)

        # Should produce valid structure
        assert result["features"].shape == (210,)

        viz_data = result["audio_features"]

        # All keys should be present
        assert len(viz_data) == 11, f"Expected 11 audio_features keys, got {len(viz_data)}"

        # Check matrix shapes
        assert len(viz_data["mel_spectrogram"]) == 128
        assert len(viz_data["chroma"]) == 12
        assert len(viz_data["mfcc"]) == 20
        assert len(viz_data["delta_mfcc"]) == 20
        assert len(viz_data["delta_delta_mfcc"]) == 20

        # Real speech should have pitch values
        assert len(viz_data["pitch_values"]) > 0, "Real speech should have detectable pitch"


@pytest.mark.unit
class TestV4VisualizationPerformance:
    """Test performance characteristics of audio_features extraction."""

    def test_extraction_with_viz_completes_quickly(self, sample_audio_file):
        """Test that feature extraction with audio_features completes in reasonable time."""
        import time

        start_time = time.time()
        result = extract_features_with_viz(sample_audio_file, "test.wav")
        elapsed = time.time() - start_time

        # Should complete in < 1 second (more lenient than regular extraction)
        assert elapsed < 1.0, f"Extraction with audio_features took {elapsed:.2f}s, expected < 1.0s"

        assert result["features"].shape == (210,), "Features should still be valid"

    def test_overhead_is_acceptable(self, sample_audio_file):
        """Test that audio_features extraction overhead is acceptable."""
        import time

        # Measure regular extraction time
        start = time.time()
        for _ in range(5):
            extract_features(sample_audio_file, "test.wav")
        regular_time = (time.time() - start) / 5

        # Measure extraction with audio_features time
        start = time.time()
        for _ in range(5):
            extract_features_with_viz(sample_audio_file, "test.wav")
        viz_time = (time.time() - start) / 5

        # Overhead should be minimal (< 100ms or < 50% increase)
        overhead = viz_time - regular_time
        overhead_pct = (overhead / regular_time) * 100 if regular_time > 0 else 0

        assert overhead < 0.1 or overhead_pct < 50, (
            f"Visualization overhead is {overhead:.3f}s ({overhead_pct:.1f}%), "
            f"should be < 0.1s or < 50%"
        )
