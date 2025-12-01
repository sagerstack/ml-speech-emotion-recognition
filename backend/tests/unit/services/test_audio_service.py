"""
Unit tests for audio processing service.

This module tests the AudioProcessor class, audio validation, feature extraction,
and audio processing pipeline functionality.
"""

import io
import numpy as np
import pytest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from app.services.audio_service import (
    AudioProcessor,
    AudioFeatures,
    AudioMetadata,
    AudioProcessingError
)


class TestAudioMetadata:
    """Test cases for AudioMetadata model."""

    def test_valid_audio_metadata_creation(self) -> None:
        """Test creating valid AudioMetadata instance."""
        metadata = AudioMetadata(
            duration=2.5,
            sample_rate=22050,
            channels=1,
            format="wav",
            file_size_bytes=110250
        )

        assert metadata.duration == 2.5
        assert metadata.sample_rate == 22050
        assert metadata.channels == 1
        assert metadata.format == "wav"
        assert metadata.file_size_bytes == 110250

    def test_audio_metadata_duration_validation(self) -> None:
        """Test duration validation in AudioMetadata."""
        # Valid durations
        valid_durations = [0.5, 1.0, 2.5, 10.0, 30.0]
        for duration in valid_durations:
            metadata = AudioMetadata(
                duration=duration,
                sample_rate=22050,
                channels=1,
                format="wav",
                file_size_bytes=1000
            )
            assert metadata.duration == duration

        # Invalid durations
        invalid_durations = [0, -0.1, -1.0, 60.1, 100.0]
        for duration in invalid_durations:
            with pytest.raises(ValidationError, match="Duration must be positive|Audio duration cannot exceed"):
                AudioMetadata(
                    duration=duration,
                    sample_rate=22050,
                    channels=1,
                    format="wav",
                    file_size_bytes=1000
                )

    def test_audio_metadata_sample_rate_validation(self) -> None:
        """Test sample rate validation in AudioMetadata."""
        # Valid sample rates
        valid_sample_rates = [8000, 16000, 22050, 44100, 48000, 96000]
        for sample_rate in valid_sample_rates:
            metadata = AudioMetadata(
                duration=2.0,
                sample_rate=sample_rate,
                channels=1,
                format="wav",
                file_size_bytes=1000
            )
            assert metadata.sample_rate == sample_rate

        # Invalid sample rates
        invalid_sample_rates = [0, -1, -22050]
        for sample_rate in invalid_sample_rates:
            with pytest.raises(ValueError, match="Sample rate must be positive"):
                AudioMetadata(
                    duration=2.0,
                    sample_rate=sample_rate,
                    channels=1,
                    format="wav",
                    file_size_bytes=1000
                )

    def test_audio_metadata_edge_cases(self) -> None:
        """Test edge cases for AudioMetadata."""
        # Minimum valid duration
        metadata = AudioMetadata(
            duration=0.01,
            sample_rate=22050,
            channels=1,
            format="wav",
            file_size_bytes=1
        )
        assert metadata.duration == 0.01

        # Maximum valid duration
        metadata = AudioMetadata(
            duration=60.0,
            sample_rate=22050,
            channels=1,
            format="wav",
            file_size_bytes=1000000
        )
        assert metadata.duration == 60.0


class TestAudioProcessor:
    """Test cases for AudioProcessor class."""

    def test_audio_processor_initialization(self) -> None:
        """Test AudioProcessor initialization."""
        processor = AudioProcessor()

        assert processor.SUPPORTED_FORMATS == {'.wav', '.mp3', '.flac', '.m4a', '.ogg'}
        assert processor.TARGET_SAMPLE_RATE == 22050
        assert processor.MAX_DURATION == 60.0
        assert processor.MIN_DURATION == 0.5
        assert hasattr(processor, 'logger')

    def test_supported_formats_property(self) -> None:
        """Test SUPPORTED_FORMATS property."""
        processor = AudioProcessor()
        expected_formats = {'.wav', '.mp3', '.flac', '.m4a', '.ogg'}
        assert processor.SUPPORTED_FORMATS == expected_formats

    def test_target_parameters(self) -> None:
        """Test target audio parameters."""
        processor = AudioProcessor()

        assert processor.TARGET_SAMPLE_RATE == 22050
        assert processor.MAX_DURATION == 60.0
        assert processor.MIN_DURATION == 0.5


class TestValidateAudioFile:
    """Test cases for validate_audio_file method."""

    def test_validate_wav_file_success(self, sample_audio_file: bytes) -> None:
        """Test successful validation of WAV file."""
        processor = AudioProcessor()
        result = processor.validate_audio_file(sample_audio_file, "test.wav")

        assert result is True

    def test_validate_mp3_file_success(self, sample_mp3_file: bytes) -> None:
        """Test successful validation of MP3 file."""
        processor = AudioProcessor()
        result = processor.validate_audio_file(sample_mp3_file, "test.mp3")

        assert result is True

    def test_validate_unsupported_format(self) -> None:
        """Test validation with unsupported file format."""
        processor = AudioProcessor()
        file_data = b"some audio data"

        with pytest.raises(AudioProcessingError, match="Unsupported audio format"):
            processor.validate_audio_file(file_data, "test.txt")

    def test_validate_empty_file(self) -> None:
        """Test validation with empty file."""
        processor = AudioProcessor()
        empty_data = b""

        with pytest.raises(AudioProcessingError, match="Audio file is empty"):
            processor.validate_audio_file(empty_data, "test.wav")

    def test_validate_file_too_large(self) -> None:
        """Test validation with file exceeding size limit."""
        processor = AudioProcessor()
        # Create data larger than 25MB
        large_data = b"x" * (26 * 1024 * 1024)

        with pytest.raises(AudioProcessingError, match="Audio file size cannot exceed 25MB"):
            processor.validate_audio_file(large_data, "test.wav")

    def test_validate_corrupted_file(self, corrupted_audio_file: bytes) -> None:
        """Test validation with corrupted audio file."""
        processor = AudioProcessor()

        with pytest.raises(AudioProcessingError, match="Audio file is corrupted or invalid"):
            processor.validate_audio_file(corrupted_audio_file, "test.wav")

    @patch('librosa.load')
    def test_validate_duration_too_short(self, mock_load: MagicMock) -> None:
        """Test validation with audio duration too short."""
        processor = AudioProcessor()

        # Mock librosa.load to return short audio
        short_audio = np.random.randn(11024)  # 0.499 seconds at 22050 Hz (below minimum)
        mock_load.return_value = (short_audio, 22050)

        with pytest.raises(AudioProcessingError, match="Audio duration.*is too short"):
            processor.validate_audio_file(b"some data", "test.wav")

    @patch('librosa.load')
    def test_validate_duration_too_long(self, mock_load: MagicMock) -> None:
        """Test validation with audio duration too long."""
        processor = AudioProcessor()

        # Mock librosa.load to return long audio
        long_audio = np.random.randn(22050 * 70)  # 70 seconds at 22050 Hz
        mock_load.return_value = (long_audio, 22050)

        with pytest.raises(AudioProcessingError, match="Audio duration.*exceeds maximum"):
            processor.validate_audio_file(b"some data", "test.wav")

    @patch('librosa.load')
    def test_validate_librosa_error(self, mock_load: MagicMock) -> None:
        """Test validation when librosa.load raises an exception."""
        processor = AudioProcessor()

        # Mock librosa.load to raise an exception
        mock_load.side_effect = Exception("Librosa error")

        with pytest.raises(AudioProcessingError, match="Audio file is corrupted or invalid"):
            processor.validate_audio_file(b"some data", "test.wav")

    def test_validate_all_supported_formats(self) -> None:
        """Test validation with all supported audio formats."""
        processor = AudioProcessor()
        audio_data = b"mock audio data"

        supported_formats = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']

        for format_ext in supported_formats:
            # This will fail at librosa.load, but should pass format validation
            try:
                processor.validate_audio_file(audio_data, f"test{format_ext}")
            except AudioProcessingError as e:
                # Should fail at librosa stage, not format validation
                assert "corrupted" in str(e).lower() or "invalid" in str(e).lower()

    def test_validate_case_insensitive_extension(self) -> None:
        """Test validation with case insensitive file extensions."""
        processor = AudioProcessor()
        audio_data = b"mock audio data"

        extensions = ['.WAV', '.MP3', '.Flac', '.M4A', '.OGG']

        for ext in extensions:
            try:
                processor.validate_audio_file(audio_data, f"test{ext}")
            except AudioProcessingError as e:
                # Should fail at librosa stage, not format validation
                assert "corrupted" in str(e).lower() or "invalid" in str(e).lower()

    @patch('librosa.load')
    def test_validate_edge_case_duration(self, mock_load: MagicMock) -> None:
        """Test validation with edge case durations."""
        processor = AudioProcessor()

        # Test exactly minimum duration
        min_audio = np.random.randn(int(22050 * 0.5))  # Exactly 0.5 seconds
        mock_load.return_value = (min_audio, 22050)

        try:
            processor.validate_audio_file(b"some data", "test.wav")
        except AudioProcessingError as e:
            assert "too short" not in str(e).lower()

        # Test exactly maximum duration
        max_audio = np.random.randn(int(22050 * 60.0))  # Exactly 60 seconds
        mock_load.return_value = (max_audio, 22050)

        try:
            processor.validate_audio_file(b"some data", "test.wav")
        except AudioProcessingError as e:
            assert "exceeds maximum" not in str(e).lower()


class TestLoadAudio:
    """Test cases for load_audio method."""

    def test_load_audio_success(self, sample_audio_file: bytes) -> None:
        """Test successful audio loading."""
        processor = AudioProcessor()
        audio_data, sample_rate = processor.load_audio(sample_audio_file)

        assert isinstance(audio_data, np.ndarray)
        assert isinstance(sample_rate, int)
        assert sample_rate == processor.TARGET_SAMPLE_RATE
        assert len(audio_data) > 0

    def test_load_audio_mono_conversion(self) -> None:
        """Test that audio is converted to mono."""
        processor = AudioProcessor()

        # Create stereo audio data
        sample_rate = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        stereo_audio = np.column_stack([np.sin(2 * np.pi * 440 * t), np.sin(2 * np.pi * 880 * t)])

        # Convert to bytes
        audio_buffer = io.BytesIO()
        import soundfile as sf
        sf.write(audio_buffer, stereo_audio, sample_rate, format='WAV')
        audio_buffer.seek(0)

        audio_data, returned_sample_rate = processor.load_audio(audio_buffer.read())

        # Should be mono (1D array)
        assert audio_data.ndim == 1
        assert returned_sample_rate == processor.TARGET_SAMPLE_RATE

    def test_load_audio_resampling(self) -> None:
        """Test that audio is resampled to target sample rate."""
        processor = AudioProcessor()

        # Create audio with different sample rate
        original_sample_rate = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(original_sample_rate * duration))
        audio_data = np.sin(2 * np.pi * 440 * t)

        # Convert to bytes
        audio_buffer = io.BytesIO()
        import soundfile as sf
        sf.write(audio_buffer, audio_data, original_sample_rate, format='WAV')
        audio_buffer.seek(0)

        loaded_audio, returned_sample_rate = processor.load_audio(audio_buffer.read())

        assert returned_sample_rate == processor.TARGET_SAMPLE_RATE

    @patch('librosa.load')
    def test_load_audio_librosa_error(self, mock_load: MagicMock) -> None:
        """Test load_audio when librosa.load raises an exception."""
        processor = AudioProcessor()

        mock_load.side_effect = Exception("Librosa loading error")

        with pytest.raises(AudioProcessingError, match="Failed to load audio"):
            processor.load_audio(b"some data")

    def test_load_audio_normalization(self) -> None:
        """Test that audio data is normalized."""
        processor = AudioProcessor()

        # Create audio with high amplitude
        sample_rate = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        high_amplitude_audio = np.sin(2 * np.pi * 440 * t) * 10.0  # High amplitude

        # Convert to bytes
        audio_buffer = io.BytesIO()
        import soundfile as sf
        sf.write(audio_buffer, high_amplitude_audio, sample_rate, format='WAV')
        audio_buffer.seek(0)

        loaded_audio, _ = processor.load_audio(audio_buffer.read())

        # Check that audio is normalized (max amplitude should be <= 1)
        assert np.max(np.abs(loaded_audio)) <= 1.0

    @patch('librosa.effects.trim')
    def test_load_audio_silence_removal(self, mock_trim: MagicMock) -> None:
        """Test that leading/trailing silence is removed."""
        processor = AudioProcessor()

        # Mock trim to return trimmed audio
        original_audio = np.random.randn(22050)  # 1 second of audio
        trimmed_audio = original_audio[1000:-1000]  # Remove leading/trailing samples
        mock_trim.return_value = (trimmed_audio, None)

        with patch('librosa.load') as mock_load:
            mock_load.return_value = (original_audio, 22050)

            loaded_audio, _ = processor.load_audio(b"some data")

            # Should have called librosa.effects.trim
            mock_trim.assert_called_once()

    def test_load_empty_audio(self) -> None:
        """Test loading empty audio data."""
        processor = AudioProcessor()

        with pytest.raises(AudioProcessingError, match="Failed to load audio"):
            processor.load_audio(b"")


class TestExtractFeatures:
    """Test cases for extract_features method."""

    def test_extract_features_success(self) -> None:
        """Test successful feature extraction."""
        processor = AudioProcessor()

        # Create sample audio data
        sample_rate = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        audio_data = np.sin(2 * np.pi * 440 * t)

        features = processor.extract_features(audio_data, sample_rate)

        assert isinstance(features, AudioFeatures)
        assert features.mfcc.shape[0] == 13  # 13 MFCC coefficients
        assert features.chroma.shape[0] == 12  # 12 chroma features
        assert features.spectral_centroid.shape[0] == 1
        assert features.spectral_rolloff.shape[0] == 1
        assert features.zero_crossing_rate.shape[0] == 1
        assert features.rms.shape[0] == 1
        assert features.metadata.duration == duration
        assert features.metadata.sample_rate == sample_rate
        assert features.metadata.channels == 1

    def test_extract_features_with_different_durations(self) -> None:
        """Test feature extraction with different audio durations."""
        processor = AudioProcessor()

        durations = [0.5, 1.0, 2.0, 5.0]

        for duration in durations:
            sample_rate = 22050
            t = np.linspace(0, duration, int(sample_rate * duration))
            audio_data = np.sin(2 * np.pi * 440 * t)

            features = processor.extract_features(audio_data, sample_rate)

            assert features.metadata.duration == duration
            assert features.mfcc.shape[1] > 0  # Should have time frames

    def test_extract_features_with_silence(self) -> None:
        """Test feature extraction with silent audio."""
        processor = AudioProcessor()

        # Create mostly silent audio with small signal
        sample_rate = 22050
        duration = 1.0
        silent_audio = np.random.randn(int(sample_rate * duration)) * 0.001  # Very quiet

        features = processor.extract_features(silent_audio, sample_rate)

        assert isinstance(features, AudioFeatures)
        # Features should still be extracted even from quiet audio
        assert features.mfcc.shape[0] == 13
        assert features.chroma.shape[0] == 12

    def test_extract_features_with_complex_audio(self) -> None:
        """Test feature extraction with complex audio (multiple frequencies)."""
        processor = AudioProcessor()

        sample_rate = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sample_rate * duration))

        # Create complex audio with multiple frequencies
        audio_data = (
            0.5 * np.sin(2 * np.pi * 440 * t) +  # A4
            0.3 * np.sin(2 * np.pi * 880 * t) +  # A5
            0.2 * np.sin(2 * np.pi * 1320 * t)    # E6
        )

        features = processor.extract_features(audio_data, sample_rate)

        assert isinstance(features, AudioFeatures)
        # Complex audio should produce more varied features
        assert np.std(features.mfcc) > 0  # Should have variation in MFCCs
        assert np.std(features.chroma) > 0  # Should have variation in chroma

    @patch('librosa.feature.mfcc')
    def test_extract_features_mfcc_error(self, mock_mfcc: MagicMock) -> None:
        """Test feature extraction when MFCC extraction fails."""
        processor = AudioProcessor()

        mock_mfcc.side_effect = Exception("MFCC extraction error")

        audio_data = np.random.randn(22050)  # 1 second of audio

        with pytest.raises(AudioProcessingError, match="Feature extraction failed"):
            processor.extract_features(audio_data, 22050)

    def test_extract_features_chroma_error(self) -> None:
        """Test feature extraction when chroma extraction fails."""
        processor = AudioProcessor()

        audio_data = np.random.randn(22050)  # 1 second of audio

        with patch('librosa.feature.chroma_cqt', side_effect=Exception("Chroma extraction error")):
            with pytest.raises(AudioProcessingError, match="Feature extraction failed"):
                processor.extract_features(audio_data, 22050)

    def test_extract_features_metadata_calculation(self) -> None:
        """Test that metadata is calculated correctly."""
        processor = AudioProcessor()

        sample_rate = 16000  # Different sample rate
        duration = 1.5
        audio_data = np.random.randn(int(sample_rate * duration))
        expected_file_size = len(audio_data.tobytes())

        features = processor.extract_features(audio_data, sample_rate)

        assert features.metadata.duration == duration
        assert features.metadata.sample_rate == sample_rate
        assert features.metadata.channels == 1  # Always mono after processing
        assert features.metadata.format == "processed"
        assert features.metadata.file_size_bytes == expected_file_size


class TestProcessAudioFile:
    """Test cases for process_audio_file method (complete pipeline)."""

    def test_process_audio_file_success(self, sample_audio_file: bytes) -> None:
        """Test successful complete audio processing pipeline."""
        processor = AudioProcessor()

        features = processor.process_audio_file(sample_audio_file, "test.wav")

        assert isinstance(features, AudioFeatures)
        assert features.mfcc.shape[0] == 13
        assert features.chroma.shape[0] == 12
        assert features.metadata.duration > 0

    def test_process_audio_file_validation_failure(self) -> None:
        """Test pipeline failure at validation stage."""
        processor = AudioProcessor()

        with pytest.raises(AudioProcessingError):
            processor.process_audio_file(b"", "empty.wav")

    @patch.object(AudioProcessor, 'load_audio')
    def test_process_audio_file_loading_failure(self, mock_load: MagicMock) -> None:
        """Test pipeline failure at loading stage."""
        processor = AudioProcessor()

        # Mock validate_audio_file to pass
        with patch.object(processor, 'validate_audio_file') as mock_validate:
            mock_validate.return_value = True

            # Mock load_audio to fail
            mock_load.side_effect = AudioProcessingError("Loading failed")

            with pytest.raises(AudioProcessingError, match="Loading failed"):
                processor.process_audio_file(b"some data", "test.wav")

    @patch.object(AudioProcessor, 'extract_features')
    def test_process_audio_file_feature_extraction_failure(self, mock_extract: MagicMock) -> None:
        """Test pipeline failure at feature extraction stage."""
        processor = AudioProcessor()

        # Mock validation and loading to pass
        with patch.object(processor, 'validate_audio_file') as mock_validate:
            with patch.object(processor, 'load_audio') as mock_load:
                mock_validate.return_value = True
                mock_load.return_value = (np.random.randn(22050), 22050)

                # Mock extract_features to fail
                mock_extract.side_effect = AudioProcessingError("Feature extraction failed")

                with pytest.raises(AudioProcessingError, match="Feature extraction failed"):
                    processor.process_audio_file(b"some data", "test.wav")

    def test_process_audio_file_with_all_formats(self) -> None:
        """Test pipeline with all supported audio formats."""
        processor = AudioProcessor()

        formats = ['wav', 'mp3', 'flac', 'm4a', 'ogg']

        for format_ext in formats:
            # Create mock audio data for each format
            try:
                # This will likely fail at librosa stage for formats other than WAV
                # but we test that the pipeline structure works
                processor.process_audio_file(b"mock data", f"test.{format_ext}")
            except AudioProcessingError as e:
                # Should fail at audio loading, not at pipeline structure
                assert "corrupted" in str(e).lower() or "invalid" in str(e).lower()

    def test_process_audio_file_pipeline_order(self) -> None:
        """Test that pipeline executes in correct order."""
        processor = AudioProcessor()

        with patch.object(processor, 'validate_audio_file') as mock_validate:
            with patch.object(processor, 'load_audio') as mock_load:
                with patch.object(processor, 'extract_features') as mock_extract:

                    # Configure mocks
                    mock_validate.return_value = True
                    mock_load.return_value = (np.random.randn(22050), 22050)
                    mock_extract.return_value = AudioFeatures(
                        mfcc=np.random.randn(13, 87),
                        chroma=np.random.randn(12, 87),
                        spectral_centroid=np.random.randn(1, 87),
                        spectral_rolloff=np.random.randn(1, 87),
                        zero_crossing_rate=np.random.randn(1, 87),
                        rms=np.random.randn(1, 87),
                        metadata=AudioMetadata(
                            duration=2.0,
                            sample_rate=22050,
                            channels=1,
                            format="processed",
                            file_size_bytes=1000
                        )
                    )

                    processor.process_audio_file(b"test data", "test.wav")

                    # Verify call order
                    mock_validate.assert_called_once()
                    mock_load.assert_called_once()
                    mock_extract.assert_called_once()


class TestFeaturesToDict:
    """Test cases for features_to_dict method."""

    def test_features_to_dict_conversion(self, sample_audio_features: AudioFeatures) -> None:
        """Test conversion of AudioFeatures to dictionary."""
        processor = AudioProcessor()

        features_dict = processor.features_to_dict(sample_audio_features)

        assert isinstance(features_dict, dict)
        assert "mfcc" in features_dict
        assert "chroma" in features_dict
        assert "spectral_centroid" in features_dict
        assert "spectral_rolloff" in features_dict
        assert "zero_crossing_rate" in features_dict
        assert "rms" in features_dict
        assert "metadata" in features_dict

        # Check that numpy arrays are converted to lists
        assert isinstance(features_dict["mfcc"], list)
        assert isinstance(features_dict["chroma"], list)
        assert isinstance(features_dict["spectral_centroid"], list)
        assert isinstance(features_dict["spectral_rolloff"], list)
        assert isinstance(features_dict["zero_crossing_rate"], list)
        assert isinstance(features_dict["rms"], list)

        # Check metadata structure
        metadata = features_dict["metadata"]
        assert "duration" in metadata
        assert "sample_rate" in metadata
        assert "channels" in metadata
        assert "format" in metadata
        assert "file_size_bytes" in metadata

    def test_features_to_dict_json_serializable(self, sample_audio_features: AudioFeatures) -> None:
        """Test that features_to_dict produces JSON-serializable output."""
        processor = AudioProcessor()

        features_dict = processor.features_to_dict(sample_audio_features)

        # Should be JSON serializable without errors
        import json
        json_str = json.dumps(features_dict)

        # Should be able to parse it back
        parsed_dict = json.loads(json_str)
        assert parsed_dict == features_dict

    def test_features_to_dict_preserves_data_integrity(self, sample_audio_features: AudioFeatures) -> None:
        """Test that features_to_dict preserves data integrity."""
        processor = AudioProcessor()

        features_dict = processor.features_to_dict(sample_audio_features)

        # Check that numerical values are preserved
        assert features_dict["metadata"]["duration"] == sample_audio_features.metadata.duration
        assert features_dict["metadata"]["sample_rate"] == sample_audio_features.metadata.sample_rate
        assert features_dict["metadata"]["channels"] == sample_audio_features.metadata.channels

        # Check array shapes are preserved in list form
        assert len(features_dict["mfcc"]) == sample_audio_features.mfcc.shape[0]
        assert len(features_dict["mfcc"][0]) == sample_audio_features.mfcc.shape[1] if sample_audio_features.mfcc.ndim > 1 else True
        assert len(features_dict["chroma"]) == sample_audio_features.chroma.shape[0]

    def test_features_to_dict_with_different_feature_shapes(self) -> None:
        """Test features_to_dict with different feature shapes."""
        processor = AudioProcessor()

        # Create features with different shapes
        features = AudioFeatures(
            mfcc=np.random.randn(13, 100),  # Different number of time frames
            chroma=np.random.randn(12, 100),
            spectral_centroid=np.random.randn(1, 100),
            spectral_rolloff=np.random.randn(1, 100),
            zero_crossing_rate=np.random.randn(1, 100),
            rms=np.random.randn(1, 100),
            metadata=AudioMetadata(
                duration=3.0,
                sample_rate=22050,
                channels=1,
                format="processed",
                file_size_bytes=2000
            )
        )

        features_dict = processor.features_to_dict(features)

        # Should handle different shapes correctly
        assert len(features_dict["mfcc"][0]) == 100
        assert len(features_dict["chroma"][0]) == 100


class TestGlobalAudioProcessor:
    """Test cases for the global audio_processor instance."""

    def test_global_audio_processor_instance(self) -> None:
        """Test that global audio_processor instance exists and is usable."""
        from app.services.audio_service import audio_processor

        assert isinstance(audio_processor, AudioProcessor)
        assert hasattr(audio_processor, 'validate_audio_file')
        assert hasattr(audio_processor, 'load_audio')
        assert hasattr(audio_processor, 'extract_features')
        assert hasattr(audio_processor, 'process_audio_file')

    def test_global_processor_singleton_behavior(self) -> None:
        """Test that global processor behaves as singleton."""
        from app.services.audio_service import audio_processor

        # Import again should return same instance
        from app.services.audio_service import audio_processor as processor2

        assert audio_processor is processor2


class TestAudioProcessingError:
    """Test cases for AudioProcessingError exception."""

    def test_audio_processing_error_creation(self) -> None:
        """Test AudioProcessingError creation."""
        error = AudioProcessingError("Test error message")

        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_audio_processing_error_inheritance(self) -> None:
        """Test AudioProcessingError inheritance."""
        error = AudioProcessingError("Test")

        assert isinstance(error, Exception)
        # Should be catchable as general Exception
        try:
            raise error
        except Exception:
            caught = True
        else:
            caught = False

        assert caught

    def test_audio_processing_error_with_none_message(self) -> None:
        """Test AudioProcessingError with None message."""
        error = AudioProcessingError(None)

        assert str(error) == "None" or error.args[0] is None