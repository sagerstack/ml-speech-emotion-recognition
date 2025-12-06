"""Audio metadata value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioMetadata:
    """Metadata about audio file.

    Contains technical information about the audio file such as
    duration, sample rate, and number of channels. This is an
    immutable value object.

    Attributes:
        duration_seconds: Duration of audio in seconds
        sample_rate: Sample rate in Hz (e.g., 16000, 44100)
        channels: Number of audio channels (1 for mono, 2 for stereo)
    """

    duration_seconds: float
    sample_rate: int
    channels: int

    def __post_init__(self) -> None:
        """Validate audio metadata values."""
        # Validate duration
        if not isinstance(self.duration_seconds, (int, float)):
            raise ValueError(f"Duration must be a number, got {type(self.duration_seconds)}")
        if self.duration_seconds <= 0:
            raise ValueError(f"Duration must be positive, got {self.duration_seconds}")

        # Validate sample rate
        if not isinstance(self.sample_rate, int):
            raise ValueError(f"Sample rate must be an integer, got {type(self.sample_rate)}")
        if self.sample_rate <= 0:
            raise ValueError(f"Sample rate must be positive, got {self.sample_rate}")

        # Common sample rates: 8000, 16000, 22050, 44100, 48000
        valid_sample_rates = [8000, 16000, 22050, 44100, 48000]
        if self.sample_rate not in valid_sample_rates:
            # Allow other rates but log a warning (in production, use logger)
            pass

        # Validate channels
        if not isinstance(self.channels, int):
            raise ValueError(f"Channels must be an integer, got {type(self.channels)}")
        if self.channels <= 0:
            raise ValueError(f"Channels must be positive, got {self.channels}")
        if self.channels > 2:
            raise ValueError(
                f"Only mono (1) and stereo (2) audio supported, got {self.channels} channels"
            )

    @classmethod
    def create(cls, duration_seconds: float, sample_rate: int, channels: int) -> "AudioMetadata":
        """Factory method to create AudioMetadata.

        Args:
            duration_seconds: Duration of audio in seconds
            sample_rate: Sample rate in Hz
            channels: Number of audio channels

        Returns:
            AudioMetadata instance

        Raises:
            ValueError: If any parameter is invalid
        """
        return cls(
            duration_seconds=duration_seconds,
            sample_rate=sample_rate,
            channels=channels,
        )

    def is_mono(self) -> bool:
        """Check if audio is mono.

        Returns:
            True if audio has 1 channel
        """
        return self.channels == 1

    def is_stereo(self) -> bool:
        """Check if audio is stereo.

        Returns:
            True if audio has 2 channels
        """
        return self.channels == 2

    def total_samples(self) -> int:
        """Calculate total number of samples.

        Returns:
            Total number of samples (duration * sample_rate)
        """
        return int(self.duration_seconds * self.sample_rate)

    def __str__(self) -> str:
        """String representation."""
        channel_str = "mono" if self.is_mono() else "stereo"
        return f"{self.duration_seconds:.2f}s, " f"{self.sample_rate}Hz, " f"{channel_str}"
