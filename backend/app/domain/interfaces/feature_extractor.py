"""
Feature Extractor Interface Contract

This module defines the interface contract that all feature extractors must implement.
Each model version should provide a feature_extractor.py module that implements this contract.

Using Protocol for structural subtyping - your extractor doesn't need to explicitly inherit,
it just needs to implement the required methods with correct signatures.
"""

from collections.abc import Callable
from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class FeatureExtractorProtocol(Protocol):
    """
    Interface contract for feature extractors.

    All feature extractors must implement the extract_features method with this exact signature.
    The @runtime_checkable decorator allows isinstance() checks at runtime for validation.

    Example implementation:

        import numpy as np
        import librosa

        def extract_features(audio_bytes: bytes, filename: str) -> np.ndarray:
            # Load audio from bytes
            audio_data, sr = librosa.load(io.BytesIO(audio_bytes), sr=22050)

            # Extract features (example: MFCCs)
            mfccs = librosa.feature.mfcc(y=audio_data, sr=sr, n_mfcc=13)
            mfcc_mean = np.mean(mfccs, axis=1)

            return mfcc_mean
    """

    def extract_features(self, audio_bytes: bytes, filename: str) -> np.ndarray:
        """
        Extract features from audio bytes.

        This is the core method that must be implemented by all feature extractors.
        It receives raw audio data and returns a feature vector that matches
        what the corresponding model expects.

        Args:
            audio_bytes (bytes): Raw audio file content (WAV, MP3, M4A, etc.)
            filename (str): Original filename with extension for format detection
                          (e.g., "speech.wav", "audio.mp3")

        Returns:
            np.ndarray: 1D feature vector of shape (n_features,)
                       The number of features must match what the model expects.
                       For example:
                       - Model v1 expects shape (162,)
                       - Model v2 expects shape (78,)

        Raises:
            ValueError: If audio format is unsupported or invalid
            Exception: If feature extraction fails (invalid audio, processing error)

        Notes:
            - The returned array MUST be 1D (single feature vector)
            - Feature order must be consistent across calls
            - Use consistent sample rates for audio loading
            - Handle different audio formats appropriately
        """
        ...


# Type alias for function-based feature extractors
# If you implement as a standalone function instead of a class method,
# use this signature:
FeatureExtractorFunction = Callable[[bytes, str], np.ndarray]


def validate_feature_extractor(extractor_module) -> bool:
    """
    Validate that a module implements the feature extractor contract.

    This function checks if a dynamically imported module has the required
    extract_features function with the correct signature.

    Args:
        extractor_module: Imported Python module

    Returns:
        bool: True if valid, False otherwise

    Example:
        >>> import importlib.util
        >>> spec = importlib.util.spec_from_file_location("extractor", "v1/feature_extractor.py")
        >>> module = importlib.util.module_from_spec(spec)
        >>> spec.loader.exec_module(module)
        >>> validate_feature_extractor(module)
        True
    """
    # Check if extract_features function exists
    if not hasattr(extractor_module, "extract_features"):
        return False

    extract_fn = getattr(extractor_module, "extract_features")

    # Check if it's callable
    if not callable(extract_fn):
        return False

    # Optional: Check function signature
    import inspect

    sig = inspect.signature(extract_fn)
    params = list(sig.parameters.keys())

    # Should have at least 2 parameters (audio_bytes, filename)
    # May have more if implemented as a method (self)
    if len(params) < 2:
        return False

    return True


def validate_feature_output(features: np.ndarray, expected_shape: int) -> bool:
    """
    Validate that extracted features match expected dimensions.

    Args:
        features: Output from extract_features()
        expected_shape: Expected number of features

    Returns:
        bool: True if valid, False otherwise
    """
    if not isinstance(features, np.ndarray):
        return False

    # Must be 1D array
    if features.ndim != 1:
        return False

    # Must match expected number of features
    if features.shape[0] != expected_shape:
        return False

    # Must contain valid numbers (no NaN or Inf)
    if not np.all(np.isfinite(features)):
        return False

    return True
