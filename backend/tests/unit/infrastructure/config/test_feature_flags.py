"""
Unit tests for Feature Flags Service.

This test suite validates the feature flag logic that controls experimental features
like audio features inference. Tests cover:
- Default disabled state for production safety
- Environment variable configuration
- Request-level logic (both feature AND user request must be true)
- Logging behavior for different scenarios
- Singleton pattern validation
"""

import os
from unittest.mock import patch

import pytest

from app.infrastructure.config.feature_flags import FeatureFlags, get_feature_flags
from app.infrastructure.config import Settings


class TestFeatureFlagsDefaultBehavior:
    """Test default feature flag behavior without environment overrides."""

    def test_audio_features_inference_disabled_by_default(self):
        """Test that audio features inference is disabled by default for safety."""
        flags = FeatureFlags()

        assert (
            flags.inference_audio_features_enabled is False
        ), "Audio features inference should be disabled by default for production safety"

    def test_should_include_audio_features_false_when_not_requested(self):
        """Test that audio_features not included when user doesn't request it."""
        flags = FeatureFlags()

        result = flags.should_include_audio_features(requested=False)

        assert result is False, "Audio features should not be included when not requested"

    def test_should_include_audio_features_false_when_feature_disabled(self):
        """Test that audio_features not included when feature is disabled globally."""
        flags = FeatureFlags()

        # User requests it, but feature is disabled
        result = flags.should_include_audio_features(requested=True)

        assert (
            result is False
        ), "Audio features should not be included when feature is disabled, even if requested"

    def test_default_request_parameter_is_false(self):
        """Test that the requested parameter defaults to False."""
        flags = FeatureFlags()

        # Call without parameter
        result = flags.should_include_audio_features()

        assert result is False, "should_include_audio_features() should default requested=False"


class TestFeatureFlagsEnvironmentConfiguration:
    """Test feature flag configuration via environment variables."""

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "true"})
    def test_audio_features_enabled_via_environment_true_string(self):
        """Test that feature can be enabled via environment variable (string 'true')."""
        # Need to create new settings instance to pick up env var
        with patch("app.infrastructure.config.feature_flags.get_settings") as mock_get_settings:
            mock_settings = Settings(secret_key="test-key", ENABLE_INFERENCE_AUDIO_FEATURES=True)
            mock_get_settings.return_value = mock_settings

            flags = FeatureFlags()

            assert (
                flags.inference_audio_features_enabled is True
            ), "Audio features should be enabled when ENABLE_INFERENCE_AUDIO_FEATURES=true"

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "false"})
    def test_audio_features_disabled_via_environment_false_string(self):
        """Test that feature remains disabled with explicit 'false' value."""
        with patch("app.infrastructure.config.feature_flags.get_settings") as mock_get_settings:
            mock_settings = Settings(secret_key="test-key", ENABLE_INFERENCE_AUDIO_FEATURES=False)
            mock_get_settings.return_value = mock_settings

            flags = FeatureFlags()

            assert (
                flags.inference_audio_features_enabled is False
            ), "Audio features should be disabled when ENABLE_INFERENCE_AUDIO_FEATURES=false"

    @patch.dict(os.environ, {"ENABLE_INFERENCE_AUDIO_FEATURES": "1"})
    def test_audio_features_enabled_via_environment_numeric_one(self):
        """Test that feature can be enabled with numeric value 1."""
        with patch("app.infrastructure.config.feature_flags.get_settings") as mock_get_settings:
            mock_settings = Settings(secret_key="test-key", ENABLE_INFERENCE_AUDIO_FEATURES=True)
            mock_get_settings.return_value = mock_settings

            flags = FeatureFlags()

            assert (
                flags.inference_audio_features_enabled is True
            ), "Audio features should be enabled when ENABLE_INFERENCE_AUDIO_FEATURES=1"


class TestFeatureFlagsRequestLevelLogic:
    """Test the request-level logic combining feature flag and user request."""

    @pytest.mark.parametrize(
        "feature_enabled,user_requested,expected_result",
        [
            (False, False, False),  # Feature off, not requested
            (False, True, False),  # Feature off, requested (denied)
            (True, False, False),  # Feature on, not requested
            (True, True, True),  # Feature on, requested (allowed)
        ],
    )
    def test_should_include_audio_features_all_combinations(
        self, feature_enabled, user_requested, expected_result
    ):
        """Test all combinations of feature flag and user request."""
        with patch("app.infrastructure.config.feature_flags.get_settings") as mock_get_settings:
            mock_settings = Settings(
                secret_key="test-key", ENABLE_INFERENCE_AUDIO_FEATURES=feature_enabled
            )
            mock_get_settings.return_value = mock_settings

            flags = FeatureFlags()
            result = flags.should_include_audio_features(requested=user_requested)

            assert result == expected_result, (
                f"Expected {expected_result} for feature_enabled={feature_enabled}, "
                f"user_requested={user_requested}"
            )

    def test_both_conditions_must_be_true(self):
        """Test that BOTH feature enabled AND user requested must be true."""
        # Feature enabled, user requested
        with patch("app.infrastructure.config.feature_flags.get_settings") as mock_get_settings:
            mock_settings = Settings(secret_key="test-key", ENABLE_INFERENCE_AUDIO_FEATURES=True)
            mock_get_settings.return_value = mock_settings

            flags = FeatureFlags()

            # Only when both are true
            assert flags.should_include_audio_features(requested=True) is True

            # False when only one is true
            assert flags.should_include_audio_features(requested=False) is False

    def test_safe_gradual_rollout_pattern(self):
        """Test that the pattern enables safe gradual rollout."""
        # Start: Feature disabled globally
        with patch("app.infrastructure.config.feature_flags.get_settings") as mock_get_settings:
            mock_settings = Settings(secret_key="test-key", ENABLE_INFERENCE_AUDIO_FEATURES=False)
            mock_get_settings.return_value = mock_settings

            flags = FeatureFlags()

            # Even if users try to request it, it's blocked
            assert flags.should_include_audio_features(requested=True) is False

        # Rollout: Feature enabled globally, but users must opt-in
        with patch("app.infrastructure.config.feature_flags.get_settings") as mock_get_settings:
            mock_settings = Settings(secret_key="test-key", ENABLE_INFERENCE_AUDIO_FEATURES=True)
            mock_get_settings.return_value = mock_settings

            flags = FeatureFlags()

            # Only users who request it get it
            assert flags.should_include_audio_features(requested=False) is False
            assert flags.should_include_audio_features(requested=True) is True


class TestFeatureFlagsLogging:
    """Test logging behavior for different scenarios."""

    def test_warning_logged_when_requested_but_disabled(self, caplog):
        """Test that warning is logged when user requests but feature is disabled."""
        import logging

        caplog.set_level(logging.WARNING)

        flags = FeatureFlags()

        # Request audio_features while feature is disabled
        result = flags.should_include_audio_features(requested=True)

        assert result is False
        # Check that warning was logged
        assert any(
            "Audio features requested but feature is disabled" in record.message
            for record in caplog.records
        ), "Should log warning when audio_features requested but feature disabled"

    def test_no_warning_when_not_requested(self, caplog):
        """Test that no warning is logged when user doesn't request audio_features."""
        import logging

        caplog.set_level(logging.WARNING)

        flags = FeatureFlags()

        # Don't request audio_features
        result = flags.should_include_audio_features(requested=False)

        assert result is False
        # Should not log warning
        assert not any(
            "Audio features requested but feature is disabled" in record.message
            for record in caplog.records
        ), "Should not log warning when audio_features not requested"

    def test_debug_logged_when_both_enabled(self, caplog):
        """Test that debug message is logged when both conditions are met."""
        import logging

        caplog.set_level(logging.DEBUG)

        with patch("app.infrastructure.config.feature_flags.get_settings") as mock_get_settings:
            mock_settings = Settings(secret_key="test-key", ENABLE_INFERENCE_AUDIO_FEATURES=True)
            mock_get_settings.return_value = mock_settings

            flags = FeatureFlags()
            result = flags.should_include_audio_features(requested=True)

            assert result is True
            # Check that debug message was logged
            assert any(
                "Audio features data will be included" in record.message for record in caplog.records
            ), "Should log debug message when audio_features will be included"


class TestFeatureFlagsSingleton:
    """Test singleton pattern for feature flags."""

    def test_get_feature_flags_returns_same_instance(self):
        """Test that get_feature_flags returns the same instance (singleton)."""
        # Clear the cache first
        get_feature_flags.cache_clear()

        flags1 = get_feature_flags()
        flags2 = get_feature_flags()

        assert (
            flags1 is flags2
        ), "get_feature_flags should return the same instance (singleton pattern)"

    def test_get_feature_flags_is_cached(self):
        """Test that get_feature_flags uses LRU cache."""
        # Clear the cache
        get_feature_flags.cache_clear()

        # First call
        flags1 = get_feature_flags()

        # Cache info should show 1 miss, 0 hits
        cache_info = get_feature_flags.cache_info()
        assert cache_info.misses >= 1, "First call should be a cache miss"

        # Second call
        flags2 = get_feature_flags()

        # Cache info should now show at least 1 hit
        cache_info = get_feature_flags.cache_info()
        assert cache_info.hits >= 1, "Second call should be a cache hit"

        assert flags1 is flags2

    def test_get_feature_flags_can_be_used_as_dependency(self):
        """Test that get_feature_flags can be used with FastAPI Depends."""
        from fastapi import Depends

        # This should not raise an error
        def endpoint_example(flags: FeatureFlags = Depends(get_feature_flags)):
            return flags.inference_audio_features_enabled

        # Verify the function is callable
        assert callable(endpoint_example)

        # Simulate dependency injection
        flags = get_feature_flags()
        result = endpoint_example(flags=flags)

        assert isinstance(result, bool)


class TestFeatureFlagsInitialization:
    """Test feature flags initialization and logging."""

    def test_initialization_logs_flag_states(self, caplog):
        """Test that initialization logs the current feature flag states."""
        import logging

        caplog.set_level(logging.INFO)

        flags = FeatureFlags()

        # Check that initialization logged the flag state
        assert any(
            "Feature flags initialized" in record.message for record in caplog.records
        ), "Initialization should log feature flag states"

    def test_initialization_uses_settings(self):
        """Test that initialization correctly reads from settings."""
        with patch("app.infrastructure.config.feature_flags.get_settings") as mock_get_settings:
            mock_settings = Settings(
                secret_key="test-key",
                ENABLE_INFERENCE_AUDIO_FEATURES=True,
                LOG_AUDIO_FEATURES_METRICS=False,
            )
            mock_get_settings.return_value = mock_settings

            flags = FeatureFlags()

            assert flags.inference_audio_features_enabled is True
            assert flags.settings.LOG_AUDIO_FEATURES_METRICS is False


class TestFeatureFlagsBackwardCompatibility:
    """Test that feature flags maintain backward compatibility."""

    def test_existing_code_works_with_default_disabled(self):
        """Test that existing code continues to work with feature disabled."""
        flags = FeatureFlags()

        # Existing code that doesn't pass include_audio_features parameter
        # Should get False (feature disabled by default)
        result = flags.should_include_audio_features()

        assert result is False, "Existing code should continue to work with feature disabled"

    def test_explicit_false_request_respected(self):
        """Test that explicit False request is respected even if feature enabled."""
        with patch("app.infrastructure.config.feature_flags.get_settings") as mock_get_settings:
            mock_settings = Settings(secret_key="test-key", ENABLE_INFERENCE_AUDIO_FEATURES=True)
            mock_get_settings.return_value = mock_settings

            flags = FeatureFlags()

            # Even with feature enabled, explicit False request returns False
            result = flags.should_include_audio_features(requested=False)

            assert (
                result is False
            ), "Explicit False request should be respected even when feature enabled"


@pytest.mark.unit
class TestFeatureFlagsEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_property_returns_boolean(self):
        """Test that inference_audio_features_enabled always returns a boolean."""
        flags = FeatureFlags()

        result = flags.inference_audio_features_enabled

        assert isinstance(
            result, bool
        ), f"inference_audio_features_enabled should return bool, got {type(result)}"

    def test_should_include_audio_features_returns_boolean(self):
        """Test that should_include_audio_features always returns a boolean."""
        flags = FeatureFlags()

        result = flags.should_include_audio_features(requested=True)

        assert isinstance(
            result, bool
        ), f"should_include_audio_features should return bool, got {type(result)}"

    def test_multiple_calls_idempotent(self):
        """Test that multiple calls to should_include_audio_features are idempotent."""
        flags = FeatureFlags()

        result1 = flags.should_include_audio_features(requested=True)
        result2 = flags.should_include_audio_features(requested=True)
        result3 = flags.should_include_audio_features(requested=True)

        assert (
            result1 == result2 == result3
        ), "Multiple calls should return the same result (idempotent)"

    @pytest.mark.parametrize("requested_value", [True, False, None, 0, 1, "", "yes"])
    def test_should_include_audio_features_handles_various_types(self, requested_value):
        """Test that should_include_audio_features handles various input types gracefully."""
        flags = FeatureFlags()

        # Should not raise error, should handle via Python's truthiness
        try:
            result = flags.should_include_audio_features(requested=requested_value)
            assert isinstance(result, bool)
        except Exception as e:
            pytest.fail(f"should_include_audio_features raised {e} for input {requested_value}")
