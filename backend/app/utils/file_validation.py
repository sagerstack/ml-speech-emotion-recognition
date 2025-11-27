"""
File validation utilities for audio files.

This module provides enhanced file validation including magic byte detection
to prevent file type spoofing and improve security.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Magic byte signatures for supported audio formats
MAGIC_BYTES = {
    "audio/wav": b"RIFF",
    "audio/wave": b"RIFF",
    "audio/x-wav": b"RIFF",
    "audio/mp3": b"ID3",
    "audio/mpeg": b"ID3",
    "audio/mpeg3": b"ID3",
    "audio/mpg": b"ID3",
    "audio/flac": b"fLaC",
    "audio/x-flac": b"fLaC",
    "audio/mp4": b"ftyp",
    "audio/x-m4a": b"ftyp",
    "audio/m4a": b"ftyp",
    # Additional signatures for files without ID3 tags
    "audio/mp3_sync": b"\xff\xfb",  # MP3 sync header
    "audio/mp3_sync2": b"\xff\xf3",  # MP3 sync header alternative
    "audio/mp3_sync3": b"\xff\xf2",  # MP3 sync header alternative
}


def detect_file_type_by_magic_bytes(file_data: bytes) -> Optional[str]:
    """
    Detect file type based on magic bytes (file signature).

    Args:
        file_data: Raw file data as bytes

    Returns:
        Detected MIME type or None if unknown
    """
    if not file_data or len(file_data) < 4:
        return None

    # Check for RIFF (WAV)
    if file_data.startswith(b"RIFF"):
        if len(file_data) > 12:
            # Check for WAVE format
            if file_data[8:12] == b"WAVE":
                return "audio/wav"

    # Check for ID3 (MP3)
    elif file_data.startswith(b"ID3"):
        return "audio/mpeg"

    # Check for FLAC
    elif file_data.startswith(b"fLaC"):
        return "audio/flac"

    # Check for MP4/M4A
    elif file_data.startswith(b"ftyp"):
        # Check for M4A brand
        if len(file_data) > 8:
            brand = file_data[8:12]
            if brand in [b"M4A ", b"mp41", b"mp42", b"isom"]:
                return "audio/mp4"

    # Check for MP3 sync headers (no ID3 tag)
    elif len(file_data) >= 2:
        # Check for MPEG sync bytes
        if (file_data[0] == 0xFF and
            file_data[1] & 0xE0 == 0xE0):  # MPEG sync pattern
            return "audio/mpeg"

    return None


def validate_audio_file(
    file_data: bytes,
    declared_content_type: str,
    max_size_mb: int = 30
) -> Tuple[bool, str]:
    """
    Enhanced audio file validation including magic byte verification.

    Args:
        file_data: Raw file data as bytes
        declared_content_type: Content type from HTTP header
        max_size_mb: Maximum allowed file size in MB

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check file size
    if len(file_data) > max_size_mb * 1024 * 1024:
        return False, f"File size exceeds maximum allowed size of {max_size_mb}MB"

    if len(file_data) == 0:
        return False, "File is empty"

    # Detect actual file type from magic bytes
    detected_type = detect_file_type_by_magic_bytes(file_data)

    if detected_type is None:
        return False, "Unable to determine file type. File may be corrupted or unsupported."

    # Map content types to detected types
    content_type_mapping = {
        "audio/wav": ["audio/wav"],
        "audio/wave": ["audio/wav"],
        "audio/x-wav": ["audio/wav"],
        "audio/mp3": ["audio/mpeg"],
        "audio/mpeg": ["audio/mpeg"],
        "audio/mpeg3": ["audio/mpeg"],
        "audio/mpg": ["audio/mpeg"],
        "audio/flac": ["audio/flac"],
        "audio/x-flac": ["audio/flac"],
        "audio/m4a": ["audio/mp4"],
        "audio/x-m4a": ["audio/mp4"],
        "audio/mp4": ["audio/mp4"],
    }

    # Check if declared content type matches detected type
    expected_detected_types = content_type_mapping.get(declared_content_type, [declared_content_type])

    if detected_type not in expected_detected_types:
        logger.warning(
            "File type mismatch detected",
            declared_type=declared_content_type,
            detected_type=detected_type,
            file_signature=file_data[:16].hex() if file_data else None
        )
        return False, (
            f"File type mismatch. Declared as {declared_content_type} "
            f"but detected as {detected_type}."
        )

    # Additional validation based on format
    if detected_type == "audio/wav":
        if not _validate_wav_file(file_data):
            return False, "Invalid WAV file format"

    elif detected_type == "audio/mpeg":
        if not _validate_mp3_file(file_data):
            return False, "Invalid MP3 file format"

    elif detected_type == "audio/flac":
        if not _validate_flac_file(file_data):
            return False, "Invalid FLAC file format"

    elif detected_type == "audio/mp4":
        if not _validate_mp4_file(file_data):
            return False, "Invalid M4A/MP4 file format"

    return True, ""


def _validate_wav_file(file_data: bytes) -> bool:
    """Validate WAV file structure."""
    if len(file_data) < 44:  # Minimum WAV header size
        return False

    # Check RIFF header
    if not file_data.startswith(b"RIFF"):
        return False

    # Check WAVE format
    if file_data[8:12] != b"WAVE":
        return False

    # Check fmt chunk
    if file_data[12:16] != b"fmt ":
        return False

    return True


def _validate_mp3_file(file_data: bytes) -> bool:
    """Validate MP3 file structure."""
    if len(file_data) < 4:
        return False

    # Check for ID3v2 tag
    if file_data.startswith(b"ID3"):
        return True

    # Check for MPEG sync header
    if len(file_data) >= 2:
        if (file_data[0] == 0xFF and
            file_data[1] & 0xE0 == 0xE0):
            return True

    return False


def _validate_flac_file(file_data: bytes) -> bool:
    """Validate FLAC file structure."""
    if len(file_data) < 4:
        return False

    return file_data.startswith(b"fLaC")


def _validate_mp4_file(file_data: bytes) -> bool:
    """Validate MP4/M4A file structure."""
    if len(file_data) < 12:
        return False

    return file_data.startswith(b"ftyp")