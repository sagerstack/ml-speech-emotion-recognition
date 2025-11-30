"""
Feature Extractor for Model v1 (Decision Tree Classifier)

This extractor uses the EXACT SAME feature extraction logic from training.
Produces 162 features: ZCR (1) + Chroma STFT (12) + MFCC (20) + RMS (1) + Mel Spectrogram (128)

Training parameters:
- Duration: 2.5 seconds
- Offset: 0.6 seconds
- Sample rate: default (22050 Hz)
"""

import io
import numpy as np
import librosa


def extract_features(audio_bytes: bytes, filename: str) -> np.ndarray:
    """
    Extract 162 features from audio bytes for v1 model.

    This matches the exact feature extraction used during training:
    - Zero Crossing Rate (1 feature)
    - Chroma STFT (12 features)
    - MFCC (20 features)
    - RMS (1 feature)
    - Mel Spectrogram (128 features)

    Args:
        audio_bytes: Raw audio file bytes
        filename: Original filename (used for format detection)

    Returns:
        np.ndarray: Feature vector of shape (162,)

    Raises:
        ValueError: If audio cannot be loaded or processed
    """
    try:
        # Load audio from bytes with same parameters as training
        # duration=2.5, offset=0.6 to skip silence at start/end
        data, sample_rate = librosa.load(
            io.BytesIO(audio_bytes),
            duration=2.5,
            offset=0.6
        )

        # Initialize result array
        result = np.array([])

        # 1. Zero Crossing Rate (1 feature)
        zcr = np.mean(librosa.feature.zero_crossing_rate(y=data).T, axis=0)
        result = np.hstack((result, zcr))

        # 2. Chroma STFT (12 features)
        stft = np.abs(librosa.stft(data))
        chroma_stft = np.mean(librosa.feature.chroma_stft(S=stft, sr=sample_rate).T, axis=0)
        result = np.hstack((result, chroma_stft))

        # 3. MFCC (20 features - default n_mfcc)
        mfcc = np.mean(librosa.feature.mfcc(y=data, sr=sample_rate).T, axis=0)
        result = np.hstack((result, mfcc))

        # 4. Root Mean Square Value (1 feature)
        rms = np.mean(librosa.feature.rms(y=data).T, axis=0)
        result = np.hstack((result, rms))

        # 5. Mel Spectrogram (128 features - default n_mels)
        mel = np.mean(librosa.feature.melspectrogram(y=data, sr=sample_rate).T, axis=0)
        result = np.hstack((result, mel))

        # Verify shape
        if result.shape[0] != 162:
            raise ValueError(f"Expected 162 features, got {result.shape[0]}")

        return result

    except Exception as e:
        raise ValueError(f"Failed to extract features from audio: {str(e)}")
