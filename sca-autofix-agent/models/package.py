"""
Package-related data models.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PackageEcosystem(str, Enum):
    """Supported package ecosystems."""

    PYTHON = "python"
    JAVA = "java"
    JAVASCRIPT = "javascript"
    R = "r"
    GO = "go"


class PackageVersion(BaseModel):
    """Represents a specific version of a package."""

    version: str = Field(description="Version string (e.g., '2.28.0')")
    release_date: Optional[str] = Field(None, description="Release date (ISO format)")
    is_yanked: bool = Field(False, description="Whether version was yanked/deprecated")


class Package(BaseModel):
    """Represents a software package."""

    name: str = Field(description="Package name")
    ecosystem: PackageEcosystem = Field(description="Package ecosystem (python, java, etc.)")
    current_version: str = Field(description="Currently installed version")
    latest_version: Optional[str] = Field(None, description="Latest available version")
    homepage: Optional[str] = Field(None, description="Package homepage URL")
    repository: Optional[str] = Field(None, description="Source repository URL")


class DependencyInfo(BaseModel):
    """Complete dependency information from a repository."""

    repo_path: str = Field(description="Path to the repository")
    branch: str = Field(description="Git branch that was scanned")
    packages: dict[str, dict[str, str]] = Field(
        description="Dependencies grouped by ecosystem",
        json_schema_extra={
            "example": {
                "python": {"requests": "2.28.0", "pandas": "1.5.3"},
                "javascript": {"react": "18.2.0"},
            }
        },
    )
    manifest_files: list[str] = Field(
        description="List of manifest files that were parsed",
        json_schema_extra={"example": ["requirements.txt", "pyproject.toml", "package.json"]},
    )
    total_packages: int = Field(description="Total number of packages found")

