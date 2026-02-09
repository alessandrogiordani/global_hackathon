"""
Java code analyzer using javalang.
Refactored from source_code_parser.py for Databricks MCP integration with temporary cloning.
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import javalang
from databricks.sdk import WorkspaceClient

from models.java_analysis import (
    JavaAnalysisResult,
    JavaFileStructure,
    JavaMethodCall,
    JavaClassInfo,
    JavaRepoScanRequest,
)

logger = logging.getLogger(__name__)

# Default directories to exclude from scanning
DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "target",
    "build",
    "out",
    ".gradle",
    ".mvn",
    "node_modules",
}

JAVA_FILE_RE = re.compile(r".*\.java$", re.IGNORECASE)


class JavaAnalyzer:
    """Analyze Java source code for method calls and structure using temporary cloning."""

    def __init__(self, workspace_client: WorkspaceClient):
        """Initialize the Java analyzer."""
        self.w = workspace_client

    def analyze_repo(
        self, git_url: str, ref: str = "main", repo_name: Optional[str] = None
    ) -> JavaAnalysisResult:
        """
        Analyze a Java repository using temporary clone.

        Args:
            git_url: Git repository URL
            ref: Branch/tag/commit to analyze
            repo_name: Human-readable name (derived from URL if not provided)

        Returns:
            JavaAnalysisResult with all analysis data
        """
        if not repo_name:
            repo_name = git_url.rstrip(".git").split("/")[-1]

        logger.info(f"🔍 Starting Java analysis: {repo_name} ({ref})")

        # Use temporary directory for cloning
        with tempfile.TemporaryDirectory() as temp_dir:
            clone_path = Path(temp_dir) / "repo"

            try:
                # Clone repository
                self._clone_repo(git_url, clone_path, ref)

                # Find and analyze Java files
                java_files = self._find_java_files(clone_path, DEFAULT_EXCLUDE_DIRS)
                logger.info(f"📁 Found {len(java_files)} Java files")

                # Parse each file
                structures = []
                method_calls = []
                parse_success = 0
                parse_errors = 0

                for java_file in java_files:
                    result = self._analyze_java_file(java_file, clone_path)

                    structures.append(
                        JavaFileStructure(
                            file_path=result["file_path"],
                            parse_ok=result["parse_ok"],
                            error=result["error"],
                            package=result["structure"].get("package")
                            if result["structure"]
                            else None,
                            top_level_types=[
                                JavaClassInfo(**t)
                                for t in result["structure"].get("top_level_types", [])
                            ]
                            if result["structure"]
                            else [],
                        )
                    )

                    if result["parse_ok"]:
                        parse_success += 1
                        for inv in result["invocations"]:
                            method_calls.append(JavaMethodCall(**inv))
                    else:
                        parse_errors += 1

                # Generate summary
                summary = self._generate_summary(structures, method_calls)

                logger.info(
                    f"✅ Analysis complete: {parse_success} files parsed, {len(method_calls)} method calls found"
                )

                return JavaAnalysisResult(
                    repo_url=git_url,
                    repo_name=repo_name,
                    ref=ref,
                    total_files=len(java_files),
                    total_calls=len(method_calls),
                    parse_success_count=parse_success,
                    parse_error_count=parse_errors,
                    structures=structures,
                    method_calls=method_calls,
                    summary=summary,
                )

            except Exception as e:
                logger.error(f"❌ Error analyzing repository: {e}")
                raise

        # Temp directory automatically cleaned up here

    def _clone_repo(self, repo_url: str, dest: Path, ref: Optional[str] = None) -> None:
        """Clone repository to destination path."""
        logger.info(f"📥 Cloning {repo_url} (ref: {ref or 'default'})")

        if dest.exists():
            shutil.rmtree(dest)

        cmd = ["git", "clone", "--depth", "1"]

        if ref:
            cmd += ["--branch", ref, "--single-branch"]

        cmd += [repo_url, str(dest)]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            # Fallback if --branch failed (e.g., ref is a commit hash)
            if ref:
                logger.warning(f"⚠️ Failed to clone with --branch, trying fallback")
                subprocess.run(
                    ["git", "clone", "--depth", "1", repo_url, str(dest)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                subprocess.run(
                    ["git", "checkout", ref],
                    cwd=dest,
                    check=True,
                    capture_output=True,
                    text=True,
                )
            else:
                raise RuntimeError(f"Failed to clone repository: {e.stderr}")

    def _find_java_files(self, root: Path, exclude_dirs: set) -> List[Path]:
        """Find all Java files under root, skipping excluded directories."""
        java_files = []

        for dirpath, dirnames, filenames in os.walk(root):
            # In-place prune excluded directories
            dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

            for fn in filenames:
                if JAVA_FILE_RE.match(fn):
                    java_files.append(Path(dirpath) / fn)

        return java_files

    def _analyze_java_file(
        self, java_file: Path, repo_root: Path
    ) -> Dict[str, Any]:
        """
        Parse a single Java file and extract structure and invocations.

        Returns:
            Dict with keys: file_path, parse_ok, error, structure, invocations
        """
        # Get relative path from repo root
        try:
            rel_path = java_file.relative_to(repo_root)
        except ValueError:
            rel_path = java_file

        # Read file content
        source = self._safe_read_text(java_file)

        try:
            # Parse with javalang
            tree = javalang.parse.parse(source)
        except (javalang.parser.JavaSyntaxError, IndexError) as e:
            logger.warning(f"⚠️ Parse error in {rel_path}: {e}")
            return {
                "file_path": str(rel_path),
                "parse_ok": False,
                "error": f"{e.__class__.__name__}: {e}",
                "structure": None,
                "invocations": [],
            }

        # Extract structure
        structure = self._extract_structure(tree)

        # Extract method invocations
        invocations = []
        for path, node in tree:
            if isinstance(node, javalang.tree.MethodInvocation):
                invocations.append(
                    self._invocation_record(str(rel_path), path, node)
                )

        return {
            "file_path": str(rel_path),
            "parse_ok": True,
            "error": None,
            "structure": structure,
            "invocations": invocations,
        }

    def _safe_read_text(self, path: Path) -> str:
        """Read file content, tolerating unknown encodings."""
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="latin-1", errors="replace")

    def _extract_structure(self, compilation_unit) -> Dict[str, Any]:
        """Extract basic file structure from a CompilationUnit."""
        pkg = compilation_unit.package.name if compilation_unit.package else None

        # Top-level types: ClassDeclaration, InterfaceDeclaration, etc.
        top_types = []
        for t in compilation_unit.types or []:
            type_kind = t.__class__.__name__
            top_types.append(
                {
                    "name": getattr(t, "name", None),
                    "kind": type_kind,
                    "modifiers": sorted(list(getattr(t, "modifiers", []) or [])),
                }
            )

        return {"package": pkg, "top_level_types": top_types}

    def _invocation_record(
        self, file_path: str, path: Tuple, inv
    ) -> Dict[str, Any]:
        """Build a record for one MethodInvocation."""
        member = getattr(inv, "member", None)
        qualifier = getattr(inv, "qualifier", None)

        # Find caller context
        cls = (
            self._nearest_ancestor(path, javalang.tree.ClassDeclaration)
            or self._nearest_ancestor(path, javalang.tree.InterfaceDeclaration)
            or self._nearest_ancestor(path, javalang.tree.EnumDeclaration)
        )

        mth = self._nearest_ancestor(
            path, javalang.tree.MethodDeclaration
        ) or self._nearest_ancestor(path, javalang.tree.ConstructorDeclaration)

        caller_class = getattr(cls, "name", None) if cls else None
        caller_method = getattr(mth, "name", None) if mth else None
        caller_method_kind = mth.__class__.__name__ if mth else None

        # Args count
        args = getattr(inv, "arguments", None) or []
        arg_count = len(args)

        # Position
        pos = self._node_position(inv)

        return {
            "file_path": file_path,
            "line_number": pos["line"] if pos else 0,
            "column_number": pos.get("column") if pos else None,
            "caller_class": caller_class,
            "caller_method": caller_method,
            "caller_method_kind": caller_method_kind,
            "callee_qualifier": qualifier,
            "callee_member": member,
            "arg_count": arg_count,
        }

    def _nearest_ancestor(self, path: Tuple, klass):
        """Find nearest ancestor of type `klass` in traversal path."""
        for anc in reversed(path):
            if isinstance(anc, klass):
                return anc
        return None

    def _node_position(self, node) -> Optional[Dict[str, int]]:
        """Extract position (line/column) from a javalang node."""
        pos = getattr(node, "position", None)
        if not pos:
            return None

        try:
            return {"line": int(pos[0]), "column": int(pos[1])}
        except Exception:
            # Some versions expose .line/.column
            line = getattr(pos, "line", None)
            col = getattr(pos, "column", None)
            if line is not None and col is not None:
                return {"line": int(line), "column": int(col)}

        return None

    def _generate_summary(
        self, structures: List[JavaFileStructure], method_calls: List[JavaMethodCall]
    ) -> Dict[str, Any]:
        """Generate summary statistics."""
        packages = set()
        classes = set()
        unique_methods = set()

        for struct in structures:
            if struct.parse_ok and struct.package:
                packages.add(struct.package)
            for type_info in struct.top_level_types:
                classes.add(type_info.name)

        for call in method_calls:
            unique_methods.add(call.callee_member)

        return {
            "unique_packages": sorted(list(packages)),
            "unique_classes": sorted(list(classes)),
            "unique_method_calls": sorted(list(unique_methods)),
            "package_count": len(packages),
            "class_count": len(classes),
            "unique_method_count": len(unique_methods),
        }

