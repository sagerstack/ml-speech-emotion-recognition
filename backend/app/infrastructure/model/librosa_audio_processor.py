"""Librosa-based audio processor implementation."""

import io

import numpy as np

from app.domain.model.entities.raw_audio import RawAudio
from app.domain.model.exceptions.invalid_audio_error import InvalidAudioError
from app.domain.model.exceptions.prediction_failed_error import PredictionFailedError
from app.domain.model.services.audio_processor import AudioProcessor
from app.domain.model.value_objects.audio_metadata import AudioMetadata
from models.v4.feature_extractor import (
    extract_features as v4_extract_features,
    extract_features_with_audio_data as v4_extract_with_audio_data,
)
from app.infrastructure.observability.logging import get_logger


class LibrosaAudioProcessor(AudioProcessor):
    """Librosa-based implementation of AudioProcessor.

    This implementation uses librosa for audio processing and feature extraction.
    It delegates to the v4 feature extractor for extracting the 210 features
    required by the v4 model.

    The implementation follows clean architecture principles:
    - Depends on domain abstractions (AudioProcessor interface)
    - Implements infrastructure concerns (librosa usage)
    - Handles error translation from infrastructure to domain exceptions
    """

    MIN_AUDIO_DURATION = 0.5  # Minimum duration in seconds

    def __init__(self):
        """Initialize LibrosaAudioProcessor."""
        self.logger = get_logger(__name__)

    def extract_features(self, audio: RawAudio) -> np.ndarray:
        """Extract 210 features from raw audio using v4 feature extractor.

        Args:
            audio: Raw audio data

        Returns:
            Feature vector as numpy array with shape (210,)

        Raises:
            InvalidAudioError: If audio cannot be processed
            PredictionFailedError: If feature extraction fails
        """
        self.logger.debug(
            "Starting feature extraction",
            filename=audio.filename,
            audio_size_bytes=len(audio.bytes)
        )

        try:
            # Validate audio first
            self.validate_audio(audio)

            # Extract features using v4 feature extractor
            features = v4_extract_features(audio.bytes, audio.filename)

            if features.shape[0] != 210:
                self.logger.error(
                    "Feature extraction returned incorrect number of features",
                    expected=210,
                    actual=features.shape[0]
                )
                raise PredictionFailedError(f"Expected 210 features, got {features.shape[0]}")

            self.logger.debug(
                "Feature extraction completed successfully",
                filename=audio.filename,
                feature_count=features.shape[0]
            )

            return features

        except (InvalidAudioError, PredictionFailedError):
            # Re-raise domain exceptions as-is
            raise
        except ValueError as e:
            # Convert librosa/feature extraction errors to domain exceptions
            self.logger.error(
                "Feature extraction failed",
                filename=audio.filename,
                error=str(e)
            )
            raise PredictionFailedError(f"Failed to extract features: {str(e)}")
        except Exception as e:
            # Catch all other errors and convert to domain exceptions
            self.logger.error(
                "Unexpected error during feature extraction",
                filename=audio.filename,
                error=str(e)
            )
            raise PredictionFailedError(f"Unexpected error during feature extraction: {str(e)}")

    def get_audio_metadata(self, audio: RawAudio) -> AudioMetadata:
        """Extract metadata from raw audio.

        Args:
            audio: Raw audio data

        Returns:
            AudioMetadata with duration, sample rate, and channels

        Raises:
            InvalidAudioError: If audio cannot be analyzed
        """
        try:
            import soundfile as sf

            # Load audio to get metadata
            audio_buffer = io.BytesIO(audio.bytes)

            # Use soundfile to get basic metadata without loading full audio
            with sf.SoundFile(audio_buffer) as sound_file:
                sample_rate = sound_file.samplerate
                frames = len(sound_file)
                channels = sound_file.channels
                duration = frames / sample_rate

            return AudioMetadata(
                duration_seconds=duration,
                sample_rate=sample_rate,
                channels=channels,
            )

        except Exception as e:
            raise InvalidAudioError(f"Failed to extract audio metadata: {str(e)}")

    def validate_audio(self, audio: RawAudio) -> bool:
        """Validate that audio can be processed.

        Performs validation checks:
        - Audio is not empty
        - Audio can be loaded by librosa
        - Audio has sufficient duration

        Args:
            audio: Raw audio data

        Returns:
            True if audio is valid for processing

        Raises:
            InvalidAudioError: If audio is invalid with details about why
        """
        # Check empty audio
        if len(audio.bytes) == 0:
            self.logger.warning("Audio validation failed: empty audio data", filename=audio.filename)
            raise InvalidAudioError("Audio data is empty")

        try:
            import librosa

            # Try to load audio
            audio_buffer = io.BytesIO(audio.bytes)
            y, sr = librosa.load(audio_buffer, duration=2.5, offset=0.6)

            # Check if audio was loaded
            if y is None or len(y) == 0:
                self.logger.warning("Audio validation failed: could not load", filename=audio.filename)
                raise InvalidAudioError("Audio data could not be loaded")

            # Check duration after trimming
            y_trimmed, _ = librosa.effects.trim(y, top_db=20)

            if len(y_trimmed) == 0:
                self.logger.warning("Audio validation failed: empty after trimming", filename=audio.filename)
                raise InvalidAudioError("Audio is empty after trimming silence")

            duration = len(y_trimmed) / sr
            if duration < self.MIN_AUDIO_DURATION:
                self.logger.warning(
                    "Audio validation failed: duration too short",
                    filename=audio.filename,
                    duration=round(duration, 2),
                    min_duration=self.MIN_AUDIO_DURATION
                )
                raise InvalidAudioError(
                    f"Audio duration {duration:.2f}s is too short. "
                    f"Minimum duration is {self.MIN_AUDIO_DURATION}s"
                )

            self.logger.debug(
                "Audio validation successful",
                filename=audio.filename,
                duration=round(duration, 2),
                sample_rate=sr
            )

            return True

        except InvalidAudioError:
            # Re-raise domain exceptions
            raise
        except Exception as e:
            # Convert librosa errors to domain exceptions
            self.logger.error(
                "Audio validation failed with unexpected error",
                filename=audio.filename,
                error=str(e)
            )
            raise InvalidAudioError(f"Invalid audio file: {str(e)}")

    def extract_features_with_audio_data(self, audio: RawAudio) -> dict:
        """Extract features AND audio_features data using v4 feature extractor.

        Args:
            audio: Raw audio data

        Returns:
            Dict with "features" (210,) and "audio_features" (dict)

        Raises:
            InvalidAudioError: If audio cannot be processed
            PredictionFailedError: If feature extraction fails
        """
        self.logger.debug(
            "Starting feature extraction with audio_features data",
            filename=audio.filename,
            audio_size_bytes=len(audio.bytes)
        )

        try:
            # Validate audio first
            self.validate_audio(audio)

            # Extract features + audio_features using v4 feature extractor
            result = v4_extract_with_audio_data(audio.bytes, audio.filename)

            features = result["features"]
            audio_features_data = result["audio_features"]

            if features.shape[0] != 210:
                self.logger.error(
                    "Feature extraction returned incorrect number of features",
                    expected=210,
                    actual=features.shape[0]
                )
                raise PredictionFailedError(f"Expected 210 features, got {features.shape[0]}")

            self.logger.debug(
                "Feature extraction with audio_features completed successfully",
                filename=audio.filename,
                feature_count=features.shape[0],
                has_audio_features=audio_features_data is not None
            )

            return result

        except (InvalidAudioError, PredictionFailedError):
            raise
        except ValueError as e:
            self.logger.error(
                "Feature extraction with audio_features failed",
                filename=audio.filename,
                error=str(e)
            )
            raise PredictionFailedError(f"Failed to extract features with audio_features: {str(e)}")
        except Exception as e:
            self.logger.error(
                "Unexpected error during feature extraction with audio_features",
                filename=audio.filename,
                error=str(e)
            )
            raise PredictionFailedError(f"Unexpected error: {str(e)}")
