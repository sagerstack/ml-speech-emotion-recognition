"""
Interface contracts for the ML Speech Emotion Recognition backend.

This package contains interface definitions (protocols) that define contracts
for various components in the system.
"""

from app.domain.interfaces.feature_extractor import (
    FeatureExtractorFunction,
    FeatureExtractorProtocol,
    validate_feature_extractor,
    validate_feature_output,
)

__all__ = [
    "FeatureExtractorProtocol",
    "FeatureExtractorFunction",
    "validate_feature_extractor",
    "validate_feature_output",
]
