"""
Mock response fixtures for API testing with different HTTP status codes
"""

import json
from typing import Dict, Any


class MockAPIResponses:
    """Factory for creating mock API responses with different status codes"""

    @staticmethod
    def health_check_response(status_code: int = 200) -> Dict[str, Any]:
        """Create mock health check response"""
        if status_code == 200:
            return {
                "status_code": status_code,
                "json": {
                    "status": "healthy",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "version": "1.0.0",
                    "uptime": 3600,
                    "checks": {
                        "database": "pass",
                        "sagemaker": "pass",
                        "storage": "pass"
                    }
                }
            }
        elif status_code == 503:
            return {
                "status_code": status_code,
                "json": {
                    "status": "unhealthy",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "error": "Service temporarily unavailable",
                    "checks": {
                        "database": "pass",
                        "sagemaker": "fail",
                        "storage": "pass"
                    }
                }
            }
        elif status_code == 500:
            return {
                "status_code": status_code,
                "json": {
                    "status": "error",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "error": "Internal server error"
                }
            }
        else:
            return {"status_code": status_code}

    @staticmethod
    def prediction_response(status_code: int = 200) -> Dict[str, Any]:
        """Create mock emotion prediction response"""
        if status_code == 200:
            return {
                "status_code": status_code,
                "json": {
                    "emotion": "happy",
                    "confidence": 0.85,
                    "probabilities": {
                        "happy": 0.85,
                        "neutral": 0.10,
                        "sad": 0.03,
                        "angry": 0.01,
                        "fearful": 0.005,
                        "disgusted": 0.005
                    },
                    "processing_time": 1.23,
                    "model_info": {
                        "name": "emotion-recognition-v1",
                        "version": "1.0.0",
                        "accuracy": 0.92
                    }
                }
            }
        elif status_code == 400:
            return {
                "status_code": status_code,
                "json": {
                    "detail": "Invalid audio format. Supported formats: wav, mp3, flac, m4a"
                }
            }
        elif status_code == 413:
            return {
                "status_code": status_code,
                "json": {
                    "detail": "File too large. Maximum size: 25MB"
                }
            }
        elif status_code == 500:
            return {
                "status_code": status_code,
                "json": {
                    "detail": "Internal server error during emotion prediction"
                }
            }
        else:
            return {"status_code": status_code}

    @staticmethod
    def supported_formats_response(status_code: int = 200) -> Dict[str, Any]:
        """Create mock supported formats response"""
        if status_code == 200:
            return {
                "status_code": status_code,
                "json": {
                    "supported_formats": ["wav", "mp3", "flac", "m4a"],
                    "max_file_size": 25000000,
                    "max_duration": 30,
                    "sample_rate": 22050
                }
            }
        else:
            return {"status_code": status_code}

    @staticmethod
    def model_info_response(status_code: int = 200) -> Dict[str, Any]:
        """Create mock model info response"""
        if status_code == 200:
            return {
                "status_code": status_code,
                "json": {
                    "model_name": "emotion-recognition-v1",
                    "version": "1.0.0",
                    "supported_emotions": ["happy", "sad", "angry", "fearful", "disgusted", "neutral"],
                    "accuracy": 0.92,
                    "training_data": "CREMA-D",
                    "last_updated": "2024-01-01T00:00:00Z"
                }
            }
        else:
            return {"status_code": status_code}


# HTTP status code to user message mapping
HTTP_STATUS_MESSAGES = {
    200: {
        "type": "success",
        "message": "✅ API connection successful!"
    },
    201: {
        "type": "success",
        "message": "✅ Resource created successfully!"
    },
    400: {
        "type": "error",
        "message": "❌ Bad request - Invalid input or parameters"
    },
    401: {
        "type": "error",
        "message": "❌ Unauthorized - Authentication required"
    },
    403: {
        "type": "error",
        "message": "❌ Forbidden - Access denied"
    },
    404: {
        "type": "error",
        "message": "❌ API endpoint not found"
    },
    405: {
        "type": "error",
        "message": "❌ Method not allowed"
    },
    408: {
        "type": "error",
        "message": "❌ Request timeout"
    },
    413: {
        "type": "error",
        "message": "❌ File too large - Check file size limits"
    },
    415: {
        "type": "error",
        "message": "❌ Unsupported media type - Check file format"
    },
    422: {
        "type": "error",
        "message": "❌ Unprocessable entity - Invalid data format"
    },
    429: {
        "type": "error",
        "message": "❌ Too many requests - Rate limit exceeded"
    },
    500: {
        "type": "error",
        "message": "❌ Internal server error"
    },
    502: {
        "type": "error",
        "message": "❌ Bad gateway - Backend service unavailable"
    },
    503: {
        "type": "error",
        "message": "❌ Service temporarily unavailable"
    },
    504: {
        "type": "error",
        "message": "❌ Gateway timeout"
    },
    "connection_error": {
        "type": "error",
        "message": "❌ Connection failed - Unable to reach server"
    },
    "timeout": {
        "type": "error",
        "message": "❌ Request timeout - Server took too long to respond"
    },
    "network_error": {
        "type": "error",
        "message": "❌ Network error - Check your internet connection"
    },
    "unknown_error": {
        "type": "error",
        "message": "❌ Unknown error occurred"
    }
}


def get_status_message(status_code: int or str) -> Dict[str, str]:
    """Get appropriate user message for HTTP status code"""
    return HTTP_STATUS_MESSAGES.get(status_code, HTTP_STATUS_MESSAGES["unknown_error"])


def create_error_response(status_code: int, detail: str = None) -> Dict[str, Any]:
    """Create standardized error response"""
    message_info = get_status_message(status_code)

    response = {
        "status": "error",
        "status_code": status_code,
        "message": message_info["message"],
        "type": message_info["type"]
    }

    if detail:
        response["detail"] = detail

    return response


def create_success_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create standardized success response"""
    return {
        "status": "success",
        "status_code": 200,
        "type": "success",
        "data": data
    }