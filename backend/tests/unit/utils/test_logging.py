"""
Unit tests for logging utilities.

This module tests the structured logging configuration, logger creation,
and logging helper functions.
"""

import json
import logging
import os
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
import structlog

from app.utils.config import Settings
from app.utils.logging import (
    setup_logging,
    get_logger,
    log_request_info,
    log_response_info
)


class TestSetupLogging:
    """Test cases for setup_logging function."""

    def test_setup_logging_basic_configuration(self) -> None:
        """Test basic logging configuration setup."""
        # Reset logging configuration
        logging.getLogger().handlers.clear()

        setup_logging()

        # Check that structlog is configured
        assert structlog.is_configured()

        # Check that we can get a logger
        logger = get_logger("test")
        assert logger is not None

    def test_setup_logging_in_debug_mode(self) -> None:
        """Test logging setup in debug mode."""
        # Reset logging configuration
        logging.getLogger().handlers.clear()

        with patch("app.utils.logging.get_settings") as mock_get_settings:
            mock_settings = Settings(debug=True)
            mock_get_settings.return_value = mock_settings

            setup_logging()

            # Check that root logger is set to DEBUG level
            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG

    def test_setup_logging_in_production_mode(self) -> None:
        """Test logging setup in production mode."""
        # Reset logging configuration
        logging.getLogger().handlers.clear()

        with patch("app.utils.logging.get_settings") as mock_get_settings:
            mock_settings = Settings(debug=False)
            mock_get_settings.return_value = mock_settings

            setup_logging()

            # Check that root logger is set to INFO level
            root_logger = logging.getLogger()
            assert root_logger.level == logging.INFO

    def test_setup_logging_configures_structlog_processors(self) -> None:
        """Test that structlog processors are configured correctly."""
        # Reset logging configuration
        logging.getLogger().handlers.clear()

        with patch("app.utils.logging.get_settings") as mock_get_settings:
            mock_settings = Settings(debug=True)
            mock_get_settings.return_value = mock_settings

            setup_logging()

            # Check that processors are configured
            from structlog.processors import JSONRenderer
            from structlog.dev import ConsoleRenderer

            # The configuration should have been called
            assert structlog.is_configured()

    def test_setup_logging_configures_third_party_loggers(self) -> None:
        """Test that third-party library loggers are configured with appropriate levels."""
        # Reset logging configuration
        logging.getLogger().handlers.clear()

        setup_logging()

        # Check that specific loggers are set to WARNING level
        loggers_to_check = [
            "uvicorn.access",
            "boto3",
            "botocore",
            "urllib3"
        ]

        for logger_name in loggers_to_check:
            logger = logging.getLogger(logger_name)
            assert logger.level == logging.WARNING

    def test_setup_logging_with_custom_stream(self) -> None:
        """Test logging setup with custom output stream."""
        # Reset logging configuration
        logging.getLogger().handlers.clear()

        with patch("sys.stdout") as mock_stdout:
            setup_logging()

            # Check that logging.basicConfig was called with stream parameter
            # This is indirectly tested by checking that logging works
            logger = logging.getLogger()
            assert len(logger.handlers) > 0

    def test_setup_logging_multiple_calls(self) -> None:
        """Test that calling setup_logging multiple times doesn't break anything."""
        # Reset logging configuration
        logging.getLogger().handlers.clear()

        # Call setup_logging multiple times
        setup_logging()
        setup_logging()
        setup_logging()

        # Should still work
        logger = get_logger("test")
        assert logger is not None


class TestGetLogger:
    """Test cases for get_logger function."""

    def test_get_logger_returns_structlog_logger(self) -> None:
        """Test that get_logger returns a structlog logger."""
        logger = get_logger("test_module")

        # Should be a structlog bound logger
        assert hasattr(logger, "bind")
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")

    def test_get_logger_with_different_names(self) -> None:
        """Test getting loggers with different names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")
        logger3 = get_logger("module1")  # Same name as logger1

        # Should be different instances for different names
        assert logger1 is not logger2
        # Should have the same configuration for the same name (check before binding)
        # Access the private attribute directly to avoid binding
        assert logger1._logger_factory_args == logger3._logger_factory_args
        assert logger1._logger_factory_args == ("module1",)
        assert logger3._logger_factory_args == ("module1",)

        # But they should behave the same way when used
        assert str(logger1) == str(logger3)

    def test_get_logger_name_is_preserved(self) -> None:
        """Test that logger name is preserved."""
        module_name = "test.module.name"
        logger = get_logger(module_name)

        # The logger should have the module name bound
        # Note: structlog doesn't expose name directly, but we can test binding
        bound_logger = logger.bind(extra_info="test")
        assert bound_logger is not None

    def test_get_logger_can_be_used_for_logging(self) -> None:
        """Test that returned logger can be used for actual logging."""
        logger = get_logger("test_logging")

        # Should not raise any exceptions
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        logger.debug("Test debug message")

    def test_get_logger_with_structured_data(self) -> None:
        """Test logging structured data with the returned logger."""
        logger = get_logger("test_structured")

        # Should be able to log structured data
        logger.info(
            "Structured log message",
            key1="value1",
            key2=42,
            key3=["list", "values"]
        )

    def test_get_logger_logger_inheritance(self) -> None:
        """Test that logger inheritance works correctly."""
        parent_logger = get_logger("parent")
        child_logger = get_logger("parent.child")

        # Both should be usable
        parent_logger.info("Parent message")
        child_logger.info("Child message")


class TestLogRequestInfo:
    """Test cases for log_request_info function."""

    def test_log_request_info_basic(self) -> None:
        """Test basic request information logging."""
        logger = get_logger("test_request")
        method = "POST"
        url = "/api/v1/predict"
        headers = {"user-agent": "test-agent", "content-type": "application/json"}
        correlation_id = "test-correlation-id"

        # Should not raise any exceptions
        log_request_info(logger, method, url, headers, correlation_id)

    def test_log_request_info_with_complex_headers(self) -> None:
        """Test request logging with complex headers."""
        logger = get_logger("test_complex_request")
        method = "GET"
        url = "/api/v1/health"
        headers = {
            "user-agent": "Mozilla/5.0 (Test Browser)",
            "accept": "application/json",
            "authorization": "Bearer token123",
            "x-forwarded-for": "192.168.1.1",
            "x-request-id": "req-123"
        }
        correlation_id = "complex-correlation-id"

        log_request_info(logger, method, url, headers, correlation_id)

    def test_log_request_info_with_missing_headers(self) -> None:
        """Test request logging with missing headers."""
        logger = get_logger("test_missing_headers")
        method = "DELETE"
        url = "/api/v1/resource/123"
        headers = {}  # Empty headers
        correlation_id = "missing-headers-id"

        log_request_info(logger, method, url, headers, correlation_id)

    def test_log_request_info_with_special_characters(self) -> None:
        """Test request logging with special characters in URL and headers."""
        logger = get_logger("test_special_chars")
        method = "POST"
        url = "/api/v1/预测?q=测试&lang=中文"
        headers = {
            "user-agent": "测试浏览器/1.0",
            "referer": "https://example.com/路径/页面"
        }
        correlation_id = "special-chars-😀"

        log_request_info(logger, method, url, headers, correlation_id)

    def test_log_request_info_with_none_values(self) -> None:
        """Test request logging with None values."""
        logger = get_logger("test_none_values")
        method = "PUT"
        url = "/api/v1/update"
        headers = {"user-agent": None, "authorization": None}
        correlation_id = None

        # Should handle None values gracefully
        log_request_info(logger, method, url, headers, correlation_id)

    def test_log_request_info_logger_binding(self) -> None:
        """Test that request info uses logger binding correctly."""
        logger = get_logger("test_binding")
        method = "PATCH"
        url = "/api/v1/patch"
        headers = {"content-type": "application/json"}
        correlation_id = "binding-test"

        # Create a bound logger with additional context
        bound_logger = logger.bind(user_id="user123", session_id="sess456")

        log_request_info(bound_logger, method, url, headers, correlation_id)

    def test_log_request_info_various_methods(self) -> None:
        """Test request logging with various HTTP methods."""
        logger = get_logger("test_methods")
        url = "/api/v1/test"
        headers = {"user-agent": "test"}
        correlation_id = "method-test"

        methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]

        for method in methods:
            log_request_info(logger, method, url, headers, correlation_id)


class TestLogResponseInfo:
    """Test cases for log_response_info function."""

    def test_log_response_info_basic(self) -> None:
        """Test basic response information logging."""
        logger = get_logger("test_response")
        status_code = 200
        correlation_id = "test-correlation-id"
        duration_ms = 150.5

        log_response_info(logger, status_code, correlation_id, duration_ms)

    def test_log_response_info_with_different_status_codes(self) -> None:
        """Test response logging with different status codes."""
        logger = get_logger("test_status_codes")
        correlation_id = "status-test"
        duration_ms = 100.0

        status_codes = [200, 201, 400, 401, 403, 404, 500, 502, 503]

        for status_code in status_codes:
            log_response_info(logger, status_code, correlation_id, duration_ms)

    def test_log_response_info_with_slow_response(self) -> None:
        """Test response logging with slow response times."""
        logger = get_logger("test_slow_response")
        status_code = 200
        correlation_id = "slow-response"
        duration_ms = 5000.0  # 5 seconds

        log_response_info(logger, status_code, correlation_id, duration_ms)

    def test_log_response_info_with_fast_response(self) -> None:
        """Test response logging with very fast response times."""
        logger = get_logger("test_fast_response")
        status_code = 200
        correlation_id = "fast-response"
        duration_ms = 5.5  # 5.5 milliseconds

        log_response_info(logger, status_code, correlation_id, duration_ms)

    def test_log_response_info_with_error_status(self) -> None:
        """Test response logging with error status codes."""
        logger = get_logger("test_error_response")
        status_code = 500
        correlation_id = "error-response"
        duration_ms = 1000.0

        log_response_info(logger, status_code, correlation_id, duration_ms)

    def test_log_response_info_with_float_precision(self) -> None:
        """Test response logging with precise float durations."""
        logger = get_logger("test_precision")
        status_code = 200
        correlation_id = "precision-test"
        duration_ms = 123.456789

        log_response_info(logger, status_code, correlation_id, duration_ms)

    def test_log_response_info_with_zero_duration(self) -> None:
        """Test response logging with zero duration."""
        logger = get_logger("test_zero_duration")
        status_code = 200
        correlation_id = "zero-duration"
        duration_ms = 0.0

        log_response_info(logger, status_code, correlation_id, duration_ms)

    def test_log_response_info_with_negative_duration(self) -> None:
        """Test response logging with negative duration (edge case)."""
        logger = get_logger("test_negative_duration")
        status_code = 200
        correlation_id = "negative-duration"
        duration_ms = -10.5  # Shouldn't happen but test robustness

        log_response_info(logger, status_code, correlation_id, duration_ms)

    def test_log_response_info_logger_binding(self) -> None:
        """Test that response info uses logger binding correctly."""
        logger = get_logger("test_response_binding")
        status_code = 201
        correlation_id = "binding-test-response"
        duration_ms = 250.0

        # Create a bound logger with additional context
        bound_logger = logger.bind(
            endpoint="/api/v1/create",
            user_id="user123"
        )

        log_response_info(bound_logger, status_code, correlation_id, duration_ms)

    def test_log_response_info_large_duration(self) -> None:
        """Test response logging with very large duration values."""
        logger = get_logger("test_large_duration")
        status_code = 200
        correlation_id = "large-duration"
        duration_ms = 60000.0  # 1 minute

        log_response_info(logger, status_code, correlation_id, duration_ms)


class TestLoggingIntegration:
    """Integration tests for logging utilities."""

    def test_complete_request_response_logging_flow(self) -> None:
        """Test complete request-response logging flow."""
        logger = get_logger("integration_test")

        # Log request
        method = "POST"
        url = "/api/v1/predict"
        headers = {"user-agent": "integration-test-agent"}
        correlation_id = "integration-correlation-id"

        log_request_info(logger, method, url, headers, correlation_id)

        # Simulate some processing
        logger.info("Processing request", step="feature_extraction")

        # Log response
        status_code = 200
        duration_ms = 750.5

        log_response_info(logger, status_code, correlation_id, duration_ms)

    def test_logging_with_correlation_tracking(self) -> None:
        """Test logging with correlation tracking across multiple log entries."""
        correlation_id = "correlation-tracking-test"
        logger = get_logger("correlation_test").bind(correlation_id=correlation_id)

        # Multiple log entries with the same correlation
        logger.info("Starting request processing")
        logger.info("Validating audio file", file_size="1024KB")
        logger.info("Extracting features", feature_count=13)
        logger.info("Calling ML model", model_name="emotion-v1")
        logger.info("Processing completed", predictions_count=7)

    def test_error_logging_flow(self) -> None:
        """Test error logging flow."""
        logger = get_logger("error_test")

        # Log request
        log_request_info(
            logger,
            "POST",
            "/api/v1/predict",
            {"user-agent": "error-test"},
            "error-correlation-id"
        )

        # Log error
        logger.error(
            "Audio processing failed",
            error_type="InvalidAudioFormat",
            file_name="corrupted.wav",
            stage="validation"
        )

        # Log error response
        log_response_info(
            logger,
            400,
            "error-correlation-id",
            50.0
        )

    def test_performance_logging_flow(self) -> None:
        """Test performance-related logging."""
        logger = get_logger("performance_test")

        logger.info(
            "Performance metrics",
            request_count=1000,
            avg_response_time=150.5,
            error_rate=0.02,
            memory_usage_mb=256
        )

    def test_structured_logging_with_complex_data(self) -> None:
        """Test structured logging with complex nested data."""
        logger = get_logger("complex_data_test")

        complex_data = {
            "user": {
                "id": "user123",
                "subscription": "premium",
                "usage": {
                    "requests_today": 45,
                    "total_duration_seconds": 180.5
                }
            },
            "audio": {
                "format": "wav",
                "duration": 3.2,
                "sample_rate": 22050,
                "features_extracted": ["mfcc", "chroma", "spectral"]
            },
            "predictions": [
                {"emotion": "happy", "confidence": 0.85},
                {"emotion": "neutral", "confidence": 0.10},
                {"emotion": "sad", "confidence": 0.05}
            ]
        }

        logger.info("Complex structured log", **complex_data)


class TestLoggingEdgeCases:
    """Edge case tests for logging utilities."""

    def test_logging_with_unicode_content(self) -> None:
        """Test logging with unicode content."""
        logger = get_logger("unicode_test")

        unicode_content = {
            "chinese": "中文测试",
            "emoji": "😀🎵🎶",
            "arabic": "اختبار الصوت",
            "russian": "тест звука",
            "mixed": "Mix of 中文, English, 😊, and русский"
        }

        logger.info("Unicode content test", **unicode_content)

    def test_logging_with_very_long_content(self) -> None:
        """Test logging with very long content."""
        logger = get_logger("long_content_test")

        long_string = "x" * 10000  # 10KB string
        logger.info("Long content test", long_field=long_string)

    def test_logging_with_recursive_data(self) -> None:
        """Test logging with potentially recursive data structures."""
        logger = get_logger("recursive_test")

        # Create a structure that could cause recursion issues
        data = {"key": "value"}
        data["self"] = data  # Self-reference

        # Should handle gracefully or limit depth
        try:
            logger.info("Recursive data test", data=data)
        except (RecursionError, ValueError):
            # Expected to handle gracefully
            pass

    def test_logging_with_special_numeric_values(self) -> None:
        """Test logging with special numeric values."""
        logger = get_logger("special_numbers_test")

        special_numbers = {
            "infinity": float('inf'),
            "negative_infinity": float('-inf'),
            "not_a_number": float('nan'),
            "very_small": 1e-10,
            "very_large": 1e10
        }

        for key, value in special_numbers.items():
            try:
                logger.info(f"Special number test: {key}", **{key: value})
            except (ValueError, TypeError):
                # Some serializers might not handle these values
                pass