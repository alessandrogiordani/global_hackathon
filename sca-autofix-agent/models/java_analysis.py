"""
Pydantic models for Java code analysis results.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class JavaMethodCall(BaseModel):
    """Represents a method invocation found in Java code."""

    file_path: str = Field(
        description="Path to the Java file containing the call"
    )
    line_number: int = Field(description="Line number where the call occurs")
    column_number: Optional[int] = Field(
        default=None, description="Column number (if available)"
    )
    caller_class: Optional[str] = Field(
        default=None, description="Class containing the method that makes the call"
    )
    caller_method: Optional[str] = Field(
        default=None, description="Method that makes the call"
    )
    caller_method_kind: Optional[str] = Field(
        default=None,
        description="Kind of caller (MethodDeclaration, ConstructorDeclaration)",
    )
    callee_qualifier: Optional[str] = Field(
        default=None,
        description="Qualifier/receiver of the call (e.g., 'logger', 'database')",
    )
    callee_member: str = Field(description="Method name being called (e.g., 'info')")
    arg_count: int = Field(description="Number of arguments in the call")


class JavaClassInfo(BaseModel):
    """Information about a Java class, interface, or enum."""

    name: str = Field(description="Name of the type")
    kind: str = Field(
        description="Kind: ClassDeclaration, InterfaceDeclaration, EnumDeclaration, etc."
    )
    modifiers: List[str] = Field(
        default_factory=list, description="Modifiers like public, abstract, final"
    )


class JavaFileStructure(BaseModel):
    """Structure information for a single Java file."""

    file_path: str = Field(description="Path to the Java file")
    parse_ok: bool = Field(description="Whether the file parsed successfully")
    error: Optional[str] = Field(default=None, description="Parse error if any")
    package: Optional[str] = Field(
        default=None, description="Package name (e.g., com.example.service)"
    )
    top_level_types: List[JavaClassInfo] = Field(
        default_factory=list, description="Top-level classes, interfaces, enums"
    )


class JavaAnalysisResult(BaseModel):
    """Complete analysis result for a Java repository."""

    repo_url: str = Field(description="Git repository URL")
    repo_name: str = Field(description="Human-readable repository name")
    ref: str = Field(description="Branch, tag, or commit that was analyzed")
    total_files: int = Field(description="Total Java files found")
    total_calls: int = Field(description="Total method invocations found")
    parse_success_count: int = Field(
        description="Number of files parsed successfully"
    )
    parse_error_count: int = Field(description="Number of files with parse errors")
    structures: List[JavaFileStructure] = Field(
        description="Structure information for each file"
    )
    method_calls: List[JavaMethodCall] = Field(
        description="All method invocations found"
    )
    summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary statistics (packages, classes, unique methods)",
    )


class JavaRepoScanRequest(BaseModel):
    """Request to scan a Java repository."""

    repo_url: str = Field(description="Git repository URL")
    ref: str = Field(default="main", description="Branch/tag/commit to scan")
    repo_name: Optional[str] = Field(
        default=None, description="Human-readable name (derived from URL if not provided)"
    )
    depth: int = Field(
        default=1, description="Git clone depth (1 for shallow clone)"
    )
    exclude_dirs: List[str] = Field(
        default_factory=lambda: [
            ".git",
            ".idea",
            ".vscode",
            "target",
            "build",
            "out",
            ".gradle",
            ".mvn",
            "node_modules",
        ],
        description="Directories to exclude from scanning",
    )

