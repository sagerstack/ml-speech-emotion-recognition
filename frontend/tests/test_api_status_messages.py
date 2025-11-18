"""
Tests for HTTP status code to user message mapping
"""

import pytest
import sys
from pathlib import Path

# Add fixtures path
fixtures_path = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(fixtures_path))

from mock_responses import get_status_message, HTTP_STATUS_MESSAGES


class TestHTTPStatusMessages:
    """Test HTTP status code to user message mapping"""

    def test_get_status_message_200(self):
        """Test success message for 200 OK"""
        message = get_status_message(200)
        assert message["type"] == "success"
        assert "✅" in message["message"]
        assert "successful" in message["message"].lower()

    def test_get_status_message_400(self):
        """Test error message for 400 Bad Request"""
        message = get_status_message(400)
        assert message["type"] == "error"
        assert "❌" in message["message"]
        assert "bad request" in message["message"].lower()

    def test_get_status_message_404(self):
        """Test error message for 404 Not Found"""
        message = get_status_message(404)
        assert message["type"] == "error"
        assert "❌" in message["message"]
        assert "not found" in message["message"].lower()

    def test_get_status_message_500(self):
        """Test error message for 500 Internal Server Error"""
        message = get_status_message(500)
        assert message["type"] == "error"
        assert "❌" in message["message"]
        assert "server error" in message["message"].lower()

    def test_get_status_message_503(self):
        """Test error message for 503 Service Unavailable"""
        message = get_status_message(503)
        assert message["type"] == "error"
        assert "❌" in message["message"]
        assert "unavailable" in message["message"].lower()

    def test_get_status_message_connection_error(self):
        """Test error message for connection error"""
        message = get_status_message("connection_error")
        assert message["type"] == "error"
        assert "❌" in message["message"]
        assert "connection failed" in message["message"].lower()

    def test_get_status_message_timeout(self):
        """Test error message for timeout"""
        message = get_status_message("timeout")
        assert message["type"] == "error"
        assert "❌" in message["message"]
        assert "timeout" in message["message"].lower()

    def test_get_status_message_unknown(self):
        """Test error message for unknown error"""
        message = get_status_message(999)
        assert message["type"] == "error"
        assert "❌" in message["message"]
        assert "unknown error" in message["message"].lower()

    def test_http_status_messages_completeness(self):
        """Test that HTTP_STATUS_MESSAGES has required entries"""
        # Test common status codes
        common_codes = [200, 400, 401, 403, 404, 500, 503]
        for code in common_codes:
            assert code in HTTP_STATUS_MESSAGES
            assert "type" in HTTP_STATUS_MESSAGES[code]
            assert "message" in HTTP_STATUS_MESSAGES[code]

        # Test error types
        assert "connection_error" in HTTP_STATUS_MESSAGES
        assert "timeout" in HTTP_STATUS_MESSAGES
        assert "unknown_error" in HTTP_STATUS_MESSAGES

    def test_status_message_structure(self):
        """Test that all status messages have required structure"""
        for key, message in HTTP_STATUS_MESSAGES.items():
            assert "type" in message
            assert "message" in message
            assert message["type"] in ["success", "error"]
            assert isinstance(message["message"], str)
            assert len(message["message"]) > 0

    def test_success_messages_have_checkmark(self):
        """Test that success messages contain checkmark emoji"""
        success_messages = [
            (code, msg) for code, msg in HTTP_STATUS_MESSAGES.items()
            if msg["type"] == "success"
        ]

        for code, message in success_messages:
            assert "✅" in message["message"]

    def test_error_messages_have_x_mark(self):
        """Test that error messages contain X mark emoji"""
        error_messages = [
            (code, msg) for code, msg in HTTP_STATUS_MESSAGES.items()
            if msg["type"] == "error"
        ]

        for code, message in error_messages:
            assert "❌" in message["message"]

    def test_connection_scenarios(self):
        """Test connection-related error scenarios"""
        connection_scenarios = ["connection_error", "timeout", "network_error"]

        for scenario in connection_scenarios:
            message = get_status_message(scenario)
            assert message["type"] == "error"
            assert "❌" in message["message"]
            # Should mention connection/network in some way
            lowered = message["message"].lower()
            assert any(word in lowered for word in ["connection", "network", "timeout"])

    @pytest.mark.parametrize("status_code,expected_type", [
        (200, "success"),
        (201, "success"),
        (400, "error"),
        (401, "error"),
        (403, "error"),
        (404, "error"),
        (500, "error"),
        (502, "error"),
        (503, "error"),
        (504, "error")
    ])
    def test_status_code_types(self, status_code, expected_type):
        """Test that status codes have correct types"""
        message = get_status_message(status_code)
        assert message["type"] == expected_type