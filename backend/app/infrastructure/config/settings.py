"""
Configuration management for ML Speech Emotion Recognition API

Uses Pydantic Settings for environment-based configuration with proper defaults.
Designed for local development first, then AWS deployment.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    model_config = SettingsConfigDict(
        env_file=".env.local",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        env_ignore_empty=True,
    )

    # Application Configuration
    app_name: str = "ML Speech Emotion Recognition API"
    app_version: str = "1.0.0"
    debug: bool = False

    # API Configuration
    api_v1_str: str = "/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    # AWS Configuration (us-east-1 as per user decision)
    aws_region: str = "us-east-1"
    sagemaker_endpoint_name: str = "speech-emotion-1763484306"

    # Security Configuration
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Audio Processing Configuration
    max_upload_size_mb: int = 30
    max_audio_duration_seconds: int = 30
    supported_formats: list[str] = ["wav", "mp3", "m4a"]

    # Local Model Configuration
    models_dir: str = "models"  # Relative to backend directory

    # S3 Configuration for temporary audio storage
    s3_bucket_name: str | None = None
    s3_temp_prefix: str = "temp-audio/"

    # Performance Configuration
    max_concurrent_requests: int = 50
    request_timeout_seconds: int = 60

    # Monitoring Configuration
    prometheus_enabled: bool = True
    metrics_port: int = 9090
    monitoring_reference_path: str | None = None
    monitoring_reports_dir: str = "monitoring_reports"
    monitoring_buffer_max_records: int = 500
    monitoring_auto_report_threshold: int = 100
    evidently_workspace_path: str = "evidently_workspace"
    evidently_project_name: str = "speech_emotion_recognition"
    evidently_dashboard_url: str | None = None
    enable_inference_monitoring_by_default: bool = False

    # CORS Configuration (for local development)
    cors_origins: list[str] = [
        "http://localhost:3000",  # React dashboard
        "http://localhost:8501",  # Streamlit interface
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8501",
    ]

    # Audio Features Feature Flags
    ENABLE_INFERENCE_AUDIO_FEATURES: bool = False
    LOG_AUDIO_FEATURES_METRICS: bool = True

    @field_validator("request_timeout_seconds")
    @classmethod
    def validate_timeout(cls, v):
        if v <= 0:
            raise ValueError("Request timeout must be positive")
        return v

    @field_validator("max_upload_size_mb")
    @classmethod
    def validate_upload_size(cls, v):
        if v <= 0:
            raise ValueError("Max upload size must be positive")
        return v

    @field_validator("max_audio_duration_seconds")
    @classmethod
    def validate_audio_duration(cls, v):
        if v <= 0:
            raise ValueError("Max audio duration must be positive")
        return v

    @field_validator("max_concurrent_requests")
    @classmethod
    def validate_concurrent_requests(cls, v):
        if v <= 0:
            raise ValueError("Max concurrent requests must be positive")
        return v

    @field_validator("monitoring_buffer_max_records", "monitoring_auto_report_threshold")
    @classmethod
    def validate_monitoring_thresholds(cls, v):
        if v <= 0:
            raise ValueError("Monitoring thresholds must be positive")
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        if not v or v.strip() == "":
            raise ValueError("SECRET_KEY environment variable must be set and non-empty")
        return v

    @field_validator("access_token_expire_minutes")
    @classmethod
    def validate_token_expiry(cls, v):
        if v <= 0:
            raise ValueError("Access token expiry must be positive")
        return v


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create global settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
