"""
Models for tracking package and method usage in source code.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ImportStatement(BaseModel):
    """Represents an import statement found in source code."""

    file_path: str = Field(description="File where the import was found")
    line_number: int = Field(description="Line number of the import")
    package_name: str = Field(description="Package being imported")
    imported_items: list[str] = Field(
        default_factory=list,
        description="Specific items imported (for 'from X import Y' statements)",
    )
    alias: Optional[str] = Field(None, description="Alias used for the import (as X)")
    import_type: str = Field(
        description="Type of import: 'module', 'from', 'star'",
        json_schema_extra={"example": "from"},
    )


class MethodUsage(BaseModel):
    """Represents usage of a specific method/function from a package."""

    package_name: str = Field(description="Package containing the method")
    method_name: str = Field(description="Name of the method/function")
    file_path: str = Field(description="File where the method is used")
    line_number: int = Field(description="Line number where the method is called")
    context: str = Field(description="Code context around the usage (few lines)")
    call_signature: Optional[str] = Field(
        None, description="How the method is called, including arguments"
    )


class PackageUsageAnalysis(BaseModel):
    """Complete analysis of how a package is used in a repository."""

    package_name: str = Field(description="Name of the analyzed package")
    package_version: str = Field(description="Current version being used")
    imports: list[ImportStatement] = Field(
        default_factory=list, description="All import statements for this package"
    )
    method_usages: list[MethodUsage] = Field(
        default_factory=list, description="All method/function usages detected"
    )
    total_files: int = Field(description="Number of files using this package")
    total_usages: int = Field(description="Total number of method calls detected")
    unique_methods: list[str] = Field(
        default_factory=list,
        description="List of unique methods/functions used from this package",
    )


class APIChange(BaseModel):
    """Represents a detected API change between package versions."""

    package_name: str = Field(description="Package name")
    from_version: str = Field(description="Old version")
    to_version: str = Field(description="New version")
    change_type: str = Field(
        description="Type of change: 'removed', 'renamed', 'signature_changed', 'deprecated'",
    )
    affected_item: str = Field(description="Class/function/method that changed")
    old_signature: Optional[str] = Field(None, description="Old function signature")
    new_signature: Optional[str] = Field(None, description="New function signature")
    migration_hint: Optional[str] = Field(
        None, description="Suggested code change to fix"
    )
    is_breaking: bool = Field(description="Whether this is a breaking change")
    severity: str = Field(
        description="Impact severity: 'critical', 'high', 'medium', 'low'",
        json_schema_extra={"example": "high"},
    )


class BreakingChangeReport(BaseModel):
    """Report of breaking changes that would affect the codebase."""

    package_name: str = Field(description="Package being upgraded")
    from_version: str = Field(description="Current version")
    to_version: str = Field(description="Target version")
    breaking_changes: list[APIChange] = Field(
        default_factory=list, description="List of breaking API changes"
    )
    affected_files: list[str] = Field(
        default_factory=list,
        description="Files that would be affected by the changes",
    )
    total_breaking_changes: int = Field(
        description="Total number of breaking changes detected"
    )
    migration_required: bool = Field(
        description="Whether code migration is required"
    )
    recommended_action: str = Field(
        description="Recommended action: 'safe_to_upgrade', 'manual_review_required', 'do_not_upgrade'"
    )

