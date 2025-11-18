"""
Tests for the Streamlit frontend audio processing utilities
"""

import pytest
import numpy as np
import librosa
import soundfile as sf
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from utils.audio_utils import AudioProcessor


class TestAudioProcessor:
    """Test cases for AudioProcessor class"""

    @pytest.fixture
    def audio_processor(self):
        """Create AudioProcessor instance for testing"""
        return AudioProcessor()

    @pytest.fixture
    def sample_audio_data(self):
        """Generate sample audio data for testing"""
        sample_rate = 22050
        duration = 2.0
        frequency = 440  # A4 note

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t) * 0.3

        return audio_data, sample_rate

    @pytest.fixture
    def sample_stereo_audio_data(self):
        """Generate sample stereo audio data for testing"""
        sample_rate = 22050
        duration = 2.0
        frequency = 440

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        mono_data = np.sin(2 * np.pi * frequency * t) * 0.3
        # Create stereo by duplicating with slight phase difference
        stereo_data = np.array([mono_data, mono_data * 0.8])

        return stereo_data, sample_rate

    @pytest.fixture
    def temp_audio_file(self, sample_audio_data):
        """Create temporary audio file"""
        audio_data, sample_rate = sample_audio_data
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, audio_data, sample_rate)
        temp_file.close()

        yield temp_file.name

        os.unlink(temp_file.name)

    @pytest.fixture
    def temp_mp3_file(self, sample_audio_data):
        """Create temporary MP3 file"""
        audio_data, sample_rate = sample_audio_data
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)

        # Write as WAV first (simplified approach)
        sf.write(temp_file.name, audio_data, sample_rate)
        temp_file.close()

        yield temp_file.name

        os.unlink(temp_file.name)

    @pytest.fixture
    def corrupted_audio_file(self):
        """Create corrupted audio file"""
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.write(b"This is not a valid WAV file content")
        temp_file.close()

        yield temp_file.name

        os.unlink(temp_file.name)

    def test_init(self, audio_processor):
        """Test AudioProcessor initialization"""
        assert audio_processor is not None
        assert hasattr(audio_processor, 'target_sample_rate')
        assert hasattr(audio_processor, 'max_duration')

    def test_load_audio_valid_wav(self, audio_processor, temp_audio_file):
        """Test loading valid WAV file"""
        with open(temp_audio_file, 'rb') as f:
            audio_data, sample_rate = audio_processor.load_audio(f)

        assert isinstance(audio_data, np.ndarray)
        assert audio_data.ndim == 1  # Should be mono
        assert sample_rate == audio_processor.target_sample_rate
        assert len(audio_data) > 0

    def test_load_audio_stereo_to_mono(self, audio_processor, sample_stereo_audio_data):
        """Test loading stereo audio and converting to mono"""
        stereo_data, original_sr = sample_stereo_audio_data

        # Create temporary stereo file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, stereo_data.T, original_sr)  # Transpose for soundfile
        temp_file.close()

        try:
            with open(temp_file.name, 'rb') as f:
                audio_data, sample_rate = audio_processor.load_audio(f)

            assert audio_data.ndim == 1  # Should be converted to mono
            assert sample_rate == audio_processor.target_sample_rate
        finally:
            os.unlink(temp_file.name)

    def test_load_audio_resampling(self, audio_processor):
        """Test audio resampling to target sample rate"""
        # Create audio with different sample rate
        original_sr = 44100
        duration = 1.0
        frequency = 440

        t = np.linspace(0, duration, int(original_sr * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t) * 0.3

        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, audio_data, original_sr)
        temp_file.close()

        try:
            with open(temp_file.name, 'rb') as f:
                audio_data, sample_rate = audio_processor.load_audio(f)

            assert sample_rate == audio_processor.target_sample_rate
            assert len(audio_data) > 0
        finally:
            os.unlink(temp_file.name)

    def test_load_audio_corrupted_file(self, audio_processor, corrupted_audio_file):
        """Test loading corrupted audio file raises error"""
        with open(corrupted_audio_file, 'rb') as f:
            with pytest.raises(Exception):
                audio_processor.load_audio(f)

    def test_validate_audio_file_valid_wav(self, audio_processor, temp_audio_file):
        """Test validating valid WAV file"""
        with open(temp_audio_file, 'rb') as f:
            file_data = f.read()

        result = audio_processor.validate_audio_file(file_data, "test.wav")

        assert result is True

    def test_validate_audio_file_valid_mp3(self, audio_processor, temp_mp3_file):
        """Test validating valid MP3 file"""
        with open(temp_mp3_file, 'rb') as f:
            file_data = f.read()

        result = audio_processor.validate_audio_file(file_data, "test.mp3")

        assert result is True

    def test_validate_audio_file_unsupported_format(self, audio_processor):
        """Test validating unsupported audio format"""
        file_data = b"Fake audio content"

        with pytest.raises(ValueError, match="Unsupported audio format"):
            audio_processor.validate_audio_file(file_data, "test.xyz")

    def test_validate_audio_file_too_large(self, audio_processor):
        """Test validating audio file that's too large"""
        # Create fake large file data
        large_data = b"x" * (30 * 1024 * 1024)  # 30MB

        with pytest.raises(ValueError, match="Audio file size cannot exceed"):
            audio_processor.validate_audio_file(large_data, "test.wav")

    def test_validate_audio_file_empty(self, audio_processor):
        """Test validating empty audio file"""
        with pytest.raises(ValueError, match="Audio file is empty"):
            audio_processor.validate_audio_file(b"", "test.wav")

    def test_validate_audio_file_invalid_content(self, audio_processor, corrupted_audio_file):
        """Test validating file with invalid content"""
        with open(corrupted_audio_file, 'rb') as f:
            file_data = f.read()

        with pytest.raises(ValueError, match="Audio file is corrupted or invalid"):
            audio_processor.validate_audio_file(file_data, "test.wav")

    def test_validate_audio_file_too_short(self, audio_processor):
        """Test validating audio file that's too short"""
        # Create very short audio
        sample_rate = 22050
        duration = 0.1  # 100ms (too short)
        frequency = 440

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t) * 0.3

        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, audio_data, sample_rate)
        temp_file.close()

        try:
            with open(temp_file.name, 'rb') as f:
                file_data = f.read()

            with pytest.raises(ValueError, match="Audio duration.*is too short"):
                audio_processor.validate_audio_file(file_data, "test.wav")
        finally:
            os.unlink(temp_file.name)

    def test_validate_audio_file_too_long(self, audio_processor):
        """Test validating audio file that's too long"""
        # Create long audio
        sample_rate = 22050
        duration = 120.0  # 2 minutes (too long)
        frequency = 440

        t = np.linspace(0, duration, int(sample_rate * duration), False)
        audio_data = np.sin(2 * np.pi * frequency * t) * 0.3

        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, audio_data, sample_rate)
        temp_file.close()

        try:
            with open(temp_file.name, 'rb') as f:
                file_data = f.read()

            with pytest.raises(ValueError, match="Audio duration.*exceeds maximum"):
                audio_processor.validate_audio_file(file_data, "test.wav")
        finally:
            os.unlink(temp_file.name)

    def test_get_audio_info_valid_file(self, audio_processor, temp_audio_file):
        """Test getting audio info for valid file"""
        with open(temp_audio_file, 'rb') as f:
            file_data = f.read()

        info = audio_processor.get_audio_info(file_data, "test.wav")

        assert "duration" in info
        assert "sample_rate" in info
        assert "channels" in info
        assert "format" in info
        assert "file_size" in info
        assert info["duration"] > 0
        assert info["sample_rate"] > 0
        assert info["file_size"] > 0

    def test_get_audio_info_invalid_file(self, audio_processor, corrupted_audio_file):
        """Test getting audio info for invalid file"""
        with open(corrupted_audio_file, 'rb') as f:
            file_data = f.read()

        with pytest.raises(ValueError):
            audio_processor.get_audio_info(file_data, "test.wav")

    def test_preprocess_audio_normalization(self, audio_processor, sample_audio_data):
        """Test audio normalization during preprocessing"""
        audio_data, sample_rate = sample_audio_data

        # Create unnormally loud audio
        loud_audio = audio_data * 10.0

        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, loud_audio, sample_rate)
        temp_file.close()

        try:
            with open(temp_file.name, 'rb') as f:
                processed_audio, processed_sr = audio_processor.load_audio(f)

            # Check that audio is normalized (peak amplitude should be <= 1.0)
            peak_amplitude = np.max(np.abs(processed_audio))
            assert peak_amplitude <= 1.0
        finally:
            os.unlink(temp_file.name)

    def test_preprocess_audio_silence_removal(self, audio_processor):
        """Test silence removal during preprocessing"""
        sample_rate = 22050
        duration = 2.0

        # Create audio with silence at beginning and end
        silence_samples = int(0.2 * sample_rate)  # 200ms of silence
        audio_samples = int(1.6 * sample_rate)   # 1.6s of actual audio

        # Create signal
        t = np.linspace(0, 1.6, audio_samples)
        signal = np.sin(2 * np.pi * 440 * t) * 0.3

        # Add silence
        audio_with_silence = np.concatenate([
            np.zeros(silence_samples),  # Leading silence
            signal,
            np.zeros(silence_samples)   # Trailing silence
        ])

        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, audio_with_silence, sample_rate)
        temp_file.close()

        try:
            with open(temp_file.name, 'rb') as f:
                processed_audio, processed_sr = audio_processor.load_audio(f)

            # Check that silence was removed (duration should be shorter)
            expected_duration = 1.6  # Should be close to 1.6 seconds
            actual_duration = len(processed_audio) / processed_sr

            assert abs(actual_duration - expected_duration) < 0.2  # Allow some tolerance
        finally:
            os.unlink(temp_file.name)

    def test_preprocess_audio_mono_conversion(self, audio_processor, sample_stereo_audio_data):
        """Test mono conversion during preprocessing"""
        stereo_data, original_sr = sample_stereo_audio_data

        # Create temporary stereo file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        sf.write(temp_file.name, stereo_data.T, original_sr)
        temp_file.close()

        try:
            with open(temp_file.name, 'rb') as f:
                processed_audio, processed_sr = audio_processor.load_audio(f)

            # Should be mono
            assert processed_audio.ndim == 1
        finally:
            os.unlink(temp_file.name)

    @patch('streamlit.error')
    def test_load_audio_with_streamlit_error(self, mock_stlit_error, audio_processor, corrupted_audio_file):
        """Test that streamlit.error is called for invalid audio"""
        with open(corrupted_audio_file, 'rb') as f:
            audio_data, sample_rate = audio_processor.load_audio(f)

        # Should call streamlit.error with appropriate message
        mock_stlit_error.assert_called_once()
        assert "error" in mock_stlit_error.call_args[0][0].lower()

    def test_supported_formats(self, audio_processor):
        """Test supported audio formats"""
        expected_formats = ['wav', 'mp3', 'flac', 'm4a']
        assert hasattr(audio_processor, 'supported_formats')
        # Check that expected formats are in supported formats
        for fmt in expected_formats:
            assert fmt in audio_processor.supported_formats

    def test_max_duration_limit(self, audio_processor):
        """Test maximum duration limit"""
        assert hasattr(audio_processor, 'max_duration')
        assert audio_processor.max_duration > 0
        # Should be reasonable (e.g., <= 300 seconds)
        assert audio_processor.max_duration <= 300

    def test_max_file_size_limit(self, audio_processor):
        """Test maximum file size limit"""
        assert hasattr(audio_processor, 'max_file_size')
        assert audio_processor.max_file_size > 0
        # Should be reasonable (e.g., <= 100MB)
        assert audio_processor.max_file_size <= 100 * 1024 * 1024

    def test_complete_processing_pipeline(self, audio_processor, temp_audio_file):
        """Test complete audio processing pipeline"""
        with open(temp_audio_file, 'rb') as f:
            file_data = f.read()

        # Step 1: Validate
        assert audio_processor.validate_audio_file(file_data, "test.wav")

        # Step 2: Get info
        info = audio_processor.get_audio_info(file_data, "test.wav")
        assert info["duration"] > 0

        # Step 3: Load and process
        with open(temp_audio_file, 'rb') as f:
            audio_data, sample_rate = audio_processor.load_audio(f)

        assert isinstance(audio_data, np.ndarray)
        assert sample_rate == audio_processor.target_sample_rate

        # Verify all steps completed successfully
        assert len(audio_data) > 0
        assert audio_data.ndim == 1  # Should be mono