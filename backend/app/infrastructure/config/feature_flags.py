"""
Feature Flag Service for ML Speech Emotion Recognition API

This service provides centralized feature flag management for controlling
experimental features like audio features inference data.

Feature flags enable safe rollout of new features:
- Default: disabled for production safety
- Environment-based: can be enabled via environment variables
- Request-level: honors user request only if feature is enabled
"""

from functools import lru_cache

from app.infrastructure.config import get_settings
from app.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


class FeatureFlags:
    """
    Centralized feature flag management.

    Controls experimental features with environment-based configuration
    for safe rollout and testing.

    Features:
    - inference_audio_features_enabled: Include audio features matrices in inference

    Usage:
        flags = FeatureFlags()
        if flags.should_include_audio_features(user_requested=True):
            # Include audio features data
            pass
    """

    def __init__(self):
        """Initialize feature flags from configuration."""
        self.settings = get_settings()
        logger.info(
            "Feature flags initialized",
            inference_audio_features_enabled=self.inference_audio_features_enabled,
        )

    @property
    def inference_audio_features_enabled(self) -> bool:
        """
        Check if audio features inference feature is enabled.

        This feature controls whether the API should capture and return
        intermediate audio features matrices (mel spectrogram, chroma, MFCCs,
        pitch contour) alongside model predictions.

        Default: False (disabled for production safety)
        Environment variable: ENABLE_INFERENCE_AUDIO_FEATURES

        Returns:
            bool: True if audio features inference is enabled globally
        """
        return self.settings.ENABLE_INFERENCE_AUDIO_FEATURES

    def should_include_audio_features(self, requested: bool = False) -> bool:
        """
        Determine if audio features data should be included in inference response.

        This method implements the feature flag logic:
        1. Feature must be enabled globally (environment variable)
        2. User must explicitly request it (query parameter)
        3. Both conditions must be true

        This ensures:
        - Feature can be disabled completely in production
        - No accidental overhead when not needed
        - Safe gradual rollout to users

        Args:
            requested: Whether the user requested audio features data

        Returns:
            bool: True if audio features should be included

        Examples:
            >>> flags = FeatureFlags()
            >>> # Feature disabled, user requested: False
            >>> flags.should_include_audio_features(requested=True)
            False

            >>> # Feature enabled, user didn't request: False
            >>> flags.should_include_audio_features(requested=False)
            False

            >>> # Feature enabled, user requested: True
            >>> flags.should_include_audio_features(requested=True)
            True
        """
        # Feature must be enabled globally
        if not self.inference_audio_features_enabled:
            if requested:
                logger.warning(
                    "Audio features requested but feature is disabled",
                    feature="inference_audio_features",
                    action="ignored",
                )
            return False

        # User must explicitly request it
        if not requested:
            return False

        # Both conditions met
        logger.debug(
            "Audio features data will be included",
            feature="inference_audio_features",
            requested=requested,
        )
        return True


@lru_cache(maxsize=1)
def get_feature_flags() -> FeatureFlags:
    """
    Get or create global feature flags instance (singleton pattern).

    This function is cached to ensure only one instance exists throughout
    the application lifecycle. Use this factory function in FastAPI
    dependency injection.

    Returns:
        FeatureFlags: Global feature flags instance

    Usage:
        from fastapi import Depends
        from app.infrastructure.config.feature_flags import get_feature_flags, FeatureFlags

        @app.get("/endpoint")
        async def endpoint(flags: FeatureFlags = Depends(get_feature_flags)):
            if flags.inference_audio_features_enabled:
                # Feature is enabled
                pass
    """
    return FeatureFlags()
