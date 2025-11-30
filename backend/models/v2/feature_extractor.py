"""
Feature Extractor for Model v2 (SVM Pipeline with RFE)

This extractor uses the EXACT SAME feature extraction logic from training.
Produces 78 features: MFCCs (13×2) + Delta MFCCs (13×2) + Delta² MFCCs (13×2)

Training parameters:
- Duration: 2.5 seconds
- Offset: 0.6 seconds
- Sample rate: default (22050 Hz)
- MFCCs: 13 coefficients
"""

import io
import numpy as np
import librosa


def extract_features(audio_bytes: bytes, filename: str) -> np.ndarray:
    """
    Extract 78 MFCC-based features from audio bytes for v2 model.

    This matches the exact feature extraction used during training:
    - MFCCs: mean (13) + std (13) = 26 features
    - Delta MFCCs: mean (13) + std (13) = 26 features
    - Delta² MFCCs: mean (13) + std (13) = 26 features
    Total: 78 features

    Args:
        audio_bytes: Raw audio file bytes
        filename: Original filename (used for format detection)

    Returns:
        np.ndarray: Feature vector of shape (78,)

    Raises:
        ValueError: If audio cannot be loaded or processed
    """
    try:
        # Load audio from bytes with same parameters as training
        # duration=2.5, offset=0.6 to skip silence at start/end
        y, sr = librosa.load(
            io.BytesIO(audio_bytes),
            duration=2.5,
            offset=0.6
        )

        # 1. Calculate features (Matrices)
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_delta = librosa.feature.delta(mfccs)
        mfcc_delta2 = librosa.feature.delta(mfccs, order=2)

        # 2. Calculate Functionals (Collapse time with axis=1)
        # Stack Mean and Std Dev for all three types
        features = np.hstack([
            np.mean(mfccs, axis=1),        # 13 features
            np.std(mfccs, axis=1),         # 13 features
            np.mean(mfcc_delta, axis=1),   # 13 features
            np.std(mfcc_delta, axis=1),    # 13 features
            np.mean(mfcc_delta2, axis=1),  # 13 features
            np.std(mfcc_delta2, axis=1)    # 13 features
        ])

        # Verify shape
        if features.shape[0] != 78:
            raise ValueError(f"Expected 78 features, got {features.shape[0]}")

        return features

    except Exception as e:
        raise ValueError(f"Failed to extract features from audio: {str(e)}")
