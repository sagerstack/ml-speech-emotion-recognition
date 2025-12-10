"""
Unit tests for file validation utilities.

Tests magic byte detection, file type validation, and format-specific validation.
"""

import pytest

from app.infrastructure.validation.file_validation import (
    _validate_flac_file,
    _validate_mp3_file,
    _validate_mp4_file,
    _validate_wav_file,
    detect_file_type_by_magic_bytes,
    validate_audio_file,
)


class TestDetectFileTypeByMagicBytes:
    """Test file type detection by magic bytes."""

    def test_detect_wav_file(self):
        """Test detecting WAV files."""
        # WAV file signature
        wav_data = b"RIFF\x00\x00\x00\x00WAVEfmt "
        result = detect_file_type_by_magic_bytes(wav_data)
        assert result == "audio/wav"

    def test_detect_mp3_with_id3(self):
        """Test detecting MP3 files with ID3 tag."""
        mp3_data = b"ID3\x03\x00\x00\x00" + b"\x00" * 100
        result = detect_file_type_by_magic_bytes(mp3_data)
        assert result == "audio/mpeg"

    def test_detect_mp3_with_sync_header(self):
        """Test detecting MP3 files with MPEG sync header."""
        # MPEG sync header: 0xFF 0xFB
        mp3_data = b"\xff\xfb" + b"\x00" * 100
        result = detect_file_type_by_magic_bytes(mp3_data)
        assert result == "audio/mpeg"

    def test_detect_mp3_with_alternate_sync(self):
        """Test detecting MP3 with alternate sync patterns."""
        # Test 0xFF 0xF3
        mp3_data1 = b"\xff\xf3" + b"\x00" * 100
        assert detect_file_type_by_magic_bytes(mp3_data1) == "audio/mpeg"

        # Test 0xFF 0xF2
        mp3_data2 = b"\xff\xf2" + b"\x00" * 100
        assert detect_file_type_by_magic_bytes(mp3_data2) == "audio/mpeg"

        # Test 0xFF 0xE0 (valid MPEG sync pattern)
        mp3_data3 = b"\xff\xe0" + b"\x00" * 100
        assert detect_file_type_by_magic_bytes(mp3_data3) == "audio/mpeg"

    def test_detect_flac_file(self):
        """Test detecting FLAC files."""
        flac_data = b"fLaC" + b"\x00" * 100
        result = detect_file_type_by_magic_bytes(flac_data)
        assert result == "audio/flac"

    def test_detect_mp4_file(self):
        """Test detecting MP4/M4A files."""
        # MP4 format: "ftyp" then 4 bytes padding, then brand at position 8
        mp4_data = b"ftyp\x00\x00\x00\x00M4A " + b"\x00" * 100
        result = detect_file_type_by_magic_bytes(mp4_data)
        assert result == "audio/mp4"

    def test_detect_empty_file(self):
        """Test detecting empty file."""
        result = detect_file_type_by_magic_bytes(b"")
        assert result is None

    def test_detect_file_too_short(self):
        """Test detecting file with insufficient data."""
        result = detect_file_type_by_magic_bytes(b"ID")
        assert result is None

    def test_detect_unknown_format(self):
        """Test detecting unknown file format."""
        unknown_data = b"UNKNOWN" + b"\x00" * 100
        result = detect_file_type_by_magic_bytes(unknown_data)
        assert result is None

    def test_detect_wav_without_wave_marker(self):
        """Test RIFF file that's not a WAV."""
        # RIFF but not WAVE
        riff_data = b"RIFF\x00\x00\x00\x00OTHR"
        result = detect_file_type_by_magic_bytes(riff_data)
        assert result is None

    def test_detect_mp4_with_different_brands(self):
        """Test detecting MP4 with different brand markers."""
        # Test mp41 brand
        mp4_data1 = b"ftyp\x00\x00\x00\x00mp41" + b"\x00" * 100
        assert detect_file_type_by_magic_bytes(mp4_data1) == "audio/mp4"

        # Test mp42 brand
        mp4_data2 = b"ftyp\x00\x00\x00\x00mp42" + b"\x00" * 100
        assert detect_file_type_by_magic_bytes(mp4_data2) == "audio/mp4"

        # Test isom brand
        mp4_data3 = b"ftyp\x00\x00\x00\x00isom" + b"\x00" * 100
        assert detect_file_type_by_magic_bytes(mp4_data3) == "audio/mp4"


class TestValidateAudioFile:
    """Test audio file validation."""

    def test_validate_wav_file_success(self):
        """Test successful WAV file validation."""
        wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * 30
        is_valid, error = validate_audio_file(wav_data, "audio/wav", max_size_mb=30)
        assert is_valid is True
        assert error == ""

    def test_validate_mp3_file_success(self):
        """Test successful MP3 file validation."""
        mp3_data = b"ID3\x03\x00\x00\x00" + b"\x00" * 100
        is_valid, error = validate_audio_file(mp3_data, "audio/mpeg", max_size_mb=30)
        assert is_valid is True
        assert error == ""

    def test_validate_flac_file_success(self):
        """Test successful FLAC file validation."""
        flac_data = b"fLaC" + b"\x00" * 100
        is_valid, error = validate_audio_file(flac_data, "audio/flac", max_size_mb=30)
        assert is_valid is True
        assert error == ""

    def test_validate_m4a_file_success(self):
        """Test successful M4A file validation."""
        m4a_data = b"ftyp\x00\x00\x00\x00M4A " + b"\x00" * 100
        is_valid, error = validate_audio_file(m4a_data, "audio/m4a", max_size_mb=30)
        assert is_valid is True
        assert error == ""

    def test_validate_file_exceeds_size_limit(self):
        """Test validation fails for oversized file."""
        large_data = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * (5 * 1024 * 1024)
        is_valid, error = validate_audio_file(large_data, "audio/wav", max_size_mb=1)
        assert is_valid is False
        assert "exceeds maximum allowed size" in error

    def test_validate_empty_file(self):
        """Test validation fails for empty file."""
        is_valid, error = validate_audio_file(b"", "audio/wav", max_size_mb=30)
        assert is_valid is False
        assert "File is empty" in error

    def test_validate_file_type_mismatch(self):
        """Test validation fails for file type mismatch."""
        # Declare as WAV but actually MP3
        mp3_data = b"ID3\x03\x00\x00\x00" + b"\x00" * 100
        is_valid, error = validate_audio_file(mp3_data, "audio/wav", max_size_mb=30)
        assert is_valid is False
        assert "File type mismatch" in error

    def test_validate_corrupted_file(self):
        """Test validation fails for corrupted/unknown file."""
        corrupted_data = b"CORRUPTED DATA" + b"\x00" * 100
        is_valid, error = validate_audio_file(corrupted_data, "audio/wav", max_size_mb=30)
        assert is_valid is False
        assert "Unable to determine file type" in error

    def test_validate_wav_with_alternative_content_types(self):
        """Test WAV validation with different content type declarations."""
        wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * 30

        # Test audio/wave
        is_valid, _ = validate_audio_file(wav_data, "audio/wave", max_size_mb=30)
        assert is_valid is True

        # Test audio/x-wav
        is_valid, _ = validate_audio_file(wav_data, "audio/x-wav", max_size_mb=30)
        assert is_valid is True

    def test_validate_mp3_with_alternative_content_types(self):
        """Test MP3 validation with different content type declarations."""
        mp3_data = b"ID3\x03\x00\x00\x00" + b"\x00" * 100

        # Test audio/mp3
        is_valid, _ = validate_audio_file(mp3_data, "audio/mp3", max_size_mb=30)
        assert is_valid is True

        # Test audio/mpeg3
        is_valid, _ = validate_audio_file(mp3_data, "audio/mpeg3", max_size_mb=30)
        assert is_valid is True

        # Test audio/mpg
        is_valid, _ = validate_audio_file(mp3_data, "audio/mpg", max_size_mb=30)
        assert is_valid is True

    def test_validate_m4a_with_alternative_content_types(self):
        """Test M4A validation with different content type declarations."""
        m4a_data = b"ftyp\x00\x00\x00\x00M4A " + b"\x00" * 100

        # Test audio/x-m4a
        is_valid, _ = validate_audio_file(m4a_data, "audio/x-m4a", max_size_mb=30)
        assert is_valid is True

        # Test audio/mp4
        is_valid, _ = validate_audio_file(m4a_data, "audio/mp4", max_size_mb=30)
        assert is_valid is True


class TestValidateWavFile:
    """Test WAV-specific validation."""

    def test_validate_wav_file_valid(self):
        """Test valid WAV file."""
        wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * 30
        assert _validate_wav_file(wav_data) is True

    def test_validate_wav_file_too_short(self):
        """Test WAV file that's too short."""
        wav_data = b"RIFF\x00\x00\x00\x00WAVE"
        assert _validate_wav_file(wav_data) is False

    def test_validate_wav_file_missing_riff(self):
        """Test WAV file without RIFF header."""
        wav_data = b"XXXX\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * 30
        assert _validate_wav_file(wav_data) is False

    def test_validate_wav_file_missing_wave(self):
        """Test WAV file without WAVE marker."""
        wav_data = b"RIFF\x24\x00\x00\x00XXXXfmt \x10\x00\x00\x00" + b"\x00" * 30
        assert _validate_wav_file(wav_data) is False

    def test_validate_wav_file_missing_fmt(self):
        """Test WAV file without fmt chunk."""
        wav_data = b"RIFF\x24\x00\x00\x00WAVExxxx\x10\x00\x00\x00" + b"\x00" * 30
        assert _validate_wav_file(wav_data) is False


class TestValidateMp3File:
    """Test MP3-specific validation."""

    def test_validate_mp3_file_with_id3(self):
        """Test valid MP3 with ID3 tag."""
        mp3_data = b"ID3\x03\x00\x00\x00" + b"\x00" * 100
        assert _validate_mp3_file(mp3_data) is True

    def test_validate_mp3_file_with_sync_header(self):
        """Test valid MP3 with MPEG sync header."""
        mp3_data = b"\xff\xfb" + b"\x00" * 100
        assert _validate_mp3_file(mp3_data) is True

    def test_validate_mp3_file_too_short(self):
        """Test MP3 file that's too short."""
        mp3_data = b"ID"
        assert _validate_mp3_file(mp3_data) is False

    def test_validate_mp3_file_invalid(self):
        """Test invalid MP3 file."""
        mp3_data = b"NOTMP3" + b"\x00" * 100
        assert _validate_mp3_file(mp3_data) is False

    def test_validate_mp3_file_with_various_sync_patterns(self):
        """Test MP3 with various valid sync patterns."""
        # 0xFF 0xE0 - 0xFF 0xFF are all valid MPEG sync patterns
        for second_byte in range(0xE0, 0x100):
            mp3_data = bytes([0xFF, second_byte]) + b"\x00" * 100
            assert _validate_mp3_file(mp3_data) is True


class TestValidateFlacFile:
    """Test FLAC-specific validation."""

    def test_validate_flac_file_valid(self):
        """Test valid FLAC file."""
        flac_data = b"fLaC" + b"\x00" * 100
        assert _validate_flac_file(flac_data) is True

    def test_validate_flac_file_too_short(self):
        """Test FLAC file that's too short."""
        flac_data = b"fL"
        assert _validate_flac_file(flac_data) is False

    def test_validate_flac_file_invalid(self):
        """Test invalid FLAC file."""
        flac_data = b"XXXX" + b"\x00" * 100
        assert _validate_flac_file(flac_data) is False


class TestValidateMp4File:
    """Test MP4/M4A-specific validation."""

    def test_validate_mp4_file_valid(self):
        """Test valid MP4 file."""
        mp4_data = b"ftypM4A " + b"\x00" * 100
        assert _validate_mp4_file(mp4_data) is True

    def test_validate_mp4_file_too_short(self):
        """Test MP4 file that's too short."""
        mp4_data = b"ftyp"
        assert _validate_mp4_file(mp4_data) is False

    def test_validate_mp4_file_invalid(self):
        """Test invalid MP4 file."""
        mp4_data = b"XXXXM4A " + b"\x00" * 100
        assert _validate_mp4_file(mp4_data) is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_validate_file_at_exact_size_limit(self):
        """Test file exactly at size limit."""
        # Create file of exactly 1MB
        size_bytes = 1 * 1024 * 1024
        wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * (
            size_bytes - 44
        )
        is_valid, _ = validate_audio_file(wav_data, "audio/wav", max_size_mb=1)
        assert is_valid is True

    def test_validate_file_just_over_size_limit(self):
        """Test file just over size limit."""
        # Create file slightly over 1MB
        size_bytes = 1 * 1024 * 1024 + 1024  # Add extra to ensure it's clearly over
        wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * (
            size_bytes - 44
        )
        is_valid, error = validate_audio_file(wav_data, "audio/wav", max_size_mb=1)
        assert is_valid is False
        assert "exceeds maximum allowed size" in error

    def test_validate_minimal_wav_file(self):
        """Test minimal valid WAV file."""
        # Minimum valid WAV: 44 bytes
        wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * 30
        is_valid, _ = validate_audio_file(wav_data, "audio/wav", max_size_mb=30)
        assert is_valid is True

    def test_validate_flac_with_x_prefix(self):
        """Test FLAC with x-flac content type."""
        flac_data = b"fLaC" + b"\x00" * 100
        is_valid, _ = validate_audio_file(flac_data, "audio/x-flac", max_size_mb=30)
        assert is_valid is True

    def test_validate_with_different_max_sizes(self):
        """Test validation with various max size limits."""
        wav_data = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00" + b"\x00" * 1000

        # Test with various size limits
        for max_size in [1, 5, 10, 30, 50, 100]:
            is_valid, _ = validate_audio_file(wav_data, "audio/wav", max_size_mb=max_size)
            assert is_valid is True

    def test_validate_mp3_without_id3_with_sync(self):
        """Test MP3 without ID3 tag but with valid sync header."""
        # MP3 with just sync header, no ID3
        mp3_data = b"\xff\xfb\x90\x00" + b"\x00" * 100
        is_valid, _ = validate_audio_file(mp3_data, "audio/mpeg", max_size_mb=30)
        assert is_valid is True
