"""
Audio processing service for speech emotion recognition.

This service handles audio file validation, preprocessing, and feature extraction
using librosa for audio analysis and ML model input preparation.
"""

import base64
import io
import logging
from pathlib import Path
from typing import BinaryIO, Tuple, Optional, Dict, Any

import librosa
import numpy as np
import soundfile as sf
from pydantic import BaseModel, field_validator, ConfigDict

logger = logging.getLogger(__name__)


class AudioMetadata(BaseModel):
    """Metadata model for audio files."""
    duration: float
    sample_rate: int
    channels: int
    format: str
    file_size_bytes: int

    @field_validator('duration')
    @classmethod
    def validate_duration(cls, v):
        if v <= 0:
            raise ValueError("Duration must be positive")
        if v > 60:  # Max 60 seconds as per requirements
            raise ValueError("Audio duration cannot exceed 60 seconds")
        return v

    @field_validator('sample_rate')
    @classmethod
    def validate_sample_rate(cls, v):
        if v <= 0:
            raise ValueError("Sample rate must be positive")
        return v


class AudioFeatures(BaseModel):
    """Extracted audio features for emotion recognition."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    mfcc: np.ndarray
    chroma: np.ndarray
    spectral_centroid: np.ndarray
    spectral_rolloff: np.ndarray
    zero_crossing_rate: np.ndarray
    rms: np.ndarray
    metadata: AudioMetadata


class AudioProcessingError(Exception):
    """Custom exception for audio processing errors."""
    pass


class AudioProcessor:
    """
    Audio processing service for speech emotion recognition.

    Handles audio validation, preprocessing, and feature extraction
    using librosa and soundfile.
    """

    # Supported audio formats
    SUPPORTED_FORMATS = {'.wav', '.mp3', '.flac', '.m4a', '.ogg'}

    # Target audio parameters
    TARGET_SAMPLE_RATE = 22050  # Standard for speech processing
    MAX_DURATION = 60.0  # Maximum duration in seconds
    MIN_DURATION = 0.5  # Minimum duration in seconds

    def __init__(self):
        """Initialize the audio processor."""
        self.logger = logging.getLogger(__name__)

    def validate_audio_file(self, file_data: bytes, filename: str) -> bool:
        """
        Validate uploaded audio file.

        Args:
            file_data: Raw audio file data
            filename: Original filename

        Returns:
            True if valid

        Raises:
            AudioProcessingError: If validation fails
        """
        try:
            # Check file extension
            file_ext = Path(filename).suffix.lower()
            if file_ext not in self.SUPPORTED_FORMATS:
                raise AudioProcessingError(
                    f"Unsupported audio format: {file_ext}. "
                    f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
                )

            # Check file size (max 25MB)
            file_size = len(file_data)
            if file_size > 25 * 1024 * 1024:
                raise AudioProcessingError("Audio file size cannot exceed 25MB")

            if file_size == 0:
                raise AudioProcessingError("Audio file is empty")

            # Try to load audio to verify it's not corrupted
            try:
                with io.BytesIO(file_data) as audio_file:
                    audio_data, sr = librosa.load(audio_file, sr=None)
            except Exception as e:
                raise AudioProcessingError(f"Audio file is corrupted or invalid: {str(e)}")

            # Check duration
            duration = len(audio_data) / sr
            if duration < self.MIN_DURATION:
                raise AudioProcessingError(
                    f"Audio duration {duration:.2f}s is too short. "
                    f"Minimum duration: {self.MIN_DURATION}s"
                )

            if duration > self.MAX_DURATION:
                raise AudioProcessingError(
                    f"Audio duration {duration:.2f}s exceeds maximum allowed. "
                    f"Maximum duration: {self.MAX_DURATION}s"
                )

            return True

        except AudioProcessingError:
            raise
        except Exception as e:
            raise AudioProcessingError(f"Audio validation failed: {str(e)}")

    def load_audio(self, file_data: bytes) -> Tuple[np.ndarray, int]:
        """
        Load and preprocess audio data.

        Args:
            file_data: Raw audio file data

        Returns:
            Tuple of (audio_data, sample_rate)

        Raises:
            AudioProcessingError: If loading fails
        """
        try:
            with io.BytesIO(file_data) as audio_file:
                # Load audio with target sample rate
                audio_data, sample_rate = librosa.load(
                    audio_file,
                    sr=self.TARGET_SAMPLE_RATE,
                    mono=True  # Convert to mono
                )

            # Normalize audio data
            if len(audio_data) > 0:
                # Normalize to [-1, 1] range
                audio_data = librosa.util.normalize(audio_data)

                # Remove leading/trailing silence
                audio_data, _ = librosa.effects.trim(
                    audio_data,
                    top_db=20
                )

            self.logger.info(
                f"Audio loaded successfully: duration={len(audio_data)/sample_rate:.2f}s, "
                f"sample_rate={sample_rate}, samples={len(audio_data)}"
            )

            return audio_data, sample_rate

        except Exception as e:
            raise AudioProcessingError(f"Failed to load audio: {str(e)}")

    def extract_features(self, audio_data: np.ndarray, sample_rate: int) -> AudioFeatures:
        """
        Extract audio features for emotion recognition.

        Args:
            audio_data: Preprocessed audio data
            sample_rate: Sample rate of the audio

        Returns:
            AudioFeatures object with extracted features

        Raises:
            AudioProcessingError: If feature extraction fails
        """
        try:
            # Calculate metadata
            duration = len(audio_data) / sample_rate

            metadata = AudioMetadata(
                duration=duration,
                sample_rate=sample_rate,
                channels=1,  # Always mono after preprocessing
                format="processed",
                file_size_bytes=len(audio_data.tobytes())
            )

            # Extract MFCC features (most important for speech emotion)
            mfcc = librosa.feature.mfcc(
                y=audio_data,
                sr=sample_rate,
                n_mfcc=13,  # Standard number of MFCC coefficients
                n_fft=2048,
                hop_length=512
            )

            # Extract chroma features using CQT to avoid caching issues
            chroma = librosa.feature.chroma_cqt(
                y=audio_data,
                sr=sample_rate,
                hop_length=512
            )

            # Extract spectral features
            spectral_centroid = librosa.feature.spectral_centroid(
                y=audio_data,
                sr=sample_rate
            )

            spectral_rolloff = librosa.feature.spectral_rolloff(
                y=audio_data,
                sr=sample_rate
            )

            # Extract temporal features
            zero_crossing_rate = librosa.feature.zero_crossing_rate(audio_data)
            rms = librosa.feature.rms(y=audio_data)

            features = AudioFeatures(
                mfcc=mfcc,
                chroma=chroma,
                spectral_centroid=spectral_centroid,
                spectral_rolloff=spectral_rolloff,
                zero_crossing_rate=zero_crossing_rate,
                rms=rms,
                metadata=metadata
            )

            self.logger.info(
                f"Features extracted successfully: "
                f"MFCC shape={mfcc.shape}, "
                f"Chroma shape={chroma.shape}, "
                f"Duration={duration:.2f}s"
            )

            return features

        except Exception as e:
            raise AudioProcessingError(f"Feature extraction failed: {str(e)}")

    def process_audio_file(self, file_data: bytes, filename: str) -> AudioFeatures:
        """
        Complete audio processing pipeline: validation -> loading -> feature extraction.

        Args:
            file_data: Raw audio file data
            filename: Original filename

        Returns:
            AudioFeatures object with extracted features

        Raises:
            AudioProcessingError: If any step in the pipeline fails
        """
        try:
            # Step 1: Validate audio file
            self.validate_audio_file(file_data, filename)

            # Step 2: Load and preprocess audio
            audio_data, sample_rate = self.load_audio(file_data)

            # Step 3: Extract features
            features = self.extract_features(audio_data, sample_rate)

            self.logger.info(f"Audio processing completed successfully for {filename}")
            return features

        except AudioProcessingError:
            raise
        except Exception as e:
            raise AudioProcessingError(f"Audio processing pipeline failed: {str(e)}")

    def audio_to_base64(self, file_data: bytes, filename: str) -> Tuple[str, int]:
        """
        Convert audio file data to base64 string for SageMaker endpoint.

        Args:
            file_data: Raw audio file data
            filename: Original filename

        Returns:
            Tuple of (base64_encoded_string, sample_rate)

        Raises:
            AudioProcessingError: If conversion fails
        """
        try:
            # Validate file first
            self.validate_audio_file(file_data, filename)

            # Load audio with original sample rate to preserve it
            with io.BytesIO(file_data) as audio_file:
                audio_data, sample_rate = librosa.load(audio_file, sr=None, mono=True)

            # Convert to float32 if needed
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            # Create WAV buffer
            buffer = io.BytesIO()
            sf.write(buffer, audio_data, sample_rate, format='WAV')
            buffer.seek(0)

            # Encode to base64
            audio_base64 = base64.b64encode(buffer.read()).decode('utf-8')

            if not audio_base64:
                raise AudioProcessingError("Failed to convert audio to base64")

            self.logger.info(
                f"Audio converted to base64 successfully: {filename}, "
                f"sample_rate={sample_rate}, size={len(audio_base64)} chars"
            )

            return audio_base64, sample_rate

        except AudioProcessingError:
            raise
        except Exception as e:
            raise AudioProcessingError(f"Failed to convert audio to base64: {str(e)}")

    def features_to_dict(self, features: AudioFeatures) -> Dict[str, Any]:
        """
        Convert AudioFeatures object to dictionary for JSON serialization.

        Args:
            features: AudioFeatures object

        Returns:
            Dictionary representation of features
        """
        return {
            "mfcc": features.mfcc.tolist(),
            "chroma": features.chroma.tolist(),
            "spectral_centroid": features.spectral_centroid.tolist(),
            "spectral_rolloff": features.spectral_rolloff.tolist(),
            "zero_crossing_rate": features.zero_crossing_rate.tolist(),
            "rms": features.rms.tolist(),
            "metadata": {
                "duration": features.metadata.duration,
                "sample_rate": features.metadata.sample_rate,
                "channels": features.metadata.channels,
                "format": features.metadata.format,
                "file_size_bytes": features.metadata.file_size_bytes
            }
        }


# Global audio processor instance
audio_processor = AudioProcessor()