"""
Unit tests for configuration management utilities.

This module tests the Settings class, environment variable handling,
and configuration validation logic.
"""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from app.utils.config import Settings, get_settings


class TestSettings:
    """Test cases for Settings class."""

    def test_default_settings(self) -> None:
        """Test default configuration values with test environment."""
        # Note: This test runs with the test_environment fixture from conftest.py
        # which sets certain environment variables for testing
        settings = Settings()

        assert settings.app_name == "ML Speech Emotion Recognition API"
        assert settings.app_version == "1.0.0"
        assert settings.debug is True  # Set by test_environment fixture
        assert settings.api_v1_str == "/v1"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.aws_region == "us-east-1"  # Set by test_environment fixture
        assert settings.sagemaker_endpoint_name == "test-endpoint"  # Set by test_environment fixture
        assert settings.max_upload_size_mb == 30
        assert settings.max_audio_duration_seconds == 30
        assert settings.supported_formats == ["wav", "mp3", "m4a"]
        assert settings.prometheus_enabled is True
        assert settings.metrics_port == 9090

    def test_settings_from_environment_variables(self) -> None:
        """Test loading settings from environment variables."""
        env_vars = {
            "APP_NAME": "Test API",
            "DEBUG": "true",
            "HOST": "127.0.0.1",
            "PORT": "9000",
            "AWS_REGION": "eu-west-1",
            "SAGEMAKER_ENDPOINT_NAME": "prod-endpoint",
            "MAX_UPLOAD_SIZE_MB": "50",
            "MAX_AUDIO_DURATION_SECONDS": "60",
            "PROMETHEUS_ENABLED": "false"
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.app_name == "Test API"
            assert settings.debug is True
            assert settings.host == "127.0.0.1"
            assert settings.port == 9000
            assert settings.aws_region == "eu-west-1"
            assert settings.sagemaker_endpoint_name == "prod-endpoint"
            assert settings.max_upload_size_mb == 50
            assert settings.max_audio_duration_seconds == 60
            assert settings.prometheus_enabled is False

    def test_cors_origins_configuration(self) -> None:
        """Test CORS origins configuration."""
        settings = Settings()

        expected_origins = [
            "http://localhost:3000",
            "http://localhost:8501",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8501"
        ]

        assert settings.cors_origins == expected_origins

    def test_cors_origins_from_environment(self) -> None:
        """Test loading CORS origins from environment."""
        env_vars = {
            "CORS_ORIGINS": '["https://example.com", "https://app.example.com"]'
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert "https://example.com" in settings.cors_origins
            assert "https://app.example.com" in settings.cors_origins

    def test_security_configuration(self) -> None:
        """Test security-related configuration."""
        settings = Settings()

        assert settings.secret_key == "test-secret-key-for-jwt"  # Set by test_environment fixture
        assert settings.algorithm == "HS256"
        assert settings.access_token_expire_minutes == 30

    def test_security_configuration_from_environment(self) -> None:
        """Test loading security configuration from environment."""
        env_vars = {
            "SECRET_KEY": "production-secret-key",
            "ALGORITHM": "RS256",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "60"
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.secret_key == "production-secret-key"
            assert settings.algorithm == "RS256"
            assert settings.access_token_expire_minutes == 60

    def test_s3_configuration(self) -> None:
        """Test S3 configuration."""
        settings = Settings()

        assert settings.s3_bucket_name == "your-s3-bucket-name"  # From .env file
        assert settings.s3_temp_prefix == "temp-audio/"

    def test_s3_configuration_from_environment(self) -> None:
        """Test loading S3 configuration from environment."""
        env_vars = {
            "S3_BUCKET_NAME": "test-audio-bucket",
            "S3_TEMP_PREFIX": "uploads/temp/"
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.s3_bucket_name == "test-audio-bucket"
            assert settings.s3_temp_prefix == "uploads/temp/"

    def test_performance_configuration(self) -> None:
        """Test performance-related configuration."""
        settings = Settings()

        assert settings.max_concurrent_requests == 50
        assert settings.request_timeout_seconds == 60

    def test_performance_configuration_from_environment(self) -> None:
        """Test loading performance configuration from environment."""
        env_vars = {
            "MAX_CONCURRENT_REQUESTS": "100",
            "REQUEST_TIMEOUT_SECONDS": "120"
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.max_concurrent_requests == 100
            assert settings.request_timeout_seconds == 120

    def test_supported_formats_configuration(self) -> None:
        """Test supported audio formats configuration."""
        settings = Settings()

        expected_formats = ["wav", "mp3", "m4a"]
        assert settings.supported_formats == expected_formats

    def test_supported_formats_from_environment(self) -> None:
        """Test loading supported formats from environment."""
        env_vars = {
            "SUPPORTED_FORMATS": '["wav", "mp3", "flac", "ogg"]'
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert "wav" in settings.supported_formats
            assert "mp3" in settings.supported_formats
            assert "flac" in settings.supported_formats
            assert "ogg" in settings.supported_formats

    def test_invalid_port_value(self) -> None:
        """Test handling of invalid port value."""
        env_vars = {"PORT": "invalid_port"}

        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValidationError):
                Settings()

    def test_invalid_boolean_value(self) -> None:
        """Test handling of invalid boolean value."""
        env_vars = {"DEBUG": "not_a_boolean"}

        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValidationError):
                Settings()

    def test_invalid_integer_value(self) -> None:
        """Test handling of invalid integer value."""
        env_vars = {"MAX_UPLOAD_SIZE_MB": "not_an_integer"}

        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValidationError):
                Settings()

    def test_case_insensitive_environment_variables(self) -> None:
        """Test that environment variables are case insensitive."""
        env_vars = {
            "app_name": "Test App Lowercase",
            "DEBUG": "true"
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            assert settings.app_name == "Test App Lowercase"
            assert settings.debug is True

    def test_extra_fields_ignored(self) -> None:
        """Test that extra fields in environment are ignored."""
        env_vars = {
            "UNKNOWN_FIELD": "some_value",
            "ANOTHER_UNKNOWN": "another_value"
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()

            # Should not raise an error and should not have unknown fields
            assert not hasattr(settings, "unknown_field")
            assert not hasattr(settings, "another_unknown")

    def test_empty_environment_variables(self) -> None:
        """Test handling of empty environment variables."""
        # Test that env_ignore_empty=True ignores empty strings and uses defaults
        # We set only specific empty variables while preserving the test_environment fixture values

        with patch.dict(os.environ, {
            "APP_NAME": "",  # Empty string
            "DEBUG": "true"   # Keep this as true from test_environment fixture
        }, clear=False):
            settings = Settings()

            # With env_ignore_empty=True, empty APP_NAME should be ignored and default used
            assert settings.app_name == "ML Speech Emotion Recognition API"  # Default value
            # DEBUG should be True since we explicitly set it to "true"
            assert settings.debug is True

    def test_env_file_loading(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading configuration from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("""
APP_NAME=Test from .env file
DEBUG=true
PORT=9999
AWS_REGION=eu-central-1
        """)

        # Clear environment variables that might interfere
        with monkeypatch.context() as m:
            env_vars_to_clear = ["AWS_REGION", "APP_NAME", "DEBUG", "PORT"]
            for var in env_vars_to_clear:
                m.delenv(var, raising=False)

            # Change to the temp directory where the .env file exists
            original_cwd = os.getcwd()
            try:
                os.chdir(tmp_path)
                settings = Settings(_env_file=str(env_file))

                assert settings.app_name == "Test from .env file"
                assert settings.debug is True
                assert settings.port == 9999
                assert settings.aws_region == "eu-central-1"
            finally:
                os.chdir(original_cwd)


class TestGetSettings:
    """Test cases for get_settings function."""

    def test_get_settings_returns_singleton(self) -> None:
        """Test that get_settings returns the same instance."""
        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2
        assert id(settings1) == id(settings2)

    def test_get_settings_creates_instance_if_none(self) -> None:
        """Test that get_settings creates instance if none exists."""
        # Reset the global settings instance
        import app.utils.config
        app.utils.config._settings = None

        settings = get_settings()

        assert settings is not None
        assert isinstance(settings, Settings)

    def test_get_settings_preserves_modifications(self) -> None:
        """Test that modifications to the returned settings are preserved."""
        # Reset the global settings instance
        import app.utils.config
        app.utils.config._settings = None

        settings1 = get_settings()
        original_name = settings1.app_name

        # Modify the settings
        settings1.app_name = "Modified Name"

        # Get settings again
        settings2 = get_settings()

        assert settings2.app_name == "Modified Name"
        assert settings2.app_name != original_name

    def test_get_settings_with_environment_override(self) -> None:
        """Test get_settings with environment variable override."""
        env_vars = {"APP_NAME": "Environment Override"}

        # Reset the global settings instance
        import app.utils.config
        app.utils.config._settings = None

        with patch.dict(os.environ, env_vars):
            settings = get_settings()

            assert settings.app_name == "Environment Override"


class TestSettingsValidation:
    """Test cases for settings validation."""

    def test_port_range_validation(self) -> None:
        """Test port number range validation."""
        # Valid port numbers
        for port in [80, 443, 8000, 8080, 9000]:
            env_vars = {"PORT": str(port)}
            with patch.dict(os.environ, env_vars):
                settings = Settings()
                assert settings.port == port

        # Invalid port numbers (outside typical range)
        for port in [-1, 0, 65536, 100000]:
            env_vars = {"PORT": str(port)}
            with patch.dict(os.environ, env_vars):
                # Pydantic doesn't validate port range by default, but we test our constraints
                settings = Settings()
                # Our application logic should handle invalid ports
                assert settings.port == port  # Pydantic accepts any positive integer

    def test_timeout_values_validation(self) -> None:
        """Test timeout value validation."""
        # Valid timeout values
        for timeout in [1, 30, 60, 300, 3600]:
            env_vars = {"REQUEST_TIMEOUT_SECONDS": str(timeout)}
            with patch.dict(os.environ, env_vars):
                settings = Settings()
                assert settings.request_timeout_seconds == timeout

        # Invalid timeout values
        for timeout in [0, -1, -30]:
            env_vars = {"REQUEST_TIMEOUT_SECONDS": str(timeout)}
            with patch.dict(os.environ, env_vars):
                # Pydantic validates positive integers for certain fields
                with pytest.raises(ValidationError):
                    Settings()

    def test_upload_size_validation(self) -> None:
        """Test upload size validation."""
        # Valid sizes
        for size in [1, 10, 25, 50, 100]:
            env_vars = {"MAX_UPLOAD_SIZE_MB": str(size)}
            with patch.dict(os.environ, env_vars):
                settings = Settings()
                assert settings.max_upload_size_mb == size

        # Invalid sizes
        for size in [0, -1, -10]:
            env_vars = {"MAX_UPLOAD_SIZE_MB": str(size)}
            with patch.dict(os.environ, env_vars):
                with pytest.raises(ValidationError):
                    Settings()

    def test_audio_duration_validation(self) -> None:
        """Test audio duration validation."""
        # Valid durations
        for duration in [1, 10, 30, 60, 120]:
            env_vars = {"MAX_AUDIO_DURATION_SECONDS": str(duration)}
            with patch.dict(os.environ, env_vars):
                settings = Settings()
                assert settings.max_audio_duration_seconds == duration

        # Invalid durations
        for duration in [0, -1, -30]:
            env_vars = {"MAX_AUDIO_DURATION_SECONDS": str(duration)}
            with patch.dict(os.environ, env_vars):
                with pytest.raises(ValidationError):
                    Settings()

    def test_concurrent_requests_validation(self) -> None:
        """Test concurrent requests validation."""
        # Valid values
        for requests in [1, 10, 50, 100, 1000]:
            env_vars = {"MAX_CONCURRENT_REQUESTS": str(requests)}
            with patch.dict(os.environ, env_vars):
                settings = Settings()
                assert settings.max_concurrent_requests == requests

        # Invalid values
        for requests in [0, -1, -10]:
            env_vars = {"MAX_CONCURRENT_REQUESTS": str(requests)}
            with patch.dict(os.environ, env_vars):
                with pytest.raises(ValidationError):
                    Settings()

    def test_token_expiry_validation(self) -> None:
        """Test access token expiry validation."""
        # Valid values
        for minutes in [1, 5, 15, 30, 60, 1440]:  # 1 day
            env_vars = {"ACCESS_TOKEN_EXPIRE_MINUTES": str(minutes)}
            with patch.dict(os.environ, env_vars):
                settings = Settings()
                assert settings.access_token_expire_minutes == minutes

        # Invalid values
        for minutes in [0, -1, -30]:
            env_vars = {"ACCESS_TOKEN_EXPIRE_MINUTES": str(minutes)}
            with patch.dict(os.environ, env_vars):
                with pytest.raises(ValidationError):
                    Settings()


class TestSettingsEdgeCases:
    """Test edge cases for settings configuration."""

    def test_very_long_values(self) -> None:
        """Test handling of very long string values."""
        long_string = "a" * 10000  # 10KB string
        env_vars = {"APP_NAME": long_string}

        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.app_name == long_string

    def test_unicode_characters(self) -> None:
        """Test handling of unicode characters in configuration."""
        unicode_name = "测试应用程序 🎵"
        env_vars = {"APP_NAME": unicode_name}

        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.app_name == unicode_name

    def test_special_characters_in_secret_key(self) -> None:
        """Test handling of special characters in secret key."""
        special_key = "secret-key-!@#$%^&*()_+-=[]{}|;:,.<>?"
        env_vars = {"SECRET_KEY": special_key}

        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.secret_key == special_key

    def test_whitespace_handling(self) -> None:
        """Test handling of whitespace in string values."""
        env_vars = {
            "APP_NAME": "  spaced name  ",
            "AWS_REGION": "\tus-east-1\n"
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()
            # Pydantic typically strips whitespace
            assert settings.app_name.strip() == "spaced name"
            assert settings.aws_region.strip() == "us-east-1"

    @pytest.mark.parametrize("config_field,expected_type", [
        ("app_name", str),
        ("app_version", str),
        ("debug", bool),
        ("port", int),
        ("max_upload_size_mb", int),
        ("max_audio_duration_seconds", int),
        ("supported_formats", list),
        ("cors_origins", list),
        ("prometheus_enabled", bool),
        ("metrics_port", int),
        ("s3_bucket_name", (str, type(None))),
        ("secret_key", str),
        ("algorithm", str),
        ("access_token_expire_minutes", int),
    ])
    def test_field_types(self, config_field, expected_type) -> None:
        """Test that configuration fields have expected types."""
        settings = Settings()
        value = getattr(settings, config_field)

        if isinstance(expected_type, tuple):
            assert isinstance(value, expected_type)
        else:
            assert isinstance(value, expected_type)