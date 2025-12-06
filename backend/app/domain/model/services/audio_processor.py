"""Audio processing domain service interface."""

from abc import ABC, abstractmethod

import numpy as np

from app.domain.model.entities.raw_audio import RawAudio
from app.domain.model.value_objects.audio_metadata import AudioMetadata


class AudioProcessor(ABC):
    """Abstract interface for audio processing operations.

    This domain service defines the contract for processing audio files
    and extracting features for emotion recognition. The actual implementation
    will be in the infrastructure layer.

    The interface follows the Dependency Inversion Principle (DIP) -
    the domain defines what it needs, and infrastructure provides
    the implementation.
    """

    @abstractmethod
    def extract_features(self, audio: RawAudio) -> np.ndarray:
        """Extract features from raw audio.

        Extracts acoustic features (e.g., MFCCs) that will be used
        as input to the emotion recognition model.

        Args:
            audio: Raw audio data

        Returns:
            Feature vector as numpy array with shape matching model's
            expected input dimension

        Raises:
            InvalidAudioError: If audio cannot be processed
            PredictionFailedError: If feature extraction fails
        """
        pass

    @abstractmethod
    def get_audio_metadata(self, audio: RawAudio) -> AudioMetadata:
        """Extract metadata from raw audio.

        Analyzes the audio file to extract technical metadata such as
        duration, sample rate, and number of channels.

        Args:
            audio: Raw audio data

        Returns:
            AudioMetadata with duration, sample rate, and channels

        Raises:
            InvalidAudioError: If audio cannot be analyzed
        """
        pass

    @abstractmethod
    def validate_audio(self, audio: RawAudio) -> bool:
        """Validate that audio can be processed.

        Performs validation checks to ensure the audio file meets
        requirements for processing (e.g., valid format, sufficient duration).

        Args:
            audio: Raw audio data

        Returns:
            True if audio is valid for processing

        Raises:
            InvalidAudioError: If audio is invalid with details about why
        """
        pass

    @abstractmethod
    def extract_features_with_audio_data(self, audio: RawAudio) -> dict:
        """Extract features AND audio_features data from raw audio.

        This method extracts both:
        - Model input features (210 scalars)
        - Audio features for visualization (matrices, time series)

        Args:
            audio: Raw audio data

        Returns:
            Dict with keys:
                - "features": np.ndarray of shape (210,)
                - "audio_features": Dict with waveform, mel, chroma, etc.

        Raises:
            InvalidAudioError: If audio cannot be processed
            PredictionFailedError: If feature extraction fails
        """
        pass
