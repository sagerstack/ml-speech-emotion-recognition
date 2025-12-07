"""Model version value object."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelVersion:
    """Model version identifier.

    Represents a semantic version for ML models (e.g., 'v4', 'v3').
    This is an immutable value object that ensures version strings
    follow the expected format.

    Attributes:
        version: Version string (e.g., 'v4')
    """

    version: str

    def __post_init__(self) -> None:
        """Validate model version format."""
        if not isinstance(self.version, str):
            raise ValueError(f"Version must be a string, got {type(self.version)}")

        if not self.version:
            raise ValueError("Version cannot be empty")

        # Version should match pattern: v{number} (e.g., v1, v2, v3, v4)
        pattern = r"^v\d+$"
        if not re.match(pattern, self.version):
            raise ValueError(f"Version must match pattern 'vN' (e.g., 'v4'), got '{self.version}'")

    @classmethod
    def from_string(cls, version_str: str) -> "ModelVersion":
        """Create ModelVersion from string.

        Args:
            version_str: Version string (e.g., 'v4', '4')

        Returns:
            ModelVersion instance

        Raises:
            ValueError: If version string is invalid
        """
        # Add 'v' prefix if not present
        if version_str and not version_str.startswith("v"):
            version_str = f"v{version_str}"

        return cls(version=version_str)

    @classmethod
    def from_number(cls, version_number: int) -> "ModelVersion":
        """Create ModelVersion from version number.

        Args:
            version_number: Version number (e.g., 4 for 'v4')

        Returns:
            ModelVersion instance

        Raises:
            ValueError: If version number is invalid
        """
        if not isinstance(version_number, int) or version_number < 1:
            raise ValueError(f"Version number must be a positive integer, got {version_number}")

        return cls(version=f"v{version_number}")

    def get_number(self) -> int:
        """Extract version number from version string.

        Returns:
            Version number (e.g., 4 from 'v4')
        """
        return int(self.version[1:])

    def __str__(self) -> str:
        """String representation."""
        return self.version

    def __lt__(self, other: "ModelVersion") -> bool:
        """Compare versions (less than)."""
        if not isinstance(other, ModelVersion):
            return NotImplemented
        return self.get_number() < other.get_number()

    def __gt__(self, other: "ModelVersion") -> bool:
        """Compare versions (greater than)."""
        if not isinstance(other, ModelVersion):
            return NotImplemented
        return self.get_number() > other.get_number()

    def __le__(self, other: "ModelVersion") -> bool:
        """Compare versions (less than or equal)."""
        if not isinstance(other, ModelVersion):
            return NotImplemented
        return self.get_number() <= other.get_number()

    def __ge__(self, other: "ModelVersion") -> bool:
        """Compare versions (greater than or equal)."""
        if not isinstance(other, ModelVersion):
            return NotImplemented
        return self.get_number() >= other.get_number()
